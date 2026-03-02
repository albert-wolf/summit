# Native Theme Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove libadwaita (Adw) import and custom CSS to let LMDE's native theme style the app.

**Architecture:** Delete all theme detection, CSS loading, and hardcoded color code. Keep only the window/app initialization. GTK4 will automatically apply system theme (Mint-Y, Arc, etc.) without any intervention.

**Tech Stack:** GTK4, Gtk.Settings for dark mode property detection (minimal, internal use only)

---

## Task 1: Remove Adw Import

**Files:**
- Modify: `src/main.py:16-22`

**Step 1: Verify current state**

Run: `grep -n "HAS_ADWAITA\|Adw" src/main.py`

Expected output shows:
```
16:try:
17:    gi.require_version('Adw', '1')
18:    from gi.repository import Adw
19:    HAS_ADWAITA = True
20:except (ValueError, ImportError):
21:    HAS_ADWAITA = False
```

**Step 2: Remove the Adw import block**

Replace lines 16-22 with nothing (delete entirely). The import section now ends at line 13.

New state: `from gi.repository import Gtk, Gio, GLib, Gdk` is the last import.

**Step 3: Verify removal**

Run: `grep -n "HAS_ADWAITA\|Adw" src/main.py`

Expected: No output (no matches found)

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove libadwaita (Adw) import from main.py"
```

---

## Task 2: Remove load_css() call and theme listener setup from do_startup()

**Files:**
- Modify: `src/main.py:56-68` (do_startup method)

**Step 1: Review current do_startup()**

Run: `sed -n '56,68p' src/main.py`

Expected: See `self.load_css()` on line 59 and Adw.StyleManager setup on lines 62-68.

**Step 2: Remove load_css() call**

Delete line 59: `self.load_css()`

**Step 3: Remove Adw.StyleManager listener setup**

Delete lines 62-68 (the entire try/except block that checks HAS_ADWAITA and connects to theme changes).

**Step 4: Verify changes**

Run: `sed -n '56,70p' src/main.py`

Expected: do_startup() should go straight from `Gtk.Application.do_startup(self)` to `if not self.window:` block, with no CSS or theme setup in between.

**Step 5: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove load_css() and Adw.StyleManager listener from do_startup()"
```

---

## Task 3: Remove load_css() method

**Files:**
- Modify: `src/main.py:121-186` (entire load_css method)

**Step 1: Verify method exists**

Run: `sed -n '121,186p' src/main.py | head -5`

Expected: Shows start of `def load_css(self):`

**Step 2: Delete entire load_css() method**

Remove all lines from 121-186 (the complete method definition).

**Step 3: Verify removal**

Run: `grep -n "def load_css" src/main.py`

Expected: No output (method completely removed)

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove load_css() method entirely"
```

---

## Task 4: Remove get_inline_css() method

**Files:**
- Modify: `src/main.py:187-201` (entire get_inline_css method)

**Step 1: Verify method exists**

Run: `grep -n "def get_inline_css" src/main.py`

Expected: Shows line number of method definition

**Step 2: Delete entire get_inline_css() method**

Remove all lines from method start to end (approximately 15 lines).

**Step 3: Verify removal**

Run: `grep -n "def get_inline_css" src/main.py`

Expected: No output (method completely removed)

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove get_inline_css() method"
```

---

## Task 5: Simplify get_is_dark_mode() method

**Files:**
- Modify: `src/main.py:252-280` (get_is_dark_mode method)

**Step 1: View current method**

Run: `sed -n '252,280p' src/main.py`

Expected: See complex logic with Adwaita checks, theme name checking, etc.

**Step 2: Replace with simplified version**

Replace the entire `get_is_dark_mode()` method with:

```python
def get_is_dark_mode(self) -> bool:
    """Detect if dark theme is active via GTK settings."""
    settings = Gtk.Settings.get_default()
    if settings:
        return settings.get_property("gtk-application-prefer-dark-theme") is True
    return False
```

This should be roughly 7-8 lines total.

**Step 3: Verify simplification**

Run: `sed -n '252,260p' src/main.py`

Expected: Shows the new simplified method that only uses Gtk.Settings

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor: simplify get_is_dark_mode() to use only Gtk.Settings"
```

---

## Task 6: Remove on_theme_changed() and helper methods

**Files:**
- Modify: `src/main.py` (remove on_theme_changed() and _reset_style_recursive())

**Step 1: Locate methods**

Run: `grep -n "def on_theme_changed\|def _reset_style_recursive" src/main.py`

Expected: Shows line numbers of both methods

**Step 2: Delete on_theme_changed() method**

Remove entire method (roughly 20-25 lines)

**Step 3: Delete _reset_style_recursive() helper**

Remove entire helper method (roughly 10-12 lines)

**Step 4: Verify removal**

Run: `grep -n "def on_theme_changed\|def _reset_style_recursive" src/main.py`

Expected: No output (both methods removed)

**Step 5: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove on_theme_changed() and _reset_style_recursive() methods"
```

---

## Task 7: Remove CSS class manipulation in build_window()

**Files:**
- Modify: `src/main.py:330-334` (build_window method, theme class setup)

**Step 1: View build_window() setup**

Run: `sed -n '320,335p' src/main.py`

Expected: See CSS class application: `if not is_dark_mode: self.window.add_css_class("light-theme")`

**Step 2: Remove dark mode class setup**

Delete lines that check `is_dark_mode` and apply CSS classes:
```python
is_dark_mode = self.get_is_dark_mode()
if not is_dark_mode:
    self.window.add_css_class("light-theme")
```

**Step 3: Verify removal**

Run: `sed -n '320,335p' src/main.py`

Expected: No theme class setup in build_window()

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove CSS class application from build_window()"
```

---

## Task 8: Remove CSS reapplication from on_activate()

**Files:**
- Modify: `src/main.py:112-120` (on_activate method)

**Step 1: View on_activate() method**

Run: `sed -n '112,120p' src/main.py`

Expected: See `GLib.idle_add(self.reapply_css)` call

**Step 2: Remove reapply_css idle_add**

Delete line: `GLib.idle_add(self.reapply_css)`

**Step 3: Verify removal**

Run: `grep -n "reapply_css" src/main.py`

Expected: No output (all references removed)

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove CSS reapplication from on_activate()"
```

---

## Task 9: Remove reapply_css() method

**Files:**
- Modify: `src/main.py` (remove reapply_css method)

**Step 1: Locate method**

Run: `grep -n "def reapply_css" src/main.py`

Expected: Shows line number

**Step 2: Delete reapply_css() method**

Remove entire method (roughly 3-4 lines)

**Step 3: Verify removal**

Run: `grep -n "def reapply_css" src/main.py`

Expected: No output (method removed)

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove reapply_css() method"
```

---

## Task 10: Remove CSS class manipulation from build_headerbar()

**Files:**
- Modify: `src/main.py` (build_headerbar method, theme class setup)

**Step 1: View build_headerbar() setup**

Run: `grep -n "is_dark_mode\|dark-mode\|light-mode" src/main.py | tail -20`

Expected: Shows CSS class additions in build_headerbar()

**Step 2: Remove theme detection and class setup from build_headerbar()**

Delete approximately lines with:
```python
is_dark_mode = self.get_is_dark_mode()
if is_dark_mode:
    header.add_css_class("dark-mode")
else:
    header.add_css_class("light-mode")
```

Also remove the debug print and queue_draw if they're theme-related.

**Step 3: Verify removal**

Run: `grep -n "dark-mode\|light-mode" src/main.py`

Expected: No output (all CSS class manipulation removed)

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor: remove CSS class application from build_headerbar()"
```

---

## Task 11: Check for and delete style.css file

**Files:**
- Delete: `style.css` (if exists)

**Step 1: Check if style.css exists**

Run: `find /home/wolf/Projects/Summit -name "style.css" -type f`

**Step 2a: If file exists, delete it**

Run: `rm style.css` (from repo root)

Then: `git add -A && git commit -m "refactor: remove custom style.css"`

**Step 2b: If file doesn't exist, skip**

Run: `grep -r "style.css" /home/wolf/Projects/Summit/src`

Expected: No matches (no references to custom CSS file)

**Step 3: Verify**

Run: `grep -r "load_from_path\|\.css" src/main.py`

Expected: No output (no CSS file loading)

---

## Task 12: Manual verification and test

**Files:**
- Test: Run app and verify theming works

**Step 1: Run app from source**

```bash
cd /home/wolf/Projects/Summit
python3 src/main.py
```

**Expected:**
- App window appears
- Colors match LMDE's current theme (light or dark)
- No hardcoded Summit colors
- Headerbar uses system theme
- All widgets (buttons, text, scrollbars) use system theme

**Step 2: Check for runtime errors**

Expected: No errors about `Adw`, `HAS_ADWAITA`, `load_css`, or missing CSS files.

**Step 3: Verify dark mode detection still works (optional internal logic test)**

If dark mode detection is still needed for internal logic, verify it works:
- Check system theme (e.g., `gsettings get org.gnome.desktop.interface gtk-application-prefer-dark-theme`)
- Confirm `get_is_dark_mode()` returns expected value

**Step 4: Close app**

`Ctrl+C` or close window

---

## Task 13: Build and test .deb package

**Files:**
- Build: Create summit_1.0.0_all.deb

**Step 1: Run build script**

```bash
cd /home/wolf/Projects/Summit
./build.sh
```

Expected: `summit_1.0.0_all.deb` created in repo root.

**Step 2: Install the package**

```bash
sudo dpkg -i summit_1.0.0_all.deb
```

Expected: Package installs successfully, no errors.

**Step 3: Launch installed version**

```bash
summit
```

Expected:
- App launches
- Theming matches system theme (Mint-Y, Arc, etc.)
- No hardcoded colors
- Smooth integration with desktop

**Step 4: Verify theme switching**

Switch system theme (via LMDE Settings → Appearance) and relaunch app.

Expected: App respects new theme immediately.

**Step 5: Commit**

```bash
git add -A
git commit -m "build: update summit package after theme refactor"
```

---

## Task 14: Final cleanup and commit summary

**Files:**
- Verify: All changes committed

**Step 1: Check git status**

Run: `git status`

Expected: "nothing to commit, working tree clean"

**Step 2: Review commit log**

Run: `git log --oneline -10`

Expected: See all refactoring commits in order, no uncommitted changes.

**Step 3: Verify no Adw references remain**

Run: `grep -r "Adw\|HAS_ADWAITA\|load_css\|style\.css" src/`

Expected: No output (all references removed)

**Step 4: Final summary**

All tasks complete. Summit now uses native LMDE theming without any custom CSS or libadwaita forcing.

---

## Rollback Plan

If issues arise at any point:

```bash
# Revert the entire refactor
git log --oneline -15  # Find the commit before theme work started
git reset --hard <commit-hash>  # Go back to that commit
sudo dpkg -i summit_1.0.0_all.deb  # Reinstall previous version
```

---

## Key Changes Summary

| Removed | Lines | Reason |
|---------|-------|--------|
| `Adw` import | 16-22 | Forcing libadwaita theme |
| `load_css()` setup in do_startup | 59, 62-68 | No custom CSS loading |
| `load_css()` method | 121-186 | Entire method unused |
| `get_inline_css()` method | 187-201 | No inline CSS fallback |
| `on_theme_changed()` method | ~282-318 | No runtime theme changes needed |
| `_reset_style_recursive()` method | ~307-318 | Helper for theme changes |
| `reapply_css()` method | ~633-636 | CSS no longer applied |
| CSS class setup in `build_window()` | ~330-334 | Let GTK handle styling |
| CSS class setup in `build_headerbar()` | ~544-549 | Let GTK handle styling |
| `style.css` file | — | Custom CSS removed |

| Kept | Purpose |
|------|---------|
| `get_is_dark_mode()` simplified | Internal use only, minimal logic |
| GTK4 imports and initialization | Core app functionality |
| Window/app building | GTK4 handles styling automatically |

