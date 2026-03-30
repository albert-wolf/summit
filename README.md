# Summit — GTK4 NordVPN GUI (v0.8.3 Beta)
An unofficial, community-developed, professional GTK4 graphical interface for the NordVPN command-line tool on Linux.

<img width="967" height="629" alt="Screenshot from 2026-03-29 02-07-40" src="https://github.com/user-attachments/assets/58a3c263-2851-49af-8d59-0f723daa659f" />
<img width="967" height="629" alt="Screenshot from 2026-03-29 02-08-08" src="https://github.com/user-attachments/assets/391774d4-6ebf-4997-a48b-1230463cb61a" />
<img width="967" height="629" alt="Screenshot from 2026-03-29 02-08-27" src="https://github.com/user-attachments/assets/0c6eea8d-7ad1-4960-b985-c2eb6a2e2913" />
<img width="967" height="629" alt="Screenshot from 2026-03-29 02-10-35" src="https://github.com/user-attachments/assets/10b796ec-7069-458e-a6ec-9c2f68537eb7" />
<img width="967" height="629" alt="Screenshot from 2026-03-29 02-10-56" src="https://github.com/user-attachments/assets/afff5aa2-2302-45c8-812c-7856a651784f" />

## ⚠️ Disclaimer

**Summit is NOT affiliated with, authorized by, maintained by, sponsored by, or endorsed by NordVPN or any of its subsidiaries.** This is an unofficial, community-developed third-party tool. For full legal details, see [DISCLAIMER.md](DISCLAIMER.md).

## Features

- **Modern 5-Tab Interface**:
  - **Status**: Real-time VPN connection monitoring with shaded card-style hierarchy and quick connect/disconnect/reconnect controls.
  - **Servers**: Intelligent country and city selection with live global search and automatic highlighting.
  - **Settings**: Comprehensive control over NordVPN features (Kill Switch, Firewall, Auto-connect, Obfuscate, etc.) and protocol selection.
  - **Ports**: Streamlined allowlisted port management.
  - **Meshnet**: Native 3-column layout for managing Meshnet state and peer visibility (This Device, Connected, Disconnected).

- **High Performance Architecture**:
  - **Blueprint UI**: Layouts defined using modern Blueprint (`.blp`) templates for clean separation of design and logic.
  - **GResource Bundling**: All UI assets and styling compiled into high-performance GResource binaries.
  - **Async Threading**: All NordVPN CLI interactions run in non-blocking background threads to ensure a responsive GUI.
  - **XDG Compliance**: User configuration persisted in `~/.config/summit/config.json`.

- **Standards & Quality**:
  - **Global Development Manifest v2.1**: Adheres to high-tier professional standards for environment, coding, and automated workflows.
  - **Logical Atomic Protocol**: Clean, milestone-based git history for maximum stability and bisectability.

## Requirements

- Linux (Native Debian/LMDE or universal Flatpak)
- NordVPN CLI (`nordvpn`) installed and logged in
- Python 3.11+ (for source builds)
- GTK 4.0 & PyGObject

## Installation

### 1. From .deb Package (Native Debian/LMDE)
Download the latest release from the `dist/` folder or the Releases page.

```bash
sudo dpkg -i dist/summit_0.8.1_all.deb
sudo apt-get install -f  # Resolve any missing dependencies
summit
```

### 2. From Flatpak (Universal Linux)
Summit supports sandboxed distribution via Flatpak.

```bash
# Build and install locally
bash build.sh flatpak
flatpak run io.github.summit
```

### 3. From Source (Development)
The project uses **`uv`** for modern Python dependency management.

```bash
# Install system build dependencies
sudo apt-get install blueprint-compiler libgirepository-2.0-dev libcairo2-dev

# Sync environment and run
uv sync
bash build.sh  # Compiles Blueprints and GResources
uv run python src/main.py
```

## NordVPN Setup

```bash
# Install NordVPN CLI (Official)
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
│   ├── ui/                  # Blueprint (.blp) UI templates
│   ├── resources/           # CSS styles and GResource manifests
│   ├── main.py              # Application entry point & GResource loading
│   ├── summit_manager.py    # Decoupled NordVPN CLI wrapper
│   └── *_pane.py            # Modular UI components (Template-based)
├── debian/                  # Debian packaging metadata
├── dist/                    # Production build artifacts (.deb)
├── io.github.summit.json    # Flatpak manifest
├── pyproject.toml           # Modern Python metadata (uv/ruff)
├── build.sh                 # Unified Debian/Flatpak build script
└── README.md                # This file
```

## Support This Project

If you find Summit useful, your support helps fund new projects and continuous improvements.

**[Buy me a coffee ☕](https://ko-fi.com/wolf792280)**

## License

MIT License + Commons Clause. Free for personal use. Commercial use requires written permission from the copyright holder. See [LICENSE](LICENSE) for full terms.
