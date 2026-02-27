import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from summit_manager import SummitManager


class MeshnetPane(Gtk.Box):
    """Tab 5: Meshnet Management with 3-pane layout"""

    def __init__(self, manager: SummitManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.manager = manager
        self.meshnet_enabled = False
        self.initializing = True

        # Meshnet toggle row
        toggle_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toggle_row.set_hexpand(True)

        toggle_label = Gtk.Label(label="Meshnet", xalign=0)
        toggle_label.add_css_class("heading")
        toggle_label.set_hexpand(True)
        toggle_row.append(toggle_label)

        self.meshnet_switch = Gtk.Switch()
        self.meshnet_switch.set_valign(Gtk.Align.CENTER)
        self.meshnet_switch.connect("notify::active", self.on_meshnet_toggled)
        toggle_row.append(self.meshnet_switch)

        self.append(toggle_row)

        # Scrollable container for 3 panes
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        panes_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        panes_container.set_margin_top(12)

        # Pane 1: This Device (with info displayed directly, not in listbox)
        self.device_pane = self.create_pane("This Device")
        self.device_info_label = Gtk.Label(label="Local Device", xalign=0, wrap=True)
        self.device_info_label.set_wrap_mode(1)  # Word wrap
        self.device_pane.append(self.device_info_label)
        panes_container.append(self.device_pane)

        # Pane 2: Connected Devices
        self.connected_pane = self.create_pane("Connected Devices")
        self.connected_list = Gtk.ListBox()
        self.connected_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.connected_pane.append(self.connected_list)
        panes_container.append(self.connected_pane)

        # Pane 3: Disconnected Devices
        self.disconnected_pane = self.create_pane("Disconnected Devices")
        self.disconnected_list = Gtk.ListBox()
        self.disconnected_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.disconnected_pane.append(self.disconnected_list)
        panes_container.append(self.disconnected_pane)

        scrolled.set_child(panes_container)
        self.append(scrolled)

        # Load initial state asynchronously to avoid blocking main thread on startup
        self.load_meshnet_state_async()

    def create_pane(self, title: str) -> Gtk.Box:
        """Create a styled pane with title and border."""
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pane.set_margin_top(8)
        pane.set_margin_bottom(8)
        pane.set_margin_start(8)
        pane.set_margin_end(8)
        pane.add_css_class("pane-box")

        title_label = Gtk.Label(label=title)
        title_label.add_css_class("heading")
        pane.append(title_label)

        return pane

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
                GLib.idle_add(lambda: setattr(self, 'initializing', False))
            except Exception as e:
                print(f"[ERROR] Failed to load meshnet state: {e}")
                GLib.idle_add(lambda: setattr(self, 'initializing', False))

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

        # Show/hide panes based on meshnet state
        self.device_pane.set_visible(enabled)
        self.connected_pane.set_visible(enabled)
        self.disconnected_pane.set_visible(enabled)

        if enabled:
            self.populate_meshnet_data(peers)

    def populate_meshnet_data(self, peers):
        """Populate the 3 panes with device and peer data."""
        # Update This Device section
        device_info = self.manager.get_this_device_info()
        local_device_name = None

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

            device_text = device_info
            self.device_info_label.set_label(device_text)
        else:
            # Fallback if info not available
            self.device_info_label.set_label("Local Device")

        # Clear peer lists
        self.connected_list.remove_all()
        self.disconnected_list.remove_all()

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
                    self.connected_list.append(row)
                    connected_count += 1
                else:
                    self.disconnected_list.append(row)
                    disconnected_count += 1

        # Show empty states if no devices
        if connected_count == 0:
            connected_row = Gtk.ListBoxRow()
            empty_label = Gtk.Label(label="No connected devices", xalign=0)
            empty_label.add_css_class("dim-label")
            connected_row.set_child(empty_label)
            self.connected_list.append(connected_row)

        if disconnected_count == 0:
            disconnected_row = Gtk.ListBoxRow()
            empty_label = Gtk.Label(label="No disconnected devices", xalign=0)
            empty_label.add_css_class("dim-label")
            disconnected_row.set_child(empty_label)
            self.disconnected_list.append(disconnected_row)

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
            self.device_pane.set_visible(enabled)
            self.connected_pane.set_visible(enabled)
            self.disconnected_pane.set_visible(enabled)

            if enabled:
                self.load_meshnet_peers()
            else:
                self.device_list.remove_all()
                self.connected_list.remove_all()
                self.disconnected_list.remove_all()
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
