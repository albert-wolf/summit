import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from summit_manager import NordManager
from datetime import datetime


class RecentPane(Gtk.Box):
    """Sidebar showing recent connection history with click-to-connect"""

    def __init__(self, nord: NordManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_size_request(250, -1)

        self.nord = nord
        self.connection_history = []
        self.last_server = None  # Track last connected server to detect changes

        # Title
        title = Gtk.Label(label="Recent Connections")
        title.add_css_class("heading")
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
        self.refresh_history_display()

    def update_status(self):
        """Check if connection status changed. Only add to history on new connections."""
        status = self.nord.get_status()
        if not status:
            return

        state = status.get("Status", "Disconnected").lower()

        # Only track when connected
        if "connected" in state:
            server = status.get("Server", "Unknown")
            # Only add to history if this is a NEW connection (different server than last)
            if server != self.last_server:
                city = status.get("City", "Unknown")
                country = status.get("Country", "Unknown")
                display_text = f"{city} - {server}"
                self.add_history_entry(display_text, country, city, server)
                self.last_server = server
        else:
            # Disconnected - clear last server so next connection gets added
            self.last_server = None

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

            if i == 0:
                # Latest connection - highlight it
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
        country = entry['country']
        city = entry['city']

        # Make button insensitive during connection
        row.set_sensitive(False)

        def worker():
            # Connect to the saved country and city
            success, message = self.nord.connect(country, city)
            GLib.idle_add(self.on_connect_done, success, row)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_connect_done(self, success, row):
        """Handle connection completion."""
        row.set_sensitive(True)
        return False
