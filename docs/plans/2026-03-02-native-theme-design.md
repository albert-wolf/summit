# Native Theme Implementation Design

**Date:** 2026-03-02
**Project:** Summit NordVPN GTK4 Client
**Status:** Design Approved

## Problem Statement

Summit was forcing libadwaita (Adw) theming, which overrides LMDE's native system theme (Mint-Y, Arc, etc.). This breaks theme consistency with the rest of the desktop and prevents users from using their preferred LMDE theme.

Similar issue was fixed in Quarry by removing the Adw import and using native GTK4 theming instead.

## Solution Overview

Remove all custom theming infrastructure and hardcoded colors. Let GTK4 and LMDE's system theme handle all styling automatically.

## Architecture Changes

### Removals

**From `src/main.py`:**
- Lines 16-22: Entire Adw (libadwaita) import block
- Lines 59, 62-68: `load_css()` call and Adw.StyleManager theme listener setup
- Lines 121-186: Complete `load_css()` method
- Lines 189-201: `get_inline_css()` method
- Lines 282-318: `on_theme_changed()` method and `_reset_style_recursive()` helper
- Lines 118-119: CSS reapplication in `on_activate()`
- Lines 633-636: `reapply_css()` method
- Lines 290-302: CSS class manipulation in `on_theme_changed()`
- Lines 330-334: CSS class application in `build_window()`
- Lines 544-549: CSS class application in `build_headerbar()`

**Files to Delete:**
- `style.css` (if it exists in the repo)
- Any CSS-related files in debian/ or config directories

### Simplifications

**Dark mode detection** — Replace all the theme detection logic with a single simple method:

```python
def get_is_dark_mode(self) -> bool:
    """Detect if dark theme is active via GTK settings."""
    settings = Gtk.Settings.get_default()
    if settings:
        return settings.get_property("gtk-application-prefer-dark-theme") is True
    return False
```

This method can remain in the code if needed for any internal logic, but won't be used for CSS application.

### No Custom Styling

- All hardcoded colors (#222226, #ebebed, #1a1a1a, etc.) are removed
- No CSS providers or style context manipulation
- GTK4 applies system theme automatically to all widgets

## Expected Behavior

1. **Light Mode (LMDE Light)**: App renders with light theme colors (light background, dark text)
2. **Dark Mode (LMDE Dark)**: App renders with dark theme colors (dark background, light text)
3. **Theme Switching**: Switching system theme immediately applies to app (no restart needed)
4. **Consistency**: App looks identical to other GTK4 apps on the system

## Testing Plan

**Test Cases:**
1. Launch app with LMDE's light theme (e.g., Mint-Y) → verify light colors apply
2. Launch app with LMDE's dark theme (e.g., Mint-Y-Dark) → verify dark colors apply
3. Switch system theme while app is running → verify app updates in real-time
4. Verify all widgets (headerbar, buttons, text, scrollbars) use system theme
5. Check that app integrates visually with other system apps

## Files Modified

- `src/main.py` — Remove ~200 lines of theme/CSS code

## Files Deleted

- `style.css` (if it exists)

## Rollback

If this causes issues:
1. Revert the commit
2. Reinstall previous version: `sudo dpkg -i summit_1.0.0_all.deb`

## Notes

- This approach matches the successful fix applied to Quarry
- Adw import is the culprit, not GTK4 itself
- Gtk.Settings dark mode property detection still works for any internal logic
- No loss of functionality—only removal of forced styling
