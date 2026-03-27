import gi
import logging

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from summit_manager import SummitManager

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/summit/ui/meshnet_pane.ui")
class MeshnetPane(Gtk.Box):
    """Tab 5: Meshnet Management with 3-pane layout"""

    __gtype_name__ = "MeshnetPane"

    meshnet_switch = Gtk.Template.Child()
    this_device_list = Gtk.Template.Child()
    connected_peers_list = Gtk.Template.Child()
    disconnected_peers_list = Gtk.Template.Child()

    def __init__(self, manager: SummitManager):
        super().__init__()
        self.init_template()

        self.manager = manager
        self.meshnet_enabled = False
        self.initializing = True

        # Load initial state asynchronously to avoid blocking main thread on startup
        self.load_meshnet_state_async()

    def load_meshnet_state(self):
        """Load meshnet state synchronously."""
        settings = self.manager.get_settings()
        meshnet_enabled = settings.get("Meshnet", "disabled").lower() == "enabled"

        if meshnet_enabled:
            enabled, peers = self.manager.get_meshnet_peers()
            self.apply_meshnet_state(enabled, peers)
        else:
            self.apply_meshnet_state(False, [])

        self.initializing = False

    def load_meshnet_state_async(self):
        """Load meshnet state in background thread to avoid blocking startup."""

        def worker():
            try:
                import time

                # Wait a bit to let UI settle after window appears
                time.sleep(0.3)

                settings = self.manager.get_settings()
                meshnet_enabled = settings.get("Meshnet", "disabled").lower() == "enabled"

                if meshnet_enabled:
                    enabled, peers = self.manager.get_meshnet_peers()
                else:
                    enabled, peers = False, []

                GLib.idle_add(self.apply_meshnet_state, enabled, peers)
                GLib.idle_add(lambda: setattr(self, "initializing", False))
            except Exception as e:
                logger.error(f"Failed to load meshnet state: {e}")
                GLib.idle_add(lambda: setattr(self, "initializing", False))

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def apply_meshnet_state(self, enabled, peers):
        """Apply meshnet state to UI."""
        self.meshnet_enabled = enabled

        # Set switch without triggering signal during initialization
        old_initializing = self.initializing
        self.initializing = True
        self.meshnet_switch.set_active(enabled)
        self.initializing = old_initializing

        # Show/hide peer lists based on meshnet state
        # In the new layout, we might want to keep the containers visible but empty,
        # or hide them. The original code hid the whole panes.
        # Since they are in a homogeneous box, hiding them might look weird or good.
        # For now, let's keep them visible but they will be populated if enabled.

        if enabled:
            self.populate_meshnet_data(peers)
        else:
            self.this_device_list.remove_all()
            self.connected_peers_list.remove_all()
            self.disconnected_peers_list.remove_all()

    def populate_meshnet_data(self, peers):
        """Populate the 3 panes with device and peer data."""
        # Update This Device section
        device_info = self.manager.get_this_device_info()
        local_device_name = None

        self.this_device_list.remove_all()

        if device_info:
            # Extract local device name from "Hostname: ..." line
            lines = device_info.split("\n")
            for line in lines:
                if line.lower().startswith("hostname:"):
                    # Extract hostname value
                    hostname = line.split(":", 1)[1].strip() if ":" in line else None
                    if hostname:
                        local_device_name = hostname
                    break

            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=device_info, xalign=0, wrap=True)
            label.set_wrap_mode(1)  # Word wrap
            label.set_margin_top(4)
            label.set_margin_bottom(4)
            label.set_margin_start(4)
            label.set_margin_end(4)
            row.set_child(label)
            self.this_device_list.append(row)
        else:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label="Local device info unavailable", xalign=0)
            label.add_css_class("dim-label")
            row.set_child(label)
            self.this_device_list.append(row)

        # Clear peer lists
        self.connected_peers_list.remove_all()
        self.disconnected_peers_list.remove_all()

        # Categorize peers as connected or disconnected
        connected_count = 0
        disconnected_count = 0

        if peers:
            for peer in peers:
                name = peer.get("name", "Unknown")

                # Skip the local device - don't show it in peer lists
                if local_device_name and name.lower() == local_device_name.lower():
                    continue

                status = peer.get("status", "disconnected").lower()

                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                row_box.set_margin_top(4)
                row_box.set_margin_bottom(4)
                row_box.set_margin_start(4)
                row_box.set_margin_end(4)

                peer_label = Gtk.Label(label=name, xalign=0)
                row_box.append(peer_label)

                if "ip" in peer:
                    ip_label = Gtk.Label(label=peer["ip"], xalign=0)
                    ip_label.add_css_class("dim-label")
                    row_box.append(ip_label)

                row.set_child(row_box)

                # Add to appropriate list based on status
                # Check for exactly "connected" or "online" (not "disconnected"!)
                is_connected = status == "connected" or status == "online"

                if is_connected:
                    self.connected_peers_list.append(row)
                    connected_count += 1
                else:
                    self.disconnected_peers_list.append(row)
                    disconnected_count += 1

        # Show empty states if no devices
        if connected_count == 0:
            connected_row = Gtk.ListBoxRow()
            empty_label = Gtk.Label(label="No connected devices", xalign=0)
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(4)
            empty_label.set_margin_bottom(4)
            empty_label.set_margin_start(4)
            empty_label.set_margin_end(4)
            connected_row.set_child(empty_label)
            self.connected_peers_list.append(connected_row)

        if disconnected_count == 0:
            disconnected_row = Gtk.ListBoxRow()
            empty_label = Gtk.Label(label="No disconnected devices", xalign=0)
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(4)
            empty_label.set_margin_bottom(4)
            empty_label.set_margin_start(4)
            empty_label.set_margin_end(4)
            disconnected_row.set_child(empty_label)
            self.disconnected_peers_list.append(disconnected_row)

    @Gtk.Template.Callback()
    def on_meshnet_toggled(self, switch, pspec):
        """Handle meshnet toggle."""
        if self.initializing:
            return

        enabled = switch.get_active()
        switch.set_sensitive(False)

        def worker():
            success, message = self.manager.set_meshnet(enabled)
            GLib.idle_add(self.on_meshnet_done, success, enabled, switch)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_meshnet_done(self, success, enabled, switch):
        """Handle meshnet toggle completion."""
        switch.set_sensitive(True)

        if success:
            self.meshnet_enabled = enabled
            # We don't hide panes anymore as they are part of the template's layout
            # but we could hide the whole horizontal box if needed.
            # For now, just populate or clear.

            if enabled:
                self.load_meshnet_peers()
            else:
                self.this_device_list.remove_all()
                self.connected_peers_list.remove_all()
                self.disconnected_peers_list.remove_all()
        else:
            # Revert switch on failure
            switch.set_active(not enabled)

        return False

    def load_meshnet_peers(self):
        """Load peers when meshnet is enabled."""

        def worker():
            enabled, peers = self.manager.get_meshnet_peers()
            GLib.idle_add(self.populate_meshnet_data, peers)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
