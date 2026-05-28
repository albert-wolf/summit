# Summit Changelog

## v0.9.2 - Hybrid Polling Migration & Efficiency Overhaul

### Features & Architecture
- **Event-Driven Status Updates**: Migrated background daemon status polling from a constant 2-second interval to a native event-driven pattern using `Gio.NetworkMonitor`. Status updates are triggered instantaneously upon any network interface transitions (e.g. connecting/disconnecting the VPN).
- **Focus-Based Active Throttling**: Added support for tracking window focus states (`notify::is-active` property). Active status polling is paused completely when the application window is minimized or defocused, conserving CPU cycles.
- **Safety Buffering**: Registered a relaxed 10-second (10000ms) safety timer that runs ONLY when the application is active and focused, with concurrent-execution lock protections preventing duplicate polling subprocesses.
- **Clean Quality Compliance**: Replaced all remaining raw stdout `print()` statements with standard `logging` levels (`logger.info`/`logger.error`) across the codebase.

## v0.9.1 - Reconnect Location Targeting Fix

### Fixes & Improvements
- **Explicit Reconnect Targeting**: The "Reconnect" button now reconnects to the exact country and city you were last connected to, bypassing the NordVPN daemon's dynamic recommendation engine.
- **Location Persistence**: Automatically captures and stores the last successful connection's city and country (`last_country` and `last_city`) in the local `config.json` upon connecting.
- **Backwards Compatibility**: Safely falls back to bare `nordvpn connect` (dynamic recommendation) if no previous session location exists in configuration.

## v0.9.0 - Status Tab Redesign & Integrated Dashboard

### Features & UI Updates
- **Complete Redesign**: The Status tab is now a centralized dashboard with a modern, high-impact aesthetic.
- **Dynamic Hero Section**: Real-time status icons (Unsecured/Connected) with pulsing animations and large, bold status labels.
- **Telemetry Dashboard**: Added "Network State" and "Session State" cards for at-a-glance connection details (IP, Protocol, Server ID, Uptime, Transfer).
- **Integrated Lists**: Favorites and Recent connections are now directly accessible within the Status tab via a segmented control (FAVORITES | RECENT).
- **Programmatic UI**: Transitioned the Status pane to a pure Python implementation, following modern GTK4 patterns and improving codebase maintainability.
- **Layout Optimization**: Removed the redundant right-side Recent sidebar, allowing more horizontal space for all tabs and a cleaner, focused layout.

### Technical Improvements
- Migrated history and favorites management logic from `RecentPane` to `StatusPane`.
- Updated `style.css` with dedicated classes for telemetry cards, hero animations, and list row cards.
- Cleaned up `main.py` and `main_window.blp` to remove legacy sidebar and Paned layout logic.

## v0.8.4 - Auto-connect & Parsing Fixes (Current)

### Fixes Applied
- **Fixed**: NordVPN CLI `set autoconnect` command now correctly handles multi-word locations (e.g., "United States Saint Louis").
- **Fixed**: Correctly parse multi-word country/city names by splitting arguments before execution.
- **Improved**: UI/UX stability on LMDE/Cinnamon; purified CSS and explicitly declared WindowControls to ensure native theme inheritance and eliminate visual artifacts.

## v0.8.3 - Meshnet Stability & Interface Optimization
  - `Kill Switch` → `killswitch`
  - `Auto-connect` → `autoconnect`
  - `LAN Discovery` → `lan-discovery`
  - `Virtual Location` → `virtual-location`
  - `Threat Protection Lite` → `threatprotectionlite`
- **Fixed**: Technology dropdown now works correctly (reconnect required for effect)
- **Fixed**: Protocol dropdown now works correctly (disconnection required for effect)
- **Improved**: Switches disabled while command executes
- **Improved**: Switches revert on command failure

#### Ports Tab
- **Fixed**: All allowlisted ports now display correctly (including "Both" UDP|TCP)
- **Fixed**: Port parsing now handles multi-line port blocks
- **Fixed**: Removed right-click context menu, added inline remove buttons
- **Fixed**: Port removal now works for both-protocol ports (no protocol specified)
- **Improved**: Add port form now defaults to "Both" (both TCP and UDP)
- **Improved**: Each port row shows port + remove button in horizontal layout

#### Meshnet Tab
- **Fixed**: Initial toggle state now loads correctly from settings on startup
- **Improved**: Changed to 3-pane layout:
  1. This Device - local device information
  2. Connected Peers - currently connected meshnet devices
  3. Disconnected Peers - available but disconnected devices
- **Improved**: Graceful handling when meshnet is disabled
- **Improved**: Better peer organization and display

#### Status Tab
- ✅ Real-time status polling (every 2 seconds)
- ✅ Detects disconnects from external sources
- **Note**: Polling interval is 2 seconds, so external disconnects may take up to 2 seconds to appear in UI

#### Visual Improvements
- **Added**: Dark pane backgrounds (#0f0f0f) for better visual hierarchy
- **Added**: 1px borders around panes for visual separation
- **Added**: Dim labels for secondary information
- **Added**: Better spacing and margins in all panes

### Technical Improvements

#### nord_manager.py
- Fixed command syntax for `set_setting()` with proper command name mapping
- Fixed `add_port()` and `remove_port()` to use correct NordVPN syntax:
  - Format: `allowlist add port <port> [protocol <protocol>]`
  - "Both" omitted when no protocol specified
- Fixed `_parse_kv_output()` to handle lines ending with `:` (no value)
- Fixed `get_meshnet_peers()` to check meshnet status from settings first

#### main.py
- Added `load_initial_pane_data()` to load all pane states before showing window
- Ensures toggles and settings show correct state on startup

#### settings_pane.py
- Switches now disabled during command execution
- Removed automatic reload after every toggle
- Toggles revert on command failure

#### ports_pane.py
- Replaced right-click context menu with inline remove buttons
- Each port row now has horizontal layout: port label + remove button
- Port removal simplified to always use "both protocols" removal

#### meshnet_pane.py
- Complete redesign with 3-pane layout
- Auto-fetches device information from `nordvpn meshnet peer this`
- Better peer categorization

#### style.css
- Added `.pane-box` class with dark background and borders
- Added `dim-label` class for secondary text
- Updated `listbox` styling

### Known Limitations
- Protocol setting may require reconnection to take effect (NordVPN limitation)
- Meshnet features require meshnet to be enabled and configured
- External disconnects detected on next polling cycle (max 2 seconds)

### Installation
```bash
sudo dpkg -i nordgui_1.0.0_all.deb
sudo apt-get install -f  # Install dependencies if needed
nordgui
```

### Testing Verified
✓ Settings load correct initial state on startup
✓ All toggles work without reverting
✓ Technology and Protocol changes apply (with reconnect)
✓ All ports display correctly
✓ Port removal works for all protocol types
✓ Meshnet state loads correctly
✓ Status detects external disconnects
✓ Dark theme renders correctly
