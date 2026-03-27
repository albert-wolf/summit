import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
import threading
from summit_manager import SummitManager


@Gtk.Template(resource_path="/io/github/summit/ui/settings_pane.ui")
class SettingsPane(Gtk.Box):
    """Tab 3: NordVPN Settings"""

    __gtype_name__ = "SettingsPane"

    killswitch_switch = Gtk.Template.Child()
    firewall_switch = Gtk.Template.Child()
    autoconnect_switch = Gtk.Template.Child()
    lan_discovery_switch = Gtk.Template.Child()
    virtual_location_switch = Gtk.Template.Child()
    threat_protection_lite_switch = Gtk.Template.Child()
    obfuscate_switch = Gtk.Template.Child()
    notify_switch = Gtk.Template.Child()
    meshnet_switch = Gtk.Template.Child()
    technology_dropdown = Gtk.Template.Child()
    protocol_dropdown = Gtk.Template.Child()

    def __init__(self, manager: SummitManager):
        super().__init__()
        self.init_template()

        self.manager = manager
        self.settings = {}

        # Mapping setting keys to widgets
        self.switch_map = {
            "Kill Switch": self.killswitch_switch,
            "Firewall": self.firewall_switch,
            "Auto-connect": self.autoconnect_switch,
            "LAN Discovery": self.lan_discovery_switch,
            "Virtual Location": self.virtual_location_switch,
            "Threat Protection Lite": self.threat_protection_lite_switch,
            "Obfuscate": self.obfuscate_switch,
            "Notify": self.notify_switch,
            "Meshnet": self.meshnet_switch,
        }

        # Store handler IDs for blocking
        self.handler_ids = {}

        # Connect switches
        for key, switch in self.switch_map.items():
            handler_id = switch.connect("notify::active", self.on_setting_toggled, key)
            self.handler_ids[key] = handler_id

        # Initialize technology dropdown
        self.technology_dropdown.append("NORDLYNX", "NordLynx")
        self.technology_dropdown.append("OPENVPN", "OpenVPN")
        self.tech_handler_id = self.technology_dropdown.connect(
            "changed", self.on_technology_changed
        )

        # Initialize protocol dropdown
        self.protocol_dropdown.append("UDP", "UDP")
        self.protocol_dropdown.append("TCP", "TCP")
        self.proto_handler_id = self.protocol_dropdown.connect("changed", self.on_protocol_changed)

        # Load settings
        self.load_settings()

    def load_settings(self, synchronous=False):
        """Load settings. If synchronous=True, load immediately; else load in background."""
        if synchronous:
            # Synchronous load - called before window shows
            settings = self.manager.get_settings()
            self.apply_settings_to_ui(settings)
        else:
            # Asynchronous load - for updates after window is shown
            def worker():
                settings = self.manager.get_settings()
                GLib.idle_add(self.apply_settings_to_ui, settings)

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()

    def apply_settings_to_ui(self, settings):
        """Update UI with loaded settings."""
        self.settings = settings

        # Update switches
        for key, switch in self.switch_map.items():
            handler_id = self.handler_ids.get(key)
            if handler_id:
                switch.handler_block(handler_id)
                value = settings.get(key, "disabled").lower()
                switch.set_active(value == "enabled")
                switch.handler_unblock(handler_id)

        # Update technology
        self.technology_dropdown.handler_block(self.tech_handler_id)
        tech = settings.get("Technology", "NORDLYNX").upper()
        self.technology_dropdown.set_active_id(tech)
        self.technology_dropdown.handler_unblock(self.tech_handler_id)

        # Update protocol
        self.protocol_dropdown.handler_block(self.proto_handler_id)
        proto = settings.get("Protocol", "UDP").upper()
        self.protocol_dropdown.set_active_id(proto)
        self.protocol_dropdown.handler_unblock(self.proto_handler_id)

        # Protocol sensitivity (only for OpenVPN)
        self.protocol_dropdown.set_sensitive(tech == "OPENVPN")

        return False

    def on_setting_toggled(self, switch, pspec, setting_key):
        """Handle boolean setting toggle."""
        # Disable switch while command executes
        switch.set_sensitive(False)
        active = switch.get_active()
        value = "enabled" if active else "disabled"

        def worker():
            success, message = self.manager.set_setting(setting_key, value)
            GLib.idle_add(self.on_setting_done, success, switch, setting_key)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_setting_done(self, success, switch, setting_key):
        """Handle setting change completion."""
        switch.set_sensitive(True)
        if not success:
            # Revert on failure
            handler_id = self.handler_ids.get(setting_key)
            if handler_id:
                switch.handler_block(handler_id)
                switch.set_active(not switch.get_active())
                switch.handler_unblock(handler_id)
        return False

    def on_technology_changed(self, combo):
        """Handle technology dropdown change."""
        # Disable dropdown while command executes
        combo.set_sensitive(False)
        technology = combo.get_active_id()

        def worker():
            success, message = self.manager.set_setting("Technology", technology)
            GLib.idle_add(self.on_technology_done, success, combo, technology)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_technology_done(self, success, combo, technology):
        """Handle technology dropdown change completion."""
        combo.set_sensitive(True)
        if not success:
            # Revert on failure would need to restore previous value
            pass
        else:
            # Enable/disable protocol dropdown based on technology
            # Protocol is only available for OpenVPN
            self.protocol_dropdown.set_sensitive(technology == "OPENVPN")
        return False

    def on_protocol_changed(self, combo):
        """Handle protocol dropdown change."""
        # Disable dropdown while command executes
        combo.set_sensitive(False)
        protocol = combo.get_active_id()

        def worker():
            success, message = self.manager.set_setting("Protocol", protocol)
            GLib.idle_add(self.on_dropdown_done, success, combo)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_dropdown_done(self, success, combo):
        """Handle dropdown change completion."""
        combo.set_sensitive(True)
        return False

    def get_autoconnect_config(self):
        """Return current auto-connect config."""
        return {
            "autoconnect_enabled": self.autoconnect_switch.get_active(),
            # Country/City selection removed in this version
        }
