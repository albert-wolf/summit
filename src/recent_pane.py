import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from summit_manager import SummitManager
from datetime import datetime


class RecentPane(Gtk.Box):
    """Sidebar showing recent connection history with click-to-connect"""

    def __init__(self, manager: SummitManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_size_request(250, -1)

        self.manager = manager
        self.connection_history = []
        self.last_server = None  # Track last connected server to detect changes
        self.app_ref = None
        self.current_connection = None

        # Favorites section
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

        # Recent connections title
        title = Gtk.Label(label="Recent Connections")
        title.add_css_class("heading")
        title.set_margin_top(12)
        self.append(title)

        # Recent connections list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self.history_listbox = Gtk.ListBox()
        self.history_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.history_listbox.connect("row-activated", self.on_connection_clicked)
        scrolled.set_child(self.history_listbox)
        self.append(scrolled)

        # Initialize with empty state
        self.refresh_favorites_display()
        self.refresh_history_display()

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

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.set_margin_top(8)
            vbox.set_margin_bottom(8)
            vbox.set_margin_start(8)
            vbox.set_margin_end(8)

            country = fav.get("country", "Unknown")
            city = fav.get("city", "Unknown")
            display_text = f"{city} - {country}"

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

            label = Gtk.Label(label=display_text)
            label.set_wrap(True)
            label.set_xalign(0)
            label.set_hexpand(True)

            # Highlight if current connection (compare by city and country underscore format)
            current_city = self.current_connection.get("city", "") if self.current_connection else ""
            current_country = self.current_connection.get("country", "") if self.current_connection else ""
            if country == current_country and city == current_city:
                label.set_markup(f"<b>{display_text}</b>")

            remove_btn = Gtk.Button(label="×")
            remove_btn.set_size_request(30, -1)
            remove_btn.connect("clicked", lambda btn: self.on_remove_favorite(fav))

            hbox.append(label)
            hbox.append(remove_btn)
            vbox.append(hbox)
            row.set_child(vbox)
            row.favorite_data = fav
            self.favorites_listbox.append(row)

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
            success, message = self.manager.connect(country, city)
            if success:
                self.manager.clear_cache()
            GLib.idle_add(self.on_connect_done, success, row, message)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def apply_status(self, status):
        """Apply pre-fetched status to UI (called from polling thread via idle_add)."""
        if not status:
            self.current_connection = None
            return

        state = status.get("Status", "Disconnected").lower()

        # Only track when fully connected (not just connecting)
        if state == "connected":
            server = status.get("Server", "Unknown")
            city = status.get("City", "Unknown")
            country = status.get("Country", "Unknown")

            # Track current connection for highlighting (use underscore format for matching)
            self.current_connection = {
                "country": country.replace(" ", "_"),
                "city": city.replace(" ", "_")
            }

            # Only add to history if this is a NEW connection (different server than last)
            if server != self.last_server:
                display_text = f"{city} - {server}"
                # CLI connect needs underscore format (e.g. United_States, Saint_Louis)
                connect_country = country.replace(" ", "_")
                connect_city = city.replace(" ", "_")
                self.add_history_entry(display_text, connect_country, connect_city, server)
                self.last_server = server
        else:
            # Disconnected or transitioning - clear last server so next connection gets added
            self.current_connection = None
            self.last_server = None

        # Refresh highlights
        self.refresh_favorites_display()
        self.refresh_history_display()
        return False

    def update_status(self):
        """Update status display from summit_manager (synchronous version for manual updates)."""
        status = self.manager.get_status()
        self.apply_status(status)

    def add_history_entry(self, display_text, country, city, server):
        """Add an entry to connection history."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Add to history
        entry = {
            'text': display_text,
            'country': country,
            'city': city,
            'server': server,
            'time': timestamp
        }
        self.connection_history.insert(0, entry)

        # Keep only last 10 entries
        if len(self.connection_history) > 10:
            self.connection_history = self.connection_history[:10]

        # Update listbox
        self.refresh_history_display()

    def refresh_history_display(self):
        """Refresh the history listbox display."""
        self.history_listbox.remove_all()

        if not self.connection_history:
            empty_row = Gtk.ListBoxRow()
            empty_label = Gtk.Label(label="No recent connections", xalign=0)
            empty_label.add_css_class("dim-label")
            empty_row.set_child(empty_label)
            self.history_listbox.append(empty_row)
            return

        for i, entry in enumerate(self.connection_history):
            row = Gtk.ListBoxRow()
            row.set_activatable(True)
            row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row_box.set_margin_top(8)
            row_box.set_margin_bottom(8)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)

            time_label = Gtk.Label(label=entry['time'])
            time_label.add_css_class("dim-label")
            time_label.set_xalign(0)
            row_box.append(time_label)

            text_label = Gtk.Label(label=entry['text'])
            text_label.set_wrap(True)
            text_label.set_wrap_mode(1)  # Gtk.WrapMode.WORD
            text_label.set_xalign(0)

            # Highlight if current connection
            if self.current_connection and entry['country'] == self.current_connection['country'] and entry['city'] == self.current_connection['city']:
                text_label.set_markup(f"<b>{entry['text']}</b>")
            elif i == 0:
                # Latest connection - highlight it (if not currently connected)
                text_label.set_markup(f"<b>{entry['text']}</b>")
            else:
                # Previous connections - dimmed
                text_label.add_css_class("dim-label")

            row_box.append(text_label)
            row.set_child(row_box)
            self.history_listbox.append(row)
            # Store the entry data on the row for retrieval when clicked
            row.entry_data = entry

    def on_connection_clicked(self, listbox, row):
        """Handle clicking a recent connection - connect to it."""
        if not hasattr(row, 'entry_data'):
            return

        entry = row.entry_data
        country = entry.get('country', '')
        city = entry.get('city', '')

        if not country:
            return  # Can't connect without country

        # Make row insensitive during connection attempt
        row.set_sensitive(False)

        def worker():
            # Connect to the saved country and city
            success, message = self.manager.connect(country, city)
            # Clear cache so next status update gets fresh data
            if success:
                self.manager.clear_cache()
            GLib.idle_add(self.on_connect_done, success, row, message)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_connect_done(self, success, row, message):
        """Handle connection completion."""
        row.set_sensitive(True)
        if not success and self.app_ref:
            self.app_ref.show_toast(f"Failed to connect: {message}", is_error=True)
        # Connection status will update via the polling loop
        return False
