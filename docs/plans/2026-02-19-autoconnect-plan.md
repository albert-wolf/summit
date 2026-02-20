# Auto-Connect Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Auto-Connect toggle + country/city dropdowns to Settings tab, allowing users to auto-connect to VPN on app startup.

**Architecture:** Add UI components to settings_pane.py, wire toggle to enable/disable dropdowns, load/save auto-connect state to config.json, send NordVPN CLI commands to enable/disable auto-connect.

**Tech Stack:** GTK4 (Gtk.Switch, Gtk.ComboBoxText), Nord Manager CLI wrapper, config.json persistence

---

## Task 1: Add Auto-Connect UI Components to Settings Tab

**Files:**
- Modify: `src/settings_pane.py:1-50` (imports and __init__)

**Step 1: Review current settings_pane structure**

Run: `grep -n "class SettingsPane\|self.switches\|def __init__" src/settings_pane.py | head -20`

Expected: Shows the class structure, how switches are created and stored

**Step 2: Add auto-connect UI components after last switch**

In `src/settings_pane.py`, find the last switch in `__init__` method (around line 50-80), then add this code after it:

```python
        # Auto-Connect section
        autoconnect_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.autoconnect_switch = Gtk.Switch()
        self.autoconnect_switch.connect("notify::active", self.on_autoconnect_toggled)
        autoconnect_label = Gtk.Label(label="Auto-Connect")
        autoconnect_label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        autoconnect_label_box.append(autoconnect_label)
        autoconnect_label_box.set_size_request(150, -1)
        autoconnect_box.append(autoconnect_label_box)
        autoconnect_box.append(self.autoconnect_switch)

        # Country dropdown
        self.autoconnect_country_combo = Gtk.ComboBoxText()
        self.autoconnect_country_combo.set_sensitive(False)
        self.autoconnect_country_combo.connect("changed", self.on_autoconnect_country_changed)
        self.autoconnect_country_combo.append("", "Select Country")
        autoconnect_box.append(self.autoconnect_country_combo)

        # City dropdown
        self.autoconnect_city_combo = Gtk.ComboBoxText()
        self.autoconnect_city_combo.set_sensitive(False)
        self.autoconnect_city_combo.connect("changed", self.on_autoconnect_city_changed)
        self.autoconnect_city_combo.append("", "Select City")
        autoconnect_box.append(self.autoconnect_city_combo)

        self.settings_grid.attach(autoconnect_box, 0, 7, 2, 1)
```

**Step 3: Verify syntax**

Run: `python3 -m py_compile src/settings_pane.py && echo "✓ Syntax valid"`

Expected: ✓ Syntax valid

---

## Task 2: Implement Auto-Connect Signal Handlers

**Files:**
- Modify: `src/settings_pane.py` (add methods at end of class)

**Step 1: Add on_autoconnect_toggled handler**

Add this method to the SettingsPane class (before the last line):

```python
    def on_autoconnect_toggled(self, switch, param):
        """Handle auto-connect toggle."""
        enabled = switch.get_active()

        # Enable/disable dropdowns
        self.autoconnect_country_combo.set_sensitive(enabled)
        self.autoconnect_city_combo.set_sensitive(enabled)

        # Send CLI command
        if enabled:
            success, message = self.nord.run_command(["settings", "autoconnect", "on"])
        else:
            success, message = self.nord.run_command(["settings", "autoconnect", "off"])

        # Save config
        if hasattr(self, 'save_config'):
            self.save_config()
```

**Step 2: Add country dropdown handler**

Add this method:

```python
    def on_autoconnect_country_changed(self, combo):
        """Handle country selection change."""
        country = combo.get_active_text()

        if not country:
            self.autoconnect_city_combo.remove_all()
            self.autoconnect_city_combo.append("", "Select City")
            return

        # Populate cities for selected country
        def worker():
            cities = self.nord.get_cities(country)
            GLib.idle_add(self.populate_autoconnect_cities, cities)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        # Save config
        if hasattr(self, 'save_config'):
            self.save_config()

    def populate_autoconnect_cities(self, cities):
        """Populate city dropdown."""
        self.autoconnect_city_combo.remove_all()
        self.autoconnect_city_combo.append("", "Select City")
        for city in cities:
            self.autoconnect_city_combo.append(city, city)
        return False
```

**Step 3: Add city dropdown handler**

Add this method:

```python
    def on_autoconnect_city_changed(self, combo):
        """Handle city selection change."""
        # Save config
        if hasattr(self, 'save_config'):
            self.save_config()
```

**Step 4: Verify syntax**

Run: `python3 -m py_compile src/settings_pane.py && echo "✓ Syntax valid"`

Expected: ✓ Syntax valid

---

## Task 3: Load Auto-Connect Config on Startup

**Files:**
- Modify: `src/settings_pane.py:load_settings()` method
- Modify: `src/main.py:build_window()` or `on_activate()` method

**Step 1: Find where settings are loaded**

Run: `grep -n "def load_settings\|def on_activate\|def build_window" src/main.py | head -10`

Expected: Shows where initial settings are loaded

**Step 2: Add auto-connect config keys to main.py**

In `src/main.py`, find where config is initialized (around line 150-170), ensure these keys exist:

```python
        # Add to config defaults if not present
        if "autoconnect_enabled" not in self.config:
            self.config["autoconnect_enabled"] = False
        if "autoconnect_country" not in self.config:
            self.config["autoconnect_country"] = ""
        if "autoconnect_city" not in self.config:
            self.config["autoconnect_city"] = ""
```

**Step 3: Load auto-connect state into UI**

In `src/main.py`, after creating `settings_pane`, add:

```python
        # Load auto-connect state
        self.settings_pane.autoconnect_switch.set_active(self.config.get("autoconnect_enabled", False))

        # Populate countries
        countries = self.nord.get_countries()
        self.settings_pane.autoconnect_country_combo.remove_all()
        self.settings_pane.autoconnect_country_combo.append("", "Select Country")
        for country in countries:
            self.settings_pane.autoconnect_country_combo.append(country, country)

        # Restore country selection
        saved_country = self.config.get("autoconnect_country", "")
        if saved_country:
            self.settings_pane.autoconnect_country_combo.set_active_id(saved_country)
            cities = self.nord.get_cities(saved_country)
            self.settings_pane.autoconnect_city_combo.remove_all()
            self.settings_pane.autoconnect_city_combo.append("", "Select City")
            for city in cities:
                self.settings_pane.autoconnect_city_combo.append(city, city)
            saved_city = self.config.get("autoconnect_city", "")
            if saved_city:
                self.settings_pane.autoconnect_city_combo.set_active_id(saved_city)
```

**Step 4: Verify syntax**

Run: `python3 -m py_compile src/main.py && echo "✓ Syntax valid"`

Expected: ✓ Syntax valid

---

## Task 4: Implement Config Save Logic

**Files:**
- Modify: `src/settings_pane.py` (add save_config method)
- Modify: `src/main.py` (wire up save_config)

**Step 1: Add save_config method to SettingsPane**

Add this to SettingsPane class:

```python
    def set_save_config_callback(self, callback):
        """Set callback for saving config (called from main.py)."""
        self.save_config = callback

    def get_autoconnect_config(self):
        """Return current auto-connect config."""
        return {
            "autoconnect_enabled": self.autoconnect_switch.get_active(),
            "autoconnect_country": self.autoconnect_country_combo.get_active_text() or "",
            "autoconnect_city": self.autoconnect_city_combo.get_active_text() or "",
        }
```

**Step 2: Wire up save_config in main.py**

In `src/main.py`, after creating settings_pane (around line 330), add:

```python
        # Set up config save callback
        self.settings_pane.set_save_config_callback(self.save_config)
```

**Step 3: Update save_config in main.py to include auto-connect**

Find the `save_config()` method in main.py, then add this before the final write:

```python
        # Save auto-connect settings
        autoconnect_config = self.settings_pane.get_autoconnect_config()
        self.config.update(autoconnect_config)
```

**Step 4: Verify syntax**

Run: `python3 -m py_compile src/main.py src/settings_pane.py && echo "✓ Syntax valid"`

Expected: ✓ Syntax valid

---

## Task 5: Populate Countries on Startup

**Files:**
- Modify: `src/settings_pane.py` (add initialization method)
- Modify: `src/main.py` (call initialization)

**Step 1: Add populate_countries method to SettingsPane**

Add this to SettingsPane class:

```python
    def populate_autoconnect_countries(self, countries):
        """Populate country dropdown."""
        self.autoconnect_country_combo.remove_all()
        self.autoconnect_country_combo.append("", "Select Country")
        for country in countries:
            self.autoconnect_country_combo.append(country, country)
```

**Step 2: Load countries in background on startup**

In `src/main.py`, in the `on_activate()` or `build_window()` method, add after creating panes:

```python
        # Load auto-connect countries in background
        def load_countries():
            countries = self.nord.get_countries()
            GLib.idle_add(self.settings_pane.populate_autoconnect_countries, countries)

        import threading
        thread = threading.Thread(target=load_countries, daemon=True)
        thread.start()
```

**Step 3: Verify syntax**

Run: `python3 -m py_compile src/main.py src/settings_pane.py && echo "✓ Syntax valid"`

Expected: ✓ Syntax valid

---

## Task 6: Test Auto-Connect Functionality

**Files:**
- Test: `/tmp/test_autoconnect.py`

**Step 1: Create test script**

```python
#!/usr/bin/env python3
"""Test auto-connect functionality."""

import sys
sys.path.insert(0, '/home/wolf/Projects/NordGUI/src')

from settings_pane import SettingsPane
from nord_manager import NordManager

def test_autoconnect_ui():
    """Verify auto-connect UI components exist."""

    nord = NordManager()
    pane = SettingsPane(nord)

    # Check components exist
    assert hasattr(pane, 'autoconnect_switch'), "Missing autoconnect_switch"
    assert hasattr(pane, 'autoconnect_country_combo'), "Missing autoconnect_country_combo"
    assert hasattr(pane, 'autoconnect_city_combo'), "Missing autoconnect_city_combo"

    print("✓ Auto-connect UI components exist")

    # Test toggle
    pane.autoconnect_switch.set_active(True)
    assert pane.autoconnect_switch.get_active() == True
    print("✓ Auto-connect toggle works")

    # Test get config
    config = pane.get_autoconnect_config()
    assert "autoconnect_enabled" in config
    assert "autoconnect_country" in config
    assert "autoconnect_city" in config
    print("✓ get_autoconnect_config works")

    print("\n✓ All auto-connect tests passed!")

if __name__ == "__main__":
    test_autoconnect_ui()
```

**Step 2: Run test**

Run: `python3 /tmp/test_autoconnect.py 2>&1`

Expected: ✓ All auto-connect tests passed!

---

## Task 7: Build and Verify

**Files:**
- Build: `build.sh`

**Step 1: Build the package**

Run: `bash build.sh 2>&1 | tail -15`

Expected: Build complete, nordgui_1.0.0_all.deb created

**Step 2: Install and test**

Run: `sudo dpkg -i nordgui_1.0.0_all.deb && nordgui`

**Manual Testing:**
1. Open Settings tab
2. Find Auto-Connect toggle (should be OFF by default)
3. Toggle ON → Country and City dropdowns should become enabled
4. Select a country → City dropdown should populate
5. Select a city
6. Close and reopen app → Settings should be restored
7. Toggle OFF → Dropdowns should become disabled

**Expected Result:**
- Auto-Connect toggle visible in Settings tab
- Dropdowns inline on same line as toggle
- Dropdowns disabled when toggle is OFF
- Dropdowns enabled when toggle is ON
- Country selection populates city list
- Settings persist across app restart

---

## Success Criteria

✓ Auto-Connect toggle appears in Settings tab
✓ Country and city dropdowns appear inline
✓ Dropdowns disabled when toggle is OFF
✓ Dropdowns enabled when toggle is ON
✓ Selecting country populates city dropdown
✓ Settings persist to config.json
✓ Settings restore on app startup
✓ NordVPN CLI commands sent on toggle change
✓ No syntax errors
✓ App builds without errors
