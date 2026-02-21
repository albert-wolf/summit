# Summit UX Improvements Design

**Date**: 2026-02-21
**Scope**: 7 feature improvements across search, errors, favorites, and UI polish

---

## Features Overview

### 1. Toast Notifications System
Overlay widget for error/success feedback. Any pane can trigger via `self.app.show_toast(message, is_error=False)`. Auto-dismiss: success after 3s, errors after 5s.

### 2. Country/City Search Filter
Text entry at top of Servers tab. Real-time case-insensitive substring filtering of both country and city listboxes. Non-persistent state (resets on tab switch).

### 3. Favorites System
- **Storage**: New `favorites` list in config.json: `[{country, city}, ...]`
- **UI**: New "Favorites" section in sidebar (above Recent Connections)
- **Adding**: Star icon/button next to city selection in Servers tab
- **Removing**: Right-click a favorite row to remove it
- **Deduplication**: Same favorite can't appear twice
- **Highlight**: Current connected server appears bold in both Favorites and Recent lists

### 4. Settings Tab Organization
Group toggles by function with bold section headers:
- **Connection**: Kill Switch, Firewall, Auto-connect
- **Privacy**: Obfuscate, IPv6 Leak Protection
- **Features**: Notify, Tray
- **Advanced**: (reserved for future)

### 5. Current Connection Highlight
In sidebar (Favorites and Recent lists), the server you're currently connected to appears bold/highlighted. Implemented by comparing `current_server` from `update_status()` against each row's entry.

### 6. Better Error Messages
Capture error messages from `self.nord.connect()` and other operations. Show in toast: `"Failed to connect: {error_message}"`. All failures (disconnect, connect, etc.) get user-visible feedback.

### 7. Connection Spinner
- **Status pane**: Spinner icon next to status indicator while connecting
- **Recent/Favorites rows**: Small spinner overlay on row being clicked while connecting
- **Auto-dismiss**: Spinner stops when connection succeeds or fails (status updates)
- **Error**: Failed connections trigger error toast with message

---

## Data Model Changes

### config.json additions:
```json
{
  ...existing fields...,
  "favorites": [
    {"country": "United_States", "city": "Saint_Louis"},
    {"country": "United_Kingdom", "city": "London"}
  ]
}
```

---

## Component Changes

| Component | Changes |
|-----------|---------|
| `main.py` | Add ToastOverlay widget, expose `show_toast()` method |
| `servers_pane.py` | Add SearchEntry at top, add star button for favorites, filter logic |
| `recent_pane.py` | Add Favorites section, highlight current server, clickable star/remove |
| `status_pane.py` | Add spinner during connect/reconnect, show connection errors in toast |
| `settings_pane.py` | Group toggles with section headers |

---

## Implementation Priority

1. **Toast system** — foundational for all error feedback
2. **Search filter** — straightforward, no dependencies
3. **Settings organization** — pure UI restructuring
4. **Favorites** — config storage + sidebar UI
5. **Current connection highlight** — leverages existing update_status()
6. **Error messages** — use toast system, update all connect handlers
7. **Connection spinner** — polish layer, uses existing status polling

---

## Testing Checklist

- [ ] Toast appears/dismisses on schedule for success and error
- [ ] Search filters countries and cities independently
- [ ] Favorite can be added from Servers tab, appears in sidebar
- [ ] Favorite can be removed, doesn't reappear
- [ ] Same favorite can't be added twice
- [ ] Current connected server highlights in sidebar
- [ ] Clicking favorite/recent connection shows spinner and error (if fails)
- [ ] All failed operations show error toast with message
- [ ] Settings groups display correctly with headers
- [ ] Config loads/saves favorites correctly across restarts
