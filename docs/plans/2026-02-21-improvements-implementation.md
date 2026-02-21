# UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 7 UX improvements: toast notifications, search filter, favorites, settings organization, error messages, connection spinner, and current connection highlight.

**Architecture:** Toast system is foundational (wraps main content overlay). Search and Settings are isolated UI changes. Favorites extends config storage and sidebar. Error messages and spinner leverage existing status polling and connection handlers.

**Tech Stack:** GTK4, Python threading, GLib signals

---

## Phase 1: Foundation — Toast Notification System

### Task 1: Create ToastOverlay widget

**Files:**
- Create: `src/toast.py`

**Code:**

```python
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

class ToastOverlay(Gtk.Overlay):
    """Toast notification overlay for success/error messages."""

    def __init__(self):
        super().__init__()
        self.toast_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_box.set_halign(Gtk.Align.CENTER)
        self.toast_box.set_valign(Gtk.Align.END)
        self.toast_box.set_margin_bottom(24)
        self.toast_box.set_margin_start(12)
        self.toast_box.set_margin_end(12)
        self.add_overlay(self.toast_box)

        self.active_toast = None
        self.toast_timeout = None

    def show_toast(self, message: str, is_error: bool = False, duration: int = None):
        """Show a toast notification.

        Args:
            message: Text to display
            is_error: If True, show red styling; if False, show green
            duration: Auto-dismiss after N ms (default 3000 for success, 5000 for error)
        """
        # Remove existing toast if any
        if self.active_toast:
            self.toast_box.remove(self.active_toast)
            if self.toast_timeout:
                GLib.source_remove(self.toast_timeout)

        # Create new toast
        toast = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toast.add_css_class("pane-box")
        toast.set_margin_top(12)
        toast.set_margin_bottom(12)
        toast.set_margin_start(16)
        toast.set_margin_end(16)

        label = Gtk.Label(label=message)
        label.set_wrap(True)
        label.set_max_width_chars(50)
        if is_error:
            label.add_css_class("error-text")
        toast.append(label)

        self.toast_box.append(toast)
        self.active_toast = toast

        # Auto-dismiss
        duration = duration or (5000 if is_error else 3000)
        self.toast_timeout = GLib.timeout_add(duration, self.dismiss_toast)

    def dismiss_toast(self):
        """Remove current toast."""
        if self.active_toast:
            self.toast_box.remove(self.active_toast)
            self.active_toast = None
        self.toast_timeout = None
        return False
```

**Step 1: Review the code**
- Toast appears centered bottom with margins
- Auto-dismisses (error 5s, success 3s)
- Removes old toast before showing new one
- Uses CSS classes for styling

**Step 2: Create style rules in style.css**

Add to `/home/wolf/Projects/Summit/style.css`:

```css
.error-text {
    color: #ff4444;
    font-weight: bold;
}
```

**Step 3: Integrate into main.py**

Modify `/home/wolf/Projects/Summit/src/main.py`:

Find: `from recent_pane import RecentPane` (line 30)
Add after: `from toast import ToastOverlay`

Find: `def build_window(self):` (line 295)
After building the header bar, change main_box setup:

```python
# Main box with toast overlay
toast_overlay = ToastOverlay()
self.toast_overlay = toast_overlay

# ... build content_paned as before ...

toast_overlay.set_child(main_box)
self.window.set_child(toast_overlay)
```

Also add method to SummitApp class:

```python
def show_toast(self, message: str, is_error: bool = False):
    """Show a toast notification from any pane."""
    if hasattr(self, 'toast_overlay'):
        self.toast_overlay.show_toast(message, is_error)
```

**Step 4: Manual test**
- Launch app with `python3 src/main.py`
- Verify layout looks normal
- No errors in console

**Step 5: Commit**

```bash
git add src/toast.py src/main.py style.css
git commit -m "feat: add toast notification system

- Create ToastOverlay widget for centered bottom notifications
- Auto-dismiss: 3s for success, 5s for errors
- Add show_toast() method to SummitApp for use by all panes"
```

---

## Phase 2: Search & Settings

### Task 2: Add search filter to Servers tab

**Files:**
- Modify: `src/servers_pane.py`

**Changes:**

At top of `__init__`, after margin setup:

```python
# Search bar
search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
search_box.set_margin_bottom(8)

search_label = Gtk.Label(label="Search:")
search_label.set_size_request(60, -1)
search_box.append(search_label)

self.search_entry = Gtk.SearchEntry()
self.search_entry.set_placeholder_text("Filter countries & cities...")
self.search_entry.set_hexpand(True)
self.search_entry.connect("search-changed", self.on_search_changed)
search_box.append(self.search_entry)

self.append(search_box)
```

Add instance variables after `__init__` setup:

```python
self.search_text = ""
self.all_countries = []  # Cache unfiltered list
self.all_cities = []     # Cache unfiltered list
```

Add filter methods before `on_country_selected`:

```python
def on_search_changed(self, search_entry):
    """Filter countries and cities by search text."""
    self.search_text = search_entry.get_text().lower()
    self.refresh_countries_display()
    self.refresh_cities_display()

def refresh_countries_display(self):
    """Refresh country list based on search."""
    self.countries_listbox.remove_all()
    for country in self.all_countries:
        if self.search_text in country.lower():
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=country, xalign=0))
            self.countries_listbox.append(row)

def refresh_cities_display(self):
    """Refresh city list based on search."""
    if not self.selected_country:
        return
    self.cities_listbox.remove_all()
    for city in self.all_cities:
        if self.search_text in city.lower():
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=city, xalign=0))
            self.cities_listbox.append(row)
```

Update `populate_countries` to cache:

Find: `for country in countries:`
Change to:

```python
self.all_countries = countries
for country in countries:
    if self.search_text in country.lower():
        # ... add row ...
```

Update `populate_cities` to cache:

Find: `for city in cities:`
Change to:

```python
self.all_cities = cities
for city in cities:
    if self.search_text in city.lower():
        # ... add row ...
```

**Step 1: Review the changes**
- Search entry at top of pane
- Two cache lists: all_countries, all_cities
- Refresh methods filter by search_text
- populate_* methods cache full lists

**Step 2: Manual test**
- Go to Servers tab
- Type in search box
- Verify countries and cities filter by substring
- Clear search, verify all items return

**Step 3: Commit**

```bash
git add src/servers_pane.py
git commit -m "feat: add search filter to Servers tab

- Search entry at top filters both countries and cities
- Real-time substring matching (case-insensitive)
- Clears when search is empty"
```

---

### Task 3: Organize Settings tab with section headers

**Files:**
- Modify: `src/settings_pane.py`

**Changes:**

Find the settings loop in `__init__` around line 100 (where toggles are created).

Replace the entire toggle creation section with grouped version:

```python
# Define settings groups
settings_groups = {
    "Connection": [
        ("Kill Switch", "killswitch"),
        ("Firewall", "firewall"),
        ("Auto-connect", "autoconnect"),
    ],
    "Privacy": [
        ("Obfuscate", "obfuscate"),
        ("IPv6 Leak Protection", "ipv6"),
    ],
    "Features": [
        ("Notify", "notify"),
        ("Tray", "tray"),
    ],
    "Advanced": [],
}

# Create grouped settings UI
for group_name, settings in settings_groups.items():
    # Group header
    header = Gtk.Label(label=group_name)
    header.add_css_class("heading")
    header.set_xalign(0)
    header.set_margin_top(12)
    header.set_margin_bottom(8)
    settings_box.append(header)

    # Settings in group
    for display_name, cli_name in settings:
        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect("notify::active", lambda s, p, name=cli_name: self.on_setting_toggled(s, name))

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_start(12)
        row.set_margin_bottom(4)

        label = Gtk.Label(label=display_name)
        label.set_hexpand(True)
        label.set_xalign(0)
        row.append(label)
        row.append(switch)
        settings_box.append(row)

        self.settings_switches[cli_name] = switch
```

Update `on_setting_toggled` to work with the new structure (no changes needed if already parameterized).

**Step 1: Review the changes**
- Settings organized into 4 groups with headers
- Same toggle functionality, just reorganized
- CLI names still map correctly

**Step 2: Manual test**
- Go to Settings tab
- Verify sections appear with headers: Connection, Privacy, Features, Advanced
- Verify toggles still work

**Step 3: Commit**

```bash
git add src/settings_pane.py
git commit -m "feat: organize Settings tab into groups

- Group toggles: Connection, Privacy, Features, Advanced
- Add section headers for clarity
- Maintain all existing toggle functionality"
```

---

## Phase 3: Favorites System

### Task 4: Add favorites to config and model

**Files:**
- Modify: `src/main.py`

**Changes:**

Find default config in `load_config()`:

```python
default_config = {
    "window_width": 900,
    "window_height": 650,
    "active_tab": 0,
    "autoconnect_enabled": False,
    "autoconnect_country": "",
    "autoconnect_city": "",
    "favorites": [],  # Add this line
}
```

**Step 1: Manual test**
- Launch app
- Check ~/.config/summit/config.json has "favorites": []

**Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add favorites list to config model"
```

---

### Task 5: Add star button to Servers tab

**Files:**
- Modify: `src/servers_pane.py`

**Changes:**

In `__init__`, after cities_label, add:

```python
# Favorite button row
fav_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
fav_button_box.set_margin_bottom(8)

self.favorite_button = Gtk.Button(label="★ Add to Favorites")
self.favorite_button.set_sensitive(False)
self.favorite_button.connect("clicked", self.on_add_favorite_clicked)
fav_button_box.append(self.favorite_button)

cities_box.append(fav_button_box)
```

Add instance variable:

```python
self.app_ref = None  # Will be set by main.py to access app.show_toast()
```

Add methods before `on_country_selected`:

```python
def set_app_ref(self, app):
    """Set reference to app for showing toasts."""
    self.app_ref = app

def on_add_favorite_clicked(self, button):
    """Add current country/city selection to favorites."""
    if not self.selected_country or not self.selected_city:
        if self.app_ref:
            self.app_ref.show_toast("Please select both country and city", is_error=True)
        return

    # Check if already favorite
    favorites = self.app_ref.config.get("favorites", [])
    new_fav = {"country": self.selected_country, "city": self.selected_city}

    if new_fav in favorites:
        if self.app_ref:
            self.app_ref.show_toast("Already in favorites", is_error=True)
        return

    # Add to config
    favorites.append(new_fav)
    self.app_ref.config["favorites"] = favorites
    self.app_ref.save_config()

    if self.app_ref:
        self.app_ref.show_toast(f"Added to favorites: {self.selected_city}")

    # Notify sidebar to refresh
    if hasattr(self.app_ref, 'recent_pane'):
        self.app_ref.recent_pane.refresh_favorites_display()

def on_city_selected(self, listbox, row):
    """Override existing to enable favorite button."""
    # ... existing code ...
    self.favorite_button.set_sensitive(True)  # Add this
```

In `main.py`, after creating servers_pane, add:

```python
self.servers_pane.set_app_ref(self)
```

**Step 1: Manual test**
- Go to Servers tab
- Select country and city
- Click "★ Add to Favorites" button
- Should show toast "Added to favorites: City"
- Verify in config.json favorites list grows

**Step 2: Commit**

```bash
git add src/servers_pane.py src/main.py
git commit -m "feat: add favorite button to Servers tab

- Star button appears when country+city selected
- Adds to config favorites list
- Shows toast on success
- Prevents duplicates"
```

---

### Task 6: Create Favorites section in sidebar

**Files:**
- Modify: `src/recent_pane.py`

**Changes:**

In `__init__`, after creating history_listbox, add before `refresh_history_display()`:

```python
# Favorites section (above recent connections)
favorites_label = Gtk.Label(label="Favorites")
favorites_label.add_css_class("heading")
favorites_label.set_margin_top(8)
self.append(favorites_label)

self.favorites_listbox = Gtk.ListBox()
self.favorites_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
self.favorites_listbox.connect("row-activated", self.on_favorite_clicked)

favorites_scrolled = Gtk.ScrolledWindow()
favorites_scrolled.set_vexpand(False)
favorites_scrolled.set_max_content_height(150)
favorites_scrolled.set_child(self.favorites_listbox)
self.append(favorites_scrolled)

# Label separator
sep_label = Gtk.Label(label="Recent Connections")
sep_label.add_css_class("heading")
sep_label.set_margin_top(12)
self.append(sep_label)
```

Add instance variables:

```python
self.app_ref = None
self.current_connection = None
```

Add methods before `update_status()`:

```python
def set_app_ref(self, app):
    """Set reference to app."""
    self.app_ref = app

def refresh_favorites_display(self):
    """Refresh favorites from config."""
    self.favorites_listbox.remove_all()

    if not self.app_ref:
        return

    favorites = self.app_ref.config.get("favorites", [])

    if not favorites:
        empty_row = Gtk.ListBoxRow()
        empty_label = Gtk.Label(label="No favorites", xalign=0)
        empty_label.add_css_class("dim-label")
        empty_row.set_child(empty_label)
        self.favorites_listbox.append(empty_row)
        return

    for fav in favorites:
        row = Gtk.ListBoxRow()
        row.set_activatable(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        country = fav.get("country", "Unknown")
        city = fav.get("city", "Unknown")
        display_text = f"{city} - {country}"

        label = Gtk.Label(label=display_text)
        label.set_wrap(True)
        label.set_xalign(0)

        # Highlight if current connection
        if self.current_connection == country and country != "Unknown":
            label.set_markup(f"<b>{display_text}</b>")

        box.append(label)
        row.set_child(box)
        row.favorite_data = fav
        self.favorites_listbox.append(row)

def on_favorite_clicked(self, listbox, row):
    """Handle clicking a favorite."""
    if not hasattr(row, 'favorite_data'):
        return

    fav = row.favorite_data
    country = fav.get('country', '')
    city = fav.get('city', '')

    if not country:
        return

    row.set_sensitive(False)

    def worker():
        success, message = self.nord.connect(country, city)
        if success:
            self.nord.clear_cache()
        GLib.idle_add(self.on_connect_done, success, row, message)

    import threading
    threading.Thread(target=worker, daemon=True).start()
```

Update `update_status()` to track current connection and highlight:

```python
def update_status(self):
    """Check if connection status changed and track current server."""
    status = self.nord.get_status()
    if not status:
        self.current_connection = None
        return

    state = status.get("Status", "Disconnected").lower()

    # Track current connection for highlighting
    if state == "connected":
        self.current_connection = status.get("Country", "Unknown")
        server = status.get("Server", "Unknown")
        if server != self.last_server:
            city = status.get("City", "Unknown")
            country = status.get("Country", "Unknown")
            display_text = f"{city} - {server}"
            connect_country = country.replace(" ", "_")
            connect_city = city.replace(" ", "_")
            self.add_history_entry(display_text, connect_country, connect_city, server)
            self.last_server = server
    else:
        self.current_connection = None
        self.last_server = None

    # Refresh highlights
    self.refresh_favorites_display()
    self.refresh_history_display()
```

In `main.py`, after creating recent_pane, add:

```python
self.recent_pane.set_app_ref(self)
self.recent_pane.refresh_favorites_display()
```

Also update `load_initial_data()` to refresh favorites:

```python
def load_autoconnect_data():
    # ... existing code ...
    # After populating UI:
    self.recent_pane.refresh_favorites_display()
```

**Step 1: Manual test**
- Add a favorite from Servers tab
- Go to Status tab
- Verify "Favorites" section appears with the entry
- Click it, should connect
- Verify it highlights bold when connected
- Right-click or remove capability pending

**Step 2: Commit**

```bash
git add src/recent_pane.py src/main.py
git commit -m "feat: add Favorites section to sidebar

- Favorites section above Recent Connections
- Click to connect (same as recent)
- Current connected server highlights bold
- Empty state shows 'No favorites'"
```

---

### Task 7: Add remove-favorite functionality

**Files:**
- Modify: `src/recent_pane.py`

**Changes:**

Update `refresh_favorites_display()` to add remove button:

```python
# After label creation, before appending to box:
remove_btn = Gtk.Button(label="×")
remove_btn.set_size_request(30, -1)
remove_btn.connect("clicked", lambda btn: self.on_remove_favorite(fav))
label.set_hexpand(True)

row_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
row_hbox.set_margin_top(8)
row_hbox.set_margin_bottom(8)
row_hbox.set_margin_start(8)
row_hbox.set_margin_end(8)
row_hbox.append(label)
row_hbox.append(remove_btn)

box.append(row_hbox)
```

Add method:

```python
def on_remove_favorite(self, fav):
    """Remove favorite from config."""
    if not self.app_ref:
        return

    favorites = self.app_ref.config.get("favorites", [])
    if fav in favorites:
        favorites.remove(fav)
        self.app_ref.config["favorites"] = favorites
        self.app_ref.save_config()
        self.refresh_favorites_display()
        self.app_ref.show_toast("Removed from favorites")
```

**Step 1: Manual test**
- Add a favorite
- See "×" button appear
- Click it
- Favorite disappears, toast shows

**Step 2: Commit**

```bash
git add src/recent_pane.py
git commit -m "feat: add remove button to favorites

- × button removes favorite from config
- Shows toast on removal"
```

---

## Phase 4: Error Handling & Visual Feedback

### Task 8: Add error messages to connection handlers

**Files:**
- Modify: `src/status_pane.py`, `src/recent_pane.py`

**Changes - status_pane.py:**

Update `on_connect_clicked` to show error:

```python
def on_connect_clicked(self, button):
    """Connect button clicked - switch to servers tab and trigger connect."""
    # Switch to servers tab
    if self.on_connect_click:
        self.on_connect_click()
```

Actually, the Connect button just switches tabs. But we should update reconnect:

Find `on_reconnect_clicked`:

```python
def on_reconnect_clicked(self, button):
    """Reconnect to VPN."""
    button.set_sensitive(False)
    button.set_label("Reconnecting...")

    def worker():
        success, message = self.nord.reconnect()
        GLib.idle_add(self.on_reconnect_done, success, message, button)

    import threading
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

def on_reconnect_done(self, success, message, button):
    """Handle reconnect completion."""
    button.set_sensitive(True)
    button.set_label("Reconnect")
    if not success and hasattr(self, 'app_ref'):
        self.app_ref.show_toast(f"Failed to reconnect: {message}", is_error=True)
    self.update_status()
    return False
```

Add instance var and method to StatusPane `__init__`:

```python
self.app_ref = None

def set_app_ref(self, app):
    """Set reference to app for toasts."""
    self.app_ref = app
```

In `main.py`, after creating status_pane:

```python
self.status_pane.set_app_ref(self)
```

**Changes - recent_pane.py:**

Update `on_connect_done` to show errors:

```python
def on_connect_done(self, success, row, message):
    """Handle connection completion."""
    row.set_sensitive(True)
    if not success and self.app_ref:
        self.app_ref.show_toast(f"Failed to connect: {message}", is_error=True)
    return False
```

Update `on_disconnect_done` in status_pane similarly:

```python
def on_disconnect_done(self, success, message, button):
    """Handle disconnect completion."""
    button.set_sensitive(True)
    button.set_label("Disconnect")
    if not success and hasattr(self, 'app_ref'):
        self.app_ref.show_toast(f"Failed to disconnect: {message}", is_error=True)
    self.update_status()
    return False
```

**Step 1: Manual test**
- Try to connect to a non-existent server
- Error toast should appear with message
- Disconnect and try invalid operation
- Error should show

**Step 2: Commit**

```bash
git add src/status_pane.py src/recent_pane.py src/main.py
git commit -m "feat: show error messages in toasts

- Connection failures show actual error message
- Disconnect failures show error
- Reconnect failures show error
- Messages captured from CLI output"
```

---

### Task 9: Add connection spinner to Status pane

**Files:**
- Modify: `src/status_pane.py`

**Changes:**

In `__init__`, find status_box (where status_dot is):

Replace:
```python
status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
self.status_dot = Gtk.Label(label="●")
```

With:
```python
status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

# Status indicator with optional spinner
self.status_indicator_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
self.status_dot = Gtk.Label(label="●")
self.status_dot.add_css_class("heading")
self.status_dot.set_size_request(24, 24)
self.status_indicator_box.append(self.status_dot)

self.status_spinner = Gtk.Spinner()
self.status_spinner.set_size_request(24, 24)
self.status_spinner.set_visible(False)
self.status_indicator_box.append(self.status_spinner)

status_box.append(self.status_indicator_box)
```

Add instance variable:

```python
self.is_connecting = False
```

Update `on_reconnect_clicked`:

```python
def on_reconnect_clicked(self, button):
    """Reconnect to VPN."""
    self.is_connecting = True
    self.status_spinner.set_visible(True)
    self.status_spinner.start()
    button.set_sensitive(False)
    button.set_label("Reconnecting...")

    def worker():
        success, message = self.nord.reconnect()
        GLib.idle_add(self.on_reconnect_done, success, message, button)

    import threading
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

def on_reconnect_done(self, success, message, button):
    """Handle reconnect completion."""
    self.is_connecting = False
    self.status_spinner.stop()
    self.status_spinner.set_visible(False)
    button.set_sensitive(True)
    button.set_label("Reconnect")
    if not success and hasattr(self, 'app_ref'):
        self.app_ref.show_toast(f"Failed to reconnect: {message}", is_error=True)
    self.update_status()
    return False
```

**Step 1: Manual test**
- Click Reconnect
- Spinner should appear next to status dot
- Spin while connecting
- Stop when done

**Step 2: Commit**

```bash
git add src/status_pane.py
git commit -m "feat: add spinner to status indicator while connecting

- Spinner appears next to status dot during reconnect
- Auto-hides when connection succeeds or fails"
```

---

### Task 10: Add spinner to favorite/recent connection rows

**Files:**
- Modify: `src/recent_pane.py`

**Changes:**

Update row creation in `refresh_favorites_display()` and `refresh_history_display()`:

In `refresh_favorites_display()`, change row creation:

```python
row = Gtk.ListBoxRow()
row.set_activatable(True)

row_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
box.set_margin_top(8)
box.set_margin_bottom(8)
box.set_margin_start(8)
box.set_margin_end(8)
box.set_hexpand(True)

# ... label creation ...

box.append(label)

spinner = Gtk.Spinner()
spinner.set_visible(False)
spinner.set_size_request(20, 20)
spinner.set_valign(Gtk.Align.CENTER)

row_container.append(box)
row_container.append(spinner)
row.set_child(row_container)
row.favorite_data = fav
row.spinner = spinner  # Store reference
self.favorites_listbox.append(row)
```

Do the same for history rows in `refresh_history_display()`.

Update `on_favorite_clicked`:

```python
def on_favorite_clicked(self, listbox, row):
    """Handle clicking a favorite."""
    if not hasattr(row, 'favorite_data'):
        return

    fav = row.favorite_data
    country = fav.get('country', '')
    city = fav.get('city', '')

    if not country:
        return

    row.set_sensitive(False)
    if hasattr(row, 'spinner'):
        row.spinner.set_visible(True)
        row.spinner.start()

    def worker():
        success, message = self.nord.connect(country, city)
        if success:
            self.nord.clear_cache()
        GLib.idle_add(self.on_connect_done, success, row, message)

    import threading
    threading.Thread(target=worker, daemon=True).start()
```

Update `on_connect_done`:

```python
def on_connect_done(self, success, row, message):
    """Handle connection completion."""
    if hasattr(row, 'spinner'):
        row.spinner.stop()
        row.spinner.set_visible(False)
    row.set_sensitive(True)
    if not success and self.app_ref:
        self.app_ref.show_toast(f"Failed to connect: {message}", is_error=True)
    return False
```

Do the same for `on_connection_clicked` and its done handler.

**Step 1: Manual test**
- Click a favorite/recent connection
- Spinner should appear and spin on the row
- Stop when connected
- Show error toast if failed

**Step 2: Commit**

```bash
git add src/recent_pane.py
git commit -m "feat: add spinner to favorite/recent connection rows

- Spinner shows while connecting
- Auto-hides when connection completes or fails
- Works for both favorites and recent connections"
```

---

## Final Steps

### Task 11: Rebuild .deb and commit

**Step 1: Rebuild**

```bash
./build.sh
```

Expected: `summit_1.0.0_all.deb` created successfully

**Step 2: Commit all changes**

```bash
git add build/
git commit -m "build: rebuild summit with all UX improvements"
```

**Step 3: Full manual test of all features**

Test checklist:
- [ ] Toast notifications appear and dismiss correctly
- [ ] Search filter works in Servers tab
- [ ] Settings organized into sections
- [ ] Can add favorite from Servers tab
- [ ] Favorite appears in sidebar
- [ ] Can remove favorite
- [ ] Can click favorite to connect
- [ ] Current connection highlights bold
- [ ] Connection shows spinner
- [ ] Errors show in toasts
- [ ] Config saves/loads favorites correctly

---

## Execution Plan

This plan has 11 tasks. Expected implementation time: 2-3 hours with testing and commits.

**Suggested approach:** Implement in order (foundational first), commit after each task. Toast system → Search/Settings → Favorites → Error handling → Spinners.

---
