#!/usr/bin/env python3
"""
Polybar Tray Toggle - A utility to toggle applications between workspaces and system tray
Supports i3 window manager with polybar system tray
"""

import subprocess
import i3ipc
import json
import time
import argparse
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple, Union
import re


@dataclass
class AppConfig:
    """Configuration for an application"""
    name: str
    process_patterns: List[str]
    launch_commands: List[str]
    tray_info: str
    window_class_patterns: List[str] = None
    window_name_patterns: List[str] = None
    
    def __post_init__(self):
        if self.window_class_patterns is None:
            self.window_class_patterns = [self.name.lower()]
        if self.window_name_patterns is None:
            self.window_name_patterns = [self.name.lower()]


class I3WindowManager:
    """Interface for i3 window manager operations"""
    
    def __init__(self):
        self.i3 = i3ipc.Connection()
    
    def get_current_workspace(self) -> Optional[Any]:
        """Get current i3 workspace"""
        try:
            tree = self.i3.get_tree()
            return tree.find_focused().workspace()
        except Exception as e:
            print(f"Error getting current workspace: {e}")
            return None
    
    def find_window(self, app_config: AppConfig) -> Tuple[Optional[Any], Union[str, Any, None]]:
        """Find app window in workspaces or scratchpad"""
        try:
            tree = self.i3.get_tree()
            
            # Search in workspaces
            for workspace in tree.workspaces():
                for window in workspace.leaves():
                    if self._window_matches(window, app_config):
                        return window, workspace
            
            # Search in scratchpad
            scratchpad = tree.scratchpad()
            if scratchpad:
                for window in scratchpad.leaves():
                    if self._window_matches(window, app_config):
                        return window, "scratchpad"
            
            return None, None
        except Exception as e:
            print(f"Error finding window in i3: {e}")
            return None, None
    
    def _window_matches(self, window: Any, app_config: AppConfig) -> bool:
        """Check if window matches app configuration"""
        # Check window class
        if window.window_class:
            for pattern in app_config.window_class_patterns:
                if pattern.lower() in window.window_class.lower():
                    return True
        
        # Check window name
        if window.name:
            for pattern in app_config.window_name_patterns:
                if pattern.lower() in window.name.lower():
                    return True
        
        return False
    
    def move_to_scratchpad(self, window: Any) -> bool:
        """Move window to scratchpad"""
        try:
            window.command('move scratchpad')
            return True
        except Exception as e:
            print(f"Error moving to scratchpad: {e}")
            return False
    
    def show_from_scratchpad(self, window: Any) -> bool:
        """Show window from scratchpad"""
        try:
            window.command('scratchpad show')
            window.command('focus')
            return True
        except Exception as e:
            print(f"Error showing from scratchpad: {e}")
            return False
    
    def move_to_workspace(self, window: Any, workspace_name: str) -> bool:
        """Move window to specific workspace and focus"""
        try:
            window.command(f'move to workspace {workspace_name}')
            window.command('focus')
            return True
        except Exception as e:
            print(f"Error moving to workspace: {e}")
            return False


class ProcessManager:
    """Handle process-related operations"""
    
    @staticmethod
    def is_running(app_config: AppConfig) -> Optional[str]:
        """Check if application process is running"""
        for pattern in app_config.process_patterns:
            try:
                result = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                continue
        return None
    
    @staticmethod
    def launch(app_config: AppConfig) -> bool:
        """Launch the application"""
        for cmd in app_config.launch_commands:
            try:
                subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"Launched {app_config.name} using command: {cmd}")
                return True
            except FileNotFoundError:
                continue
        
        print(f"Failed to launch {app_config.name} - no working command found")
        return False


class TrayManager:
    """Handle polybar system tray operations"""
    
    @staticmethod
    def find_icon_geometry(tray_info: str) -> Optional[Dict[str, int]]:
        """Get tray icon geometry from xwininfo"""
        try:
            result = subprocess.run(['xwininfo', '-tree', '-root'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"xwininfo error: {result.stderr}")
                return None
            
            lines = result.stdout.split('\n')
            polybar_found = False
            in_polybar_children = False
            
            for i, line in enumerate(lines):
                # Look for polybar window
                if 'polybar' in line.lower() and ('("polybar"' in line or '"Polybar"' in line):
                    polybar_found = True
                    continue
                
                # Enter polybar children section
                if polybar_found and 'children:' in line:
                    in_polybar_children = True
                    continue
                
                # Process polybar children
                if in_polybar_children and polybar_found:
                    # Check if we've left the polybar section
                    if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                        if 'polybar' not in line.lower():
                            break
                    
                    if tray_info in line:
                        print(f"Found app in tray: {line.strip()}")
                        return TrayManager._parse_geometry(line, lines, i)
            
            return None
        except Exception as e:
            print(f"Error getting tray geometry: {e}")
            return None
    
    @staticmethod
    def _parse_geometry(line: str, lines: List[str], line_index: int) -> Optional[Dict[str, int]]:
        """Parse geometry information from xwininfo output"""
        geometry_pattern = r'(\d+)x(\d+)\+(\d+)\+(\d+)\s+\+(\d+)\+(\d+)'
        
        # Try parent line first
        if line_index > 0:
            parent_line = lines[line_index - 1]
            match = re.search(geometry_pattern, parent_line)
            if match:
                width, height, rel_x, rel_y, abs_x, abs_y = map(int, match.groups())
                return {'x': abs_x, 'y': abs_y, 'width': width, 'height': height}
        
        # Try current line
        match = re.search(geometry_pattern, line)
        if match:
            width, height, rel_x, rel_y, abs_x, abs_y = map(int, match.groups())
            return {'x': abs_x, 'y': abs_y, 'width': width, 'height': height}
        
        return None
    
    @staticmethod
    def click_icon(geometry: Dict[str, int]) -> bool:
        """Simulate mouse click on tray icon"""
        try:
            # Save original mouse position
            orig_pos = subprocess.run(['xdotool', 'getmouselocation', '--shell'], 
                                    capture_output=True, text=True)
            orig_x = orig_y = None
            
            if orig_pos.returncode == 0:
                for line in orig_pos.stdout.splitlines():
                    if line.startswith('X='):
                        orig_x = int(line.split('=')[1])
                    elif line.startswith('Y='):
                        orig_y = int(line.split('=')[1])
            
            # Click center of tray icon
            center_x = geometry['x'] + (geometry['width'] // 2)
            center_y = geometry['y'] + (geometry['height'] // 2)
            
            print(f"Clicking tray at ({center_x}, {center_y})")
            
            subprocess.run(['xdotool', 'mousemove', str(center_x), str(center_y)])
            time.sleep(0.1)
            subprocess.run(['xdotool', 'click', '1'])
            
            # Restore mouse position
            if orig_x is not None and orig_y is not None:
                subprocess.run(['xdotool', 'mousemove', str(orig_x), str(orig_y)])
            
            return True
        except Exception as e:
            print(f"Error clicking tray icon: {e}")
            return False


class AppToggler:
    """Main application toggler class"""
    
    def __init__(self):
        self.wm = I3WindowManager()
        self.process_mgr = ProcessManager()
        self.tray_mgr = TrayManager()
    
    def toggle_app(self, app_config: AppConfig, verbose: bool = True) -> bool:
        """Toggle application visibility/state"""
        if verbose:
            print(f"=== Toggling {app_config.name} ===")
        
        # Gather current state
        process_id = self.process_mgr.is_running(app_config)
        in_tray = self.tray_mgr.find_icon_geometry(app_config.tray_info) is not None
        app_window, app_workspace = self.wm.find_window(app_config)
        current_workspace = self.wm.get_current_workspace()
        
        if verbose:
            print(f"Process running: {bool(process_id)}")
            print(f"App in tray: {in_tray}")
            print(f"App window found: {bool(app_window)}")
            if app_window and app_workspace:
                ws_name = "scratchpad" if app_workspace == "scratchpad" else app_workspace.name
                print(f"App workspace: {ws_name}")
            if current_workspace:
                print(f"Current workspace: {current_workspace.name}")
        
        # Case 1: App not launched
        if not in_tray:
            if verbose:
                print("Case 1: App not launched, launching...")
            return self.process_mgr.launch(app_config)
        
        # Case 2: App has window in i3 (workspace or scratchpad)
        if app_window and app_workspace and current_workspace:
            return self._handle_window_case(app_window, app_workspace, current_workspace, 
                                          app_config.name, verbose)
        
        # Case 3: App in tray only
        if process_id and in_tray and not app_window:
            if verbose:
                print("Case 3: App in tray only, clicking tray icon...")
            return self._click_tray_icon(app_config)
        
        # Fallback
        if verbose:
            print("Fallback: Unexpected state, trying tray click...")
        return self._click_tray_icon(app_config)
    
    def _handle_window_case(self, app_window: Any, app_workspace: Union[str, Any], 
                          current_workspace: Any, app_name: str, verbose: bool) -> bool:
        """Handle cases where app window exists in i3"""
        if app_workspace == "scratchpad":
            if verbose:
                print("Case 2c: App in scratchpad, showing in current workspace...")
            success = self.wm.show_from_scratchpad(app_window)
            if verbose and success:
                print(f"Showed {app_name} from scratchpad and focused")
            return success
        
        elif app_workspace.name == current_workspace.name:
            if verbose:
                print("Case 2a: App in current workspace, moving to scratchpad...")
            success = self.wm.move_to_scratchpad(app_window)
            if verbose and success:
                print(f"Moved {app_name} to scratchpad")
            return success
        
        else:
            if verbose:
                print(f"Case 2b: App in workspace '{app_workspace.name}', "
                     f"moving to current workspace '{current_workspace.name}'...")
            success = self.wm.move_to_workspace(app_window, current_workspace.name)
            if verbose and success:
                print(f"Moved {app_name} to current workspace and focused")
            return success
    
    def _click_tray_icon(self, app_config: AppConfig) -> bool:
        """Click tray icon for the app"""
        geometry = self.tray_mgr.find_icon_geometry(app_config.tray_info)
        if geometry:
            success = self.tray_mgr.click_icon(geometry)
            if success:
                time.sleep(0.5)  # Wait for window to appear
            return success
        return False


class ConfigManager:
    """Handle configuration loading and management"""
    
    DEFAULT_CONFIG = {
        "wechat": {
            "name": "wechat",
            "process_patterns": ["wechat"],
            "launch_commands": ["wechat.sh", "wechat-universal"],
            "tray_info": '"wechat": ("wechat" "wechat")',
            "window_class_patterns": ["wechat"],
            "window_name_patterns": ["wechat"]
        },
        "discord": {
            "name": "discord",
            "process_patterns": ["discord", "Discord"],
            "launch_commands": ["discord", "/usr/bin/discord"],
            "tray_info": '"discord": ("discord" "Discord")',
            "window_class_patterns": ["discord", "Discord"],
            "window_name_patterns": ["discord", "Discord"]
        },
        "telegram": {
            "name": "telegram",
            "process_patterns": ["telegram", "Telegram"],
            "launch_commands": ["telegram-desktop", "telegram"],
            "tray_info": '"telegram": ("telegram" "TelegramDesktop")',
            "window_class_patterns": ["telegram", "TelegramDesktop"],
            "window_name_patterns": ["telegram", "Telegram"]
        },
        "qq": {
            "name": "qq",
            "process_patterns": ["qq", "QQ"],
            "launch_commands": ["qq"],
            "tray_info": '"electron": ("electron" "Electron")',
            "window_class_patterns": ["qq", "QQ"],
            "window_name_patterns": ["qq", "QQ"]
        }
    }
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> Dict[str, AppConfig]:
        """Load configuration from file or use defaults"""
        config_data = cls.DEFAULT_CONFIG.copy()
        
        if config_path:
            config_file = Path(config_path)
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        user_config = json.load(f)
                        config_data.update(user_config)
                        print(f"Loaded config from {config_path}")
                except Exception as e:
                    print(f"Error loading config from {config_path}: {e}")
                    print("Using default configuration")
        
        # Convert to AppConfig objects
        apps = {}
        for app_name, app_data in config_data.items():
            try:
                apps[app_name] = AppConfig(**app_data)
            except Exception as e:
                print(f"Error creating config for {app_name}: {e}")
        
        return apps
    
    @classmethod
    def save_default_config(cls, config_path: str):
        """Save default configuration to file"""
        try:
            with open(config_path, 'w') as f:
                json.dump(cls.DEFAULT_CONFIG, f, indent=2)
            print(f"Default configuration saved to {config_path}")
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Toggle applications between workspaces and system tray",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s wechat                    # Toggle WeChat
  %(prog)s --config apps.json discord # Toggle Discord with custom config
  %(prog)s --list                    # List available apps
  %(prog)s --generate-config         # Generate default config file
        """
    )
    
    parser.add_argument('app', nargs='?', help='Application name to toggle')
    parser.add_argument('--config', '-c', help='Path to JSON configuration file')
    parser.add_argument('--list', '-l', action='store_true', help='List available applications')
    parser.add_argument('--generate-config', '-g', metavar='FILE', 
                       help='Generate default configuration file')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')
    
    args = parser.parse_args()
    
    # Generate config file
    if args.generate_config:
        ConfigManager.save_default_config(args.generate_config)
        return 0
    
    # Load configuration
    apps = ConfigManager.load_config(args.config)
    
    # List apps
    if args.list:
        print("Available applications:")
        for app_name in sorted(apps.keys()):
            print(f"  {app_name}")
        return 0
    
    # Validate app argument
    if not args.app:
        parser.print_help()
        return 1
    
    if args.app not in apps:
        print(f"Error: Unknown application '{args.app}'")
        print(f"Available apps: {', '.join(sorted(apps.keys()))}")
        return 1
    
    # Toggle the application
    toggler = AppToggler()
    app_config = apps[args.app]
    
    try:
        success = toggler.toggle_app(app_config, verbose=not args.quiet)
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())