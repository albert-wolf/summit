# Summit — GTK4 NordVPN GUI

<img width="942" height="650" alt="image" src="https://github.com/user-attachments/assets/d1030e2d-829e-4b33-a3b2-2619a5687dac" />
<img width="942" height="650" alt="image" src="https://github.com/user-attachments/assets/f8d473e9-8090-4500-b62e-e1c4aaea7ed1" />
<img width="942" height="650" alt="image" src="https://github.com/user-attachments/assets/70955d01-6b18-43e8-9ca4-d00322cbe18b" />
<img width="942" height="650" alt="image" src="https://github.com/user-attachments/assets/e7104de1-0a61-4460-ba3f-2e107b987cb3" />

An unofficial, community-developed GTK4 graphical interface for the NordVPN command-line tool on Linux.

## ⚠️ Work In Progress

Summit is actively being developed. Features may change, bugs may exist, and some functionality is still being refined. Contributions, feedback, and bug reports are welcome.

## ⚠️ Disclaimer

**Summit is NOT affiliated with, authorized by, maintained by, sponsored by, or endorsed by NordVPN or any of its subsidiaries.** This is an unofficial, community-developed third-party tool. For full legal details, see [DISCLAIMER.md](DISCLAIMER.md).

## Features

- **5-Tab Interface**:
  - **Status**: Real-time VPN connection status with colored indicator, quick connect/disconnect/reconnect buttons
  - **Servers**: Country and city selection with live search and auto-highlighting
  - **Settings**: Toggle all NordVPN settings (Kill Switch, Firewall, Auto-connect, etc.) and select technology/protocol
  - **Ports**: Manage allowlisted ports with add/remove interface
  - **Meshnet**: Enable/disable meshnet and view connected peers

- **Real-Time Polling**: Status updates every 2 seconds
- **City Search**: Search cities by name — matching country auto-highlights in the left pane
- **Server Cache**: City-to-country mappings cached locally for fast startup
- **Configuration Persistence**: Window size, position, and last-selected tab saved to `~/.config/summit/config.json`
- **Async Operations**: All CLI commands run in background threads for a responsive UI

## Requirements

- Linux (Debian/Ubuntu-based recommended)
- Python 3.10+
- NordVPN CLI (`nordvpn`) installed and logged in
- GTK4 libraries
- PyGObject

## Installation

### From .deb Package (Recommended)

```bash
sudo dpkg -i summit_0.8.0_all.deb
sudo apt-get install -f  # Install any missing dependencies
summit
```

### From Source

```bash
# Install dependencies
sudo apt-get install python3 python3-gi gir1.2-gtk-4.0

# Run directly
python3 src/main.py
```

## NordVPN Setup

```bash
# Install NordVPN CLI
curl https://repo.nordvpn.com/gpg/nordvpn_public.asc | sudo apt-key add -
echo 'deb https://repo.nordvpn.com/deb/nordvpn/debian stable main' | sudo tee /etc/apt/sources.list.d/nordvpn.list
sudo apt update && sudo apt install nordvpn

# Log in
nordvpn login
```

## File Structure

```
Summit/
├── src/
│   ├── main.py              # GTK Application, window layout, config, polling
│   ├── summit_manager.py    # NordVPN CLI wrapper (no GTK dependencies)
│   ├── status_pane.py       # Tab 1: Status display & connect/disconnect
│   ├── servers_pane.py      # Tab 2: Country/city selection with search
│   ├── settings_pane.py     # Tab 3: Boolean toggles & protocol selector
│   ├── ports_pane.py        # Tab 4: Port allowlist management
│   ├── meshnet_pane.py      # Tab 5: Meshnet toggle & peer list
│   └── recent_pane.py       # Sidebar: Recent connections & favorites
├── tests/
│   └── test_servers_pane.py # Unit tests
├── style.css                # GTK4 dark theme
├── build.sh                 # .deb build script
├── debian/                  # Debian package metadata
├── docs/                    # Design documents and plans
├── summit_0.8.0_all.deb     # Pre-built installer
├── DISCLAIMER.md            # Legal disclaimer
└── README.md                # This file
```

## Uninstall

```bash
# If installed via .deb
sudo dpkg -r summit

# If running from source, just delete the folder
```

## Known Limitations

- Requires active NordVPN login (`nordvpn login`)
- Meshnet must be enabled before viewing peers
- Country/city names use underscore format (NordVPN CLI format)

## License

MIT License + Commons Clause. Free for personal use. Commercial use requires written permission from the copyright holder. See [LICENSE](LICENSE) for full terms.
