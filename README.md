# Summit — GTK4 NordVPN CLI Wrapper

<img width="942" height="650" alt="image" src="https://github.com/user-attachments/assets/d1030e2d-829e-4b33-a3b2-2619a5687dac" />
<img width="942" height="650" alt="image" src="https://github.com/user-attachments/assets/f8d473e9-8090-4500-b62e-e1c4aaea7ed1" />
<img width="942" height="650" alt="image" src="https://github.com/user-attachments/assets/70955d01-6b18-43e8-9ca4-d00322cbe18b" />
<img width="942" height="650" alt="image" src="https://github.com/user-attachments/assets/e7104de1-0a61-4460-ba3f-2e107b987cb3" />


An unofficial community-developed GTK4 graphical interface for the NordVPN command-line tool.

## ⚠️ IMPORTANT DISCLAIMER

**Summit is NOT affiliated with, authorized by, maintained by, sponsored by, or endorsed by NordVPN or any of its subsidiaries.** This is an unofficial, community-developed third-party tool. For full legal details, see [DISCLAIMER.md](DISCLAIMER.md).

## Features

- **5-Tab Interface**:
  - **Status**: Real-time VPN connection status with colored indicator, quick disconnect/reconnect buttons
  - **Servers**: Country and city selection with geographic filtering
  - **Settings**: Toggle all NordVPN settings (Kill Switch, Firewall, Auto-connect, etc.) and select technology/protocol
  - **Ports**: Manage allowlisted ports with add/remove interface
  - **Meshnet**: Enable/disable meshnet and view connected peers

- **Real-Time Polling**: Status updates every 2 seconds
- **Configuration Persistence**: Window size, position, and last-selected tab saved to `~/.config/nordgui/config.json`
- **Professional Dark Theme**: Custom GTK4 CSS with Nord-inspired colors
- **Async Operations**: All CLI commands run in background threads for responsive UI
- **Error Handling**: Graceful fallback for missing dependencies and NordVPN login requirements

## Installation

### Requirements
- Python 3.10+
- NordVPN CLI tool (`nordvpn`)
- NordVPN login (run `nordvpn login` first)
- GTK4 libraries
- PyGObject for GTK bindings

### From .deb Package (Recommended)

```bash
sudo dpkg -i nordgui_0.8.0_all.deb
sudo apt-get install -f  # Install dependencies if needed
nordgui
```

### Manual Installation

```bash
# Install dependencies
sudo apt-get install python3 python3-gi gir1.2-gtk-4.0

# Copy application files
sudo mkdir -p /usr/share/nordgui/src
sudo cp src/*.py /usr/share/nordgui/src/
sudo cp style.css /usr/share/nordgui/

# Create launcher
sudo tee /usr/bin/nordgui > /dev/null << 'EOF'
#!/bin/sh
exec python3 /usr/share/nordgui/src/main.py "$@"
EOF
sudo chmod +x /usr/bin/nordgui

# Create desktop entry
sudo cp nordgui.desktop /usr/share/applications/

# Launch
nordgui
```

## File Structure

```
NordGUI/
├── src/
│   ├── main.py              # GTK Application, window layout, config, polling
│   ├── nord_manager.py      # NordVPN CLI wrapper (no GTK dependencies)
│   ├── status_pane.py       # Tab 1: Status display & connect/disconnect
│   ├── servers_pane.py      # Tab 2: Country/city selection
│   ├── settings_pane.py     # Tab 3: Boolean toggles & protocol selector
│   ├── ports_pane.py        # Tab 4: Port allowlist management
│   └── meshnet_pane.py      # Tab 5: Meshnet toggle & peer list
├── style.css                # GTK4 dark theme
├── build.sh                 # .deb build script
├── debian/                  # Debian package metadata
│   ├── control              # Package info
│   ├── postinst             # Post-install hook
│   ├── changelog            # Version history
│   └── compat               # Debian compatibility
└── README.md                # This file
```

## Architecture

### nord_manager.py (CLI Wrapper)
Pure Python wrapper with no GTK dependencies. Key methods:

```python
is_installed() -> bool                           # Check if nordvpn exists
is_logged_in() -> bool                           # Check login status
get_status() -> dict                             # Parse `nordvpn status`
get_settings() -> dict                           # Parse `nordvpn settings`
get_countries() -> list[str]                     # Parse `nordvpn countries`
get_cities(country) -> list[str]                 # Parse `nordvpn cities <country>`
connect(country, city=None) -> (bool, str)       # Connect to server
disconnect() -> (bool, str)                      # Disconnect
reconnect() -> (bool, str)                       # Reconnect to last server
set_setting(key, value) -> (bool, str)           # Change a setting
add_port(port, protocol) -> (bool, str)          # Add allowlisted port
remove_port(port, protocol) -> (bool, str)       # Remove allowlisted port
get_meshnet_peers() -> (enabled, peers_list)     # Get meshnet state
set_meshnet(enabled) -> (bool, str)              # Toggle meshnet
```

### Pane Architecture
Each pane is a `Gtk.Box` subclass implementing one tab:
- **StatusPane**: Grid layout showing current status + action buttons
- **ServersPane**: Paned layout with country/city lists + connect button
- **SettingsPane**: ScrolledWindow with switches/dropdowns for all settings
- **PortsPane**: ListBox with right-click context menu + add port form
- **MeshnetPane**: Toggle switch + conditional peer list

All panes use background threading with `GLib.idle_add()` for async CLI operations.

### Main Application Flow
1. Check `nordvpn` installed → Show alert and exit if not
2. Load config from `~/.config/nordgui/config.json`
3. Build window with 5 tabs
4. Check login status → Show notification if not logged in
5. Start 2-second polling loop to update status
6. Restore window size and active tab
7. On close: Save config and stop polling

## Building from Source

```bash
# Build .deb package
bash build.sh

# Output: nordgui_0.8.0_all.deb (20KB)
```

## Development

### Running Directly

```bash
# From project root
python3 src/main.py
```

### Adding a New Setting Toggle

Edit `settings_pane.py`:

```python
boolean_settings = [
    ("Display Name", "NordVPN Key"),  # Add here
    # ...
]
```

Then rebuild:

```bash
bash build.sh
```

### Testing CLI Integration

```python
import sys
sys.path.insert(0, 'src')
from nord_manager import NordManager

nord = NordManager()
print(nord.get_status())
print(nord.get_settings())
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| python3 | ≥3.10 | Runtime |
| python3-gi | - | GTK bindings |
| gir1.2-gtk-4.0 | 4.0 | GTK4 library |
| nordvpn | latest | VPN CLI |
| dpkg | - | Installation |

## Uninstall

```bash
# If installed via .deb
sudo dpkg -r nordgui

# If installed manually
sudo rm -rf /usr/share/nordgui
sudo rm /usr/bin/nordgui
sudo rm /usr/share/applications/nordgui.desktop
```

## Known Limitations

- Requires active NordVPN login (run `nordvpn login` first)
- Meshnet must be enabled before viewing peers (graceful error handling included)
- Country/city names use underscores (NordVPN API format)
- Port range: 1-65535

## License

Built as a personal GTK4 learning project. Feel free to modify and extend.

## Troubleshooting

### "NordVPN Not Installed"
```bash
# Install NordVPN
curl https://repo.nordvpn.com/gpg/nordvpn_public.asc | sudo apt-key add -
echo 'deb https://repo.nordvpn.com/deb/nordvpn/debian stable main' | sudo tee /etc/apt/sources.list.d/nordvpn.list > /dev/null
sudo apt update
sudo apt install nordvpn
```

### "Not Logged In"
```bash
# Log in to NordVPN
nordvpn login
```

### Application Won't Start
```bash
# Check for import errors
python3 -c "import sys; sys.path.insert(0, 'src'); from main import NordGUIApp"

# Check NordVPN CLI
nordvpn status
```

### Settings Don't Update
Ensure NordVPN is running and you have permission to modify settings:
```bash
nordvpn set killswitch on
nordvpn settings
```

## Credits

Developed using:
- GTK4 4.18+ with PyGObject
- NordVPN CLI API
- Gtk4 best practices from production projects
