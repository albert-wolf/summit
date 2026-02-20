# Cities Double-Click Connect Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable users to connect to VPN by double-clicking a city in the Servers tab, with "Connecting..." feedback in the button.

**Architecture:** Extract shared connection logic into `_do_connect(country, city)` method. Both button click and city double-click call this method, eliminating duplication and ensuring consistent behavior.

**Tech Stack:** GTK4 (Python), threading with GLib.idle_add(), nord_manager command execution

---

## Task 1: Extract Shared Connection Method

**Files:**
- Modify: `src/servers_pane.py:148-171` (on_connect_clicked method)
- Add: new `_do_connect()` method before on_connect_clicked

**Step 1: Create the `_do_connect()` method**

Insert this new method before `on_connect_clicked()` (around line 148):

```python
def _do_connect(self, country, city=None):
    """Shared connection logic for button and double-click handlers.

    Args:
        country: Country to connect to
        city: Optional city to connect to (if None, connects to country)
    """
    if not country:
        return

    self.connect_btn.set_sensitive(True)  # Keep button enabled
    self.connect_btn.set_label("Connecting...")

    def worker():
        success, message = self.nord.connect(country, city)
        GLib.idle_add(self.on_connect_done, success, message, self.connect_btn)

    import threading
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
```

**Step 2: Refactor `on_connect_clicked()` to use `_do_connect()`**

Replace the entire `on_connect_clicked()` method (lines 148-165) with:

```python
def on_connect_clicked(self, button):
    """Connect to selected country/city."""
    self._do_connect(self.selected_country, self.selected_city)
```

**Step 3: Verify syntax**

Run: `python3 -m py_compile src/servers_pane.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add src/servers_pane.py
git commit -m "refactor: extract shared connection logic into _do_connect()"
```

---

## Task 2: Add Double-Click Signal Handler

**Files:**
- Modify: `src/servers_pane.py` (add signal connection + handler)

**Step 1: Add signal connection during initialization**

In `__init__()` method, after line 59 where cities_listbox signals are connected, add:

```python
self.cities_listbox.connect("row-activated", self.on_city_row_activated)
```

Location: After line 59 (`self.cities_listbox.connect("row-selected", self.on_city_selected)`)

**Step 2: Implement the `on_city_row_activated()` handler**

Add this new method after `on_city_selected()` (around line 146):

```python
def on_city_row_activated(self, listbox, row):
    """Handle double-click on city to connect directly."""
    if row and self.selected_country:
        city_label = row.get_child()
        city = city_label.get_label()
        self._do_connect(self.selected_country, city)
```

**Step 3: Verify syntax**

Run: `python3 -m py_compile src/servers_pane.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add src/servers_pane.py
git commit -m "feat: add double-click handler to connect to city"
```

---

## Task 3: Integration Testing

**Files:**
- Test: Create synthetic test in `/tmp/test_double_click.py`

**Step 1: Create test script**

```python
#!/usr/bin/env python3
"""Test double-click to connect functionality."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import sys
sys.path.insert(0, 'src')

from servers_pane import ServersPane
from nord_manager import NordManager

def test_double_click_connection():
    """Verify double-click signal handler works correctly."""

    nord = NordManager()
    pane = ServersPane(nord)

    # Load test data
    test_countries = ["Afghanistan", "Albania"]
    pane.on_countries_loaded(test_countries)

    # Select first country
    first_country_row = pane.countries_listbox.get_row_at_index(0)
    pane.on_country_selected(pane.countries_listbox, first_country_row)

    # Load test cities
    test_cities = ["Kabul", "Kandahar"]
    pane.on_cities_loaded(test_cities)

    # Verify cities loaded
    first_city_row = pane.cities_listbox.get_row_at_index(0)
    assert first_city_row is not None, "Cities not loaded"

    # Simulate double-click on first city
    print("✓ Simulating double-click on city...")
    pane.on_city_row_activated(pane.cities_listbox, first_city_row)

    # Verify button shows "Connecting..."
    assert pane.connect_btn.get_label() == "Connecting...", \
        f"Expected 'Connecting...', got '{pane.connect_btn.get_label()}'"

    print("✓ Button shows 'Connecting...'")
    print("✓ All tests passed!")

if __name__ == "__main__":
    test_double_click_connection()
```

**Step 2: Run the test**

Run: `python3 /tmp/test_double_click.py`
Expected: All tests passed message

**Step 3: Manual verification with app**

Run the app and verify:
- Select a country (cities appear)
- Double-click a city
- Button changes to "Connecting..."
- Button remains enabled
- After connection, button returns to "Connect to Selected"

---

## Task 4: Build and Package

**Files:**
- Build: `build.sh` (existing)

**Step 1: Build the package**

Run: `bash build.sh 2>&1 | tail -20`
Expected: Build complete, nordgui_1.0.0_all.deb created

**Step 2: Verify package contents**

Run: `dpkg -c nordgui_1.0.0_all.deb | grep servers_pane.py`
Expected: Shows servers_pane.py in package

**Step 3: Commit build artifacts**

```bash
git status
```
Note: Only commit .py changes, not .deb or __pycache__

---

## Task 5: Final Verification and Commit

**Files:**
- Verify: `src/servers_pane.py` changes

**Step 1: Review all changes**

Run: `git diff src/servers_pane.py | head -100`
Expected: Shows:
- New `_do_connect()` method
- Refactored `on_connect_clicked()`
- New `on_city_row_activated()` handler
- New signal connection in `__init__()`

**Step 2: Final test with installed package**

```bash
sudo dpkg -i nordgui_1.0.0_all.deb
nordgui
```

Verify:
- Open Servers tab
- Select a country
- Double-click a city
- Button shows "Connecting..."
- Connection initiates
- Button returns to normal

**Step 3: Final commit**

```bash
git log --oneline -5
```
Expected: Shows recent commits for refactor and feature

---

## Success Criteria

✓ Double-click on city triggers connection
✓ Button shows "Connecting..." during connection
✓ Button remains enabled (not disabled)
✓ Button text returns to "Connect to Selected" after connection
✓ No duplication of connection logic
✓ Works with both button click and double-click
✓ All code compiles without errors
✓ Package builds successfully
