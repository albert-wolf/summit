import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from summit_manager import SummitManager


class StatusPane(Gtk.Box):
    """Tab 1: VPN Status and Connection Controls"""

    def __init__(self, manager: SummitManager, on_status_change=None, on_connect_click=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.manager = manager
        self.on_status_change = on_status_change
        self.on_connect_click = on_connect_click
        self.current_status = None
        self.app_ref = None
        self.is_connecting = False

        # Status indicator with optional spinner
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

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

        self.status_label = Gtk.Label(label="Disconnected")
        self.status_label.add_css_class("heading")
        status_box.append(self.status_label)
        self.append(status_box)

        # Status grid with border
        grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        grid_box.add_css_class("pane-box")
        grid_box.set_margin_top(8)
        grid_box.set_margin_bottom(8)
        grid_box.set_margin_start(8)
        grid_box.set_margin_end(8)

        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(8)
        self.grid.set_column_spacing(12)
        self.grid.set_margin_top(4)
        self.grid.set_margin_bottom(4)
        self.grid.set_margin_start(4)
        self.grid.set_margin_end(4)

        self.status_fields = {}
        fields = ["Server", "IP", "Country", "City", "Technology", "Protocol", "Transfer", "Uptime"]
        for i, field in enumerate(fields):
            label = Gtk.Label(label=f"{field}:")
            label.set_xalign(1)  # Right align
            self.grid.attach(label, 0, i, 1, 1)

            value = Gtk.Label(label="—")
            value.set_xalign(0)  # Left align
            self.grid.attach(value, 1, i, 1, 1)
            self.status_fields[field] = value

        grid_box.append(self.grid)
        self.append(grid_box)

        # Button row
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_margin_top(12)

        self.connect_btn = Gtk.Button(label="Connect")
        self.connect_btn.connect("clicked", self.on_connect_clicked)
        button_box.append(self.connect_btn)

        self.disconnect_btn = Gtk.Button(label="Disconnect")
        self.disconnect_btn.connect("clicked", self.on_disconnect_clicked)
        button_box.append(self.disconnect_btn)

        self.reconnect_btn = Gtk.Button(label="Reconnect")
        self.reconnect_btn.connect("clicked", self.on_reconnect_clicked)
        button_box.append(self.reconnect_btn)

        self.append(button_box)

    def apply_status(self, status):
        """Apply pre-fetched status to UI (called from polling thread via idle_add)."""
        if not status:
            self.status_label.set_label("Disconnected")
            self.status_dot.set_label("●")
            self.status_dot.set_markup('<span foreground="#ff4444">●</span>')
            return

        # Update status indicator
        state = status.get("Status", "Disconnected").lower()
        if state == "connected":
            self.status_dot.set_markup('<span foreground="#44ff44">●</span>')
            self.status_label.set_label("Connected")
        elif state == "connecting":
            self.status_dot.set_markup('<span foreground="#ffff44">●</span>')
            self.status_label.set_label("Connecting...")
        else:
            self.status_dot.set_markup('<span foreground="#ff4444">●</span>')
            self.status_label.set_label("Disconnected")

        # Update fields
        field_mapping = {
            "Server": "Server",
            "IP": "IP",
            "Country": "Country",
            "City": "City",
            "Technology": "Current technology",
            "Protocol": "Current protocol",
            "Transfer": "Transfer",
            "Uptime": "Uptime",
        }

        for display_name, status_key in field_mapping.items():
            value = status.get(status_key, "—")
            if self.status_fields.get(display_name):
                self.status_fields[display_name].set_label(value)

        self.current_status = status
        if self.on_status_change:
            self.on_status_change(status)
        return False

    def update_status(self):
        """Update status display from summit_manager (synchronous version for manual updates)."""
        status = self.manager.get_status()
        self.apply_status(status)

    def on_connect_clicked(self, button):
        """Connect button clicked - switch to servers tab."""
        if self.on_connect_click:
            self.on_connect_click()

    def set_app_ref(self, app):
        """Set reference to app for showing toasts."""
        self.app_ref = app

    def on_disconnect_clicked(self, button):
        """Disconnect from VPN."""
        button.set_sensitive(False)
        button.set_label("Disconnecting...")

        def worker():
            success, message = self.manager.disconnect()
            GLib.idle_add(self.on_disconnect_done, success, message, button)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_disconnect_done(self, success, message, button):
        """Handle disconnect completion."""
        button.set_sensitive(True)
        button.set_label("Disconnect")
        if not success and self.app_ref:
            self.app_ref.show_toast(f"Failed to disconnect: {message}", is_error=True)
        self.update_status()
        return False

    def on_reconnect_clicked(self, button):
        """Reconnect to last server."""
        self.is_connecting = True
        self.status_spinner.set_visible(True)
        self.status_spinner.start()
        button.set_sensitive(False)
        button.set_label("Reconnecting...")

        def worker():
            success, message = self.manager.reconnect()
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
        if not success and self.app_ref:
            self.app_ref.show_toast(f"Failed to reconnect: {message}", is_error=True)
        self.update_status()
        return False
