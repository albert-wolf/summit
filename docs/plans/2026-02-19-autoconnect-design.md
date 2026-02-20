# Auto-Connect Feature Design

**Date**: 2026-02-19
**Status**: Approved

## Overview

Add an Auto-Connect feature to NordGUI that allows users to automatically connect to a VPN server on app startup. Users can toggle auto-connect ON/OFF and optionally specify a country/city. When disabled, a default/last connection is used.

## Requirements

1. Add Auto-Connect toggle + country/city dropdowns to Settings tab
2. Dropdowns displayed inline on same line as toggle
3. Dropdowns optional (user can enable toggle without selecting country/city)
4. Persist auto-connect state and country/city selection to config file
5. Load and restore settings on app startup
6. Send appropriate NordVPN CLI commands to enable/disable auto-connect

## Design: Auto-Connect UI

### Settings Tab Layout

Auto-Connect section added to Settings tab (alongside existing toggles):

```
[ ☑ ] Auto-Connect    Country: [Select Country ▼]    City: [Select City ▼]
```

### Behavior

**Toggle OFF (default):**
- Dropdowns are disabled/grayed out
- Auto-connect is inactive
- No NordVPN CLI commands are sent

**Toggle ON:**
- Dropdowns become active and editable
- User can leave dropdowns empty (auto-connect with default/last server)
- User can select country → city dropdown auto-populates
- When country is selected, save to config
- When city is selected, save to config

### Architecture

**UI Components:**
- Toggle switch (Gtk.Switch)
- Country dropdown (Gtk.ComboBoxText, populated from `nordvpn countries`)
- City dropdown (Gtk.ComboBoxText, populated dynamically from `nordvpn cities <country>`)

**Data Flow:**
1. On app startup: read config, load auto-connect state
2. If enabled, restore country/city selections and populate dropdowns
3. Set toggle state based on config
4. When user toggles: enable/disable dropdowns, send CLI command
5. When user selects country: populate city dropdown
6. When user selects city: save both to config

**NordVPN CLI Integration:**

Enable auto-connect (no country specified):
```bash
nordvpn settings autoconnect on
```

Enable auto-connect with specific country:
```bash
nordvpn settings autoconnect on --country "<country>"
```

Disable auto-connect:
```bash
nordvpn settings autoconnect off
```

Note: NordVPN CLI may not support `--country` in settings command. Behavior may be to just set autoconnect on, and user must use CLI separately to set country. Verify actual CLI behavior during implementation.

**Config Persistence:**

Store in `~/.config/nordgui/config.json`:
```json
{
  "autoconnect_enabled": false,
  "autoconnect_country": "",
  "autoconnect_city": ""
}
```

### Error Handling

- If country/city selection fails to save: show error toast
- If NordVPN CLI command fails: show error and revert toggle state
- If config file can't be written: log warning, don't crash

### Testing

1. Toggle auto-connect ON → verify CLI command is sent
2. Toggle auto-connect OFF → verify CLI command is sent
3. Select country with auto-connect ON → verify cities populate, config is saved
4. Select city → verify config is saved
5. Close and reopen app → verify settings are restored
6. Enable with no country selected → verify app connects with default

## Implementation Plan

See: `2026-02-19-autoconnect-plan.md`
