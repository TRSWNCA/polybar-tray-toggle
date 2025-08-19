# Polybar Tray Toggle

A smart utility for toggling applications between i3 workspaces and the polybar system tray. Seamlessly manage your applications' visibility with intelligent workspace detection and tray interaction.

## 🚀 Features

- **Smart Application Detection**: Automatically detects if apps are running, visible in workspaces, or minimized to tray
- **Intelligent Workspace Management**:
  - Launch apps if not running
  - Move apps between workspaces
  - Hide/show apps using i3 scratchpad
  - Restore apps from system tray
- **Multi-Application Support**: Built-in support for WeChat, Discord, Telegram, QQ, and easy configuration for custom apps
- **Flexible Configuration**: JSON-based configuration system with command-line overrides
- **Clean Architecture**: Object-oriented design with modular components


## 📝 TODOs

- [ ] Publish a release version
- [ ] Support other DEs
- [ ] Full test


## 📋 Requirements

- **Window Manager**: i3wm
- **Status Bar**: Polybar with system tray module
- **Python**: 3.12+
- **System Tools**: `xdotool`, `xwininfo`, `pgrep`
- **Python Dependencies**: `i3ipc`

## 🔧 Installation

### 1. Install System Dependencies

```bash
# Arch Linux / Manjaro
sudo pacman -S xdotool xorg-xwininfo

# Ubuntu / Debian
sudo apt install xdotool x11-utils

# Fedora
sudo dnf install xdotool xorg-x11-utils
```

### 2. Clone and Setup

```bash
git clone <repository-url> polybar-tray-toggle
cd polybar-tray-toggle

# Install Python dependencies with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt  # if you create one
# pip install i3ipc
```

### 3. Make Executable

```bash
chmod +x main.py
```

## 📖 Usage

### Basic Commands

```bash
# Toggle WeChat (using uv)
uv run ./main.py wechat

# Toggle Discord
uv run ./main.py discord

# List available applications
uv run ./main.py --list

# Show help
uv run ./main.py --help

# Quiet mode (no output)
uv run ./main.py --quiet wechat
```

### Advanced Usage

```bash
# Use custom configuration file
uv run ./main.py --config my-apps.json discord

# Generate default configuration template
uv run ./main.py --generate-config apps.json
```

## ⚙️ Configuration

### Built-in Applications

The following applications are supported out of the box:

- **wechat**: WeChat messaging app
- **discord**: Discord chat application
- **telegram**: Telegram desktop client
- **qq**: QQ messaging app

### Custom Configuration

Create a JSON configuration file to add or modify applications:

```json
{
  "myapp": {
    "name": "myapp",
    "process_patterns": ["myapp", "MyApp"],
    "launch_commands": ["myapp", "/usr/bin/myapp", "flatpak run com.example.MyApp"],
    "tray_info": "\"myapp\": (\"myapp\" \"MyApp\")",
    "window_class_patterns": ["myapp", "MyApp"],
    "window_name_patterns": ["myapp", "My Application"]
  }
}
```

#### Configuration Fields

- **`name`**: Display name for the application
- **`process_patterns`**: List of process names to search for with `pgrep -f`
- **`launch_commands`**: Commands to try when launching the app (first working command is used)
- **`tray_info`**: String pattern to find the app in polybar tray (from `xwininfo` output)
- **`window_class_patterns`**: X11 window class patterns to match
- **`window_name_patterns`**: X11 window name patterns to match

### Finding Tray Info

To find the correct `tray_info` for your application:

```bash
# Run this while your app is in the tray
xwininfo -tree -root | grep -A 5 -B 5 "polybar"
```

Look for lines like: `0x4a00014 "wechat": ("wechat" "wechat")`

## 🔄 How It Works

The application follows this intelligent decision tree:

1. **App Not Launched**: If the app is not visible in the tray → Launch it
2. **App in Scratchpad**: If the app window is in i3 scratchpad → Show it in current workspace
3. **App in Current Workspace**: If the app is visible in current workspace → Hide it to scratchpad
4. **App in Other Workspace**: If the app is in a different workspace → Move it to current workspace
5. **App in Tray Only**: If the app is running but only visible in tray → Click tray icon to restore

## 🎯 Integration Examples

### i3 Keybindings

Add to your i3 config (`~/.config/i3/config`):

```bash
# Toggle applications
bindsym $mod+w exec --no-startup-id cd /path/to/polybar-tray-toggle && uv run ./main.py wechat
bindsym $mod+d exec --no-startup-id cd /path/to/polybar-tray-toggle && uv run ./main.py discord
bindsym $mod+t exec --no-startup-id cd /path/to/polybar-tray-toggle && uv run ./main.py telegram
```


### Shell Aliases

Add to your shell config (`.bashrc`, `.zshrc`):

```bash
alias tw='cd /path/to/polybar-tray-toggle && uv run ./main.py wechat'
alias td='cd /path/to/polybar-tray-toggle && uv run ./main.py discord'
alias tt='cd /path/to/polybar-tray-toggle && uv run ./main.py telegram'
```

## 🐛 Troubleshooting

### Common Issues

**App not found in tray**

- Ensure the app is actually running and visible in polybar tray
- Check the `tray_info` pattern matches the `xwininfo` output
- Verify polybar tray module is configured correctly

**Window not detected in i3**

- Check `window_class_patterns` and `window_name_patterns` match your app
- Use `xprop` to inspect window properties: click on the app window after running `xprop`

**Launch commands not working**

- Verify the commands in `launch_commands` are correct and executable
- Test launch commands manually in terminal
- Check if the app requires special environment or paths

### Debug Information

Run with verbose output to see what the script detects:

```bash
uv run ./main.py wechat  # Verbose by default
uv run ./main.py --quiet wechat  # Suppress output
```

### Getting Window Information

```bash
# Get window class and name
xprop | grep -E "(WM_CLASS|WM_NAME)"

# See all windows in i3 tree
i3-msg -t get_tree | jq '.nodes[].nodes[].nodes[].nodes[] | select(.window_properties) | {name: .name, class: .window_properties.class}'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with multiple applications
5. Submit a pull request

### Adding New Applications

To add support for a new application:

1. Find the application's process name, window class, and tray signature
2. Add configuration to `ConfigManager.DEFAULT_CONFIG`
3. Test the toggle functionality
4. Update this README

## 📄 License

This project is licensed under the [MIT License](./LICENSE).

## 🙏 Acknowledgments

- [i3ipc-python](https://github.com/altdesktop/i3ipc-python) for i3 window manager integration
- [polybar](https://github.com/polybar/polybar) for the system tray functionality
- The i3wm community for inspiration and support
