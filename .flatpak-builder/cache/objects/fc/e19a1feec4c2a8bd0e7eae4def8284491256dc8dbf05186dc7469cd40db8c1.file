import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from summit_manager import SummitManager


@Gtk.Template(resource_path="/io/github/summit/ui/status_pane.ui")
class StatusPane(Gtk.Box):
    """Tab 1: VPN Status and Connection Controls"""

    __gtype_name__ = "StatusPane"

    status_dot = Gtk.Template.Child()
    status_spinner = Gtk.Template.Child()
    status_label = Gtk.Template.Child()

    server_value = Gtk.Template.Child()
    ip_value = Gtk.Template.Child()
    country_value = Gtk.Template.Child()
    city_value = Gtk.Template.Child()
    technology_value = Gtk.Template.Child()
    protocol_value = Gtk.Template.Child()
    transfer_value = Gtk.Template.Child()
    uptime_value = Gtk.Template.Child()

    connect_btn = Gtk.Template.Child()
    disconnect_btn = Gtk.Template.Child()
    reconnect_btn = Gtk.Template.Child()

    def __init__(self, manager: SummitManager, on_status_change=None, on_connect_click=None):
        super().__init__()
        self.init_template()

        self.manager = manager
        self.on_status_change = on_status_change
        self.on_connect_click = on_connect_click
        self.current_status = None
        self.app_ref = None
        self.is_connecting = False

        self.status_fields = {
            "Server": self.server_value,
            "IP": self.ip_value,
            "Country": self.country_value,
            "City": self.city_value,
            "Technology": self.technology_value,
            "Protocol": self.protocol_value,
            "Transfer": self.transfer_value,
            "Uptime": self.uptime_value,
        }

        # Connect signals
        self.connect_btn.connect("clicked", self.on_connect_clicked)
        self.disconnect_btn.connect("clicked", self.on_disconnect_clicked)
        self.reconnect_btn.connect("clicked", self.on_reconnect_clicked)

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
