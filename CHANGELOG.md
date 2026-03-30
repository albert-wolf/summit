# Summit Changelog

## v0.8.3 - Meshnet Stability & Interface Optimization (Current)

### Features Implemented
- ✅ **Meshnet UX Refactor**: Removed the redundant Meshnet toggle from the Settings pane to streamline the interface and establish the Meshnet tab as the single source of truth.
- ✅ **Cross-Pane Synchronization**: Improved state persistence and notification logic to ensure the Meshnet UI is always accurate.
- ✅ **Automatic Tab Refresh**: Relevant tabs now automatically refresh their data from the CLI when selected.
- ✅ **Increased Command Timeout**: Increased NordVPN CLI timeout to 30s to accommodate slow Meshnet initialization.

### Fixes Applied
- **Fixed**: Theme synchronization; application now correctly respects system Light/Dark mode settings (LMDE/Cinnamon/Ubuntu).
- **Fixed**: Signal loop when Meshnet toggle failed and reverted.
- **Improved**: UI stability during concurrent state updates and background polling.

## v0.8.2 - Cross-Platform Compatibility & Theming
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
