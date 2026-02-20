import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from summit_manager import NordManager


class SettingsPane(Gtk.Box):
    """Tab 3: NordVPN Settings"""

    def __init__(self, nord: NordManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.nord = nord
        self.settings = {}
        self.switches = {}

        # Scrollable settings list with border
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        settings_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        settings_container.add_css_class("pane-box")
        settings_container.set_margin_top(8)
        settings_container.set_margin_bottom(8)
        settings_container.set_margin_start(8)
        settings_container.set_margin_end(8)

        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        settings_box.set_margin_top(4)
        settings_box.set_margin_bottom(4)
        settings_box.set_margin_start(4)
        settings_box.set_margin_end(4)

        # Auto-Connect section (at the top, inline with toggle, country, city)
        autoconnect_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        autoconnect_row.set_hexpand(True)

        self.autoconnect_switch = Gtk.Switch()
        self.autoconnect_switch.set_valign(Gtk.Align.CENTER)
        self.autoconnect_switch.connect("notify::active", self.on_autoconnect_toggled)

        autoconnect_label = Gtk.Label(label="Auto-Connect")
        autoconnect_label.set_hexpand(True)
        autoconnect_label.set_xalign(0)

        autoconnect_row.append(autoconnect_label)
        autoconnect_row.append(self.autoconnect_switch)

        # Country dropdown
        self.autoconnect_country_combo = Gtk.ComboBoxText()
        self.autoconnect_country_combo.set_sensitive(False)
        self.autoconnect_country_handler_id = self.autoconnect_country_combo.connect("changed", self.on_autoconnect_country_changed)
        self.autoconnect_country_combo.append("", "Select Country")
        autoconnect_row.append(self.autoconnect_country_combo)

        # City dropdown
        self.autoconnect_city_combo = Gtk.ComboBoxText()
        self.autoconnect_city_combo.set_sensitive(False)
        self.autoconnect_city_combo.connect("changed", self.on_autoconnect_city_changed)
        self.autoconnect_city_combo.append("", "Select City")
        autoconnect_row.append(self.autoconnect_city_combo)

        settings_box.append(autoconnect_row)

        # Technology (NORDLYNX, OPENVPN)
        tech_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tech_row.set_hexpand(True)

        tech_label = Gtk.Label(label="Technology", xalign=0)
        tech_label.set_hexpand(True)
        tech_row.append(tech_label)

        tech_dropdown = Gtk.DropDown.new_from_strings(["NORDLYNX", "OPENVPN"])
        tech_dropdown.connect("notify::selected", self.on_technology_changed)
        self.tech_dropdown = tech_dropdown
        tech_row.append(tech_dropdown)

        settings_box.append(tech_row)

        # Protocol (TCP, UDP)
        proto_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        proto_row.set_hexpand(True)

        proto_label = Gtk.Label(label="Protocol", xalign=0)
        proto_label.set_hexpand(True)
        proto_row.append(proto_label)

        proto_dropdown = Gtk.DropDown.new_from_strings(["TCP", "UDP"])
        proto_dropdown.connect("notify::selected", self.on_protocol_changed)
        self.proto_dropdown = proto_dropdown
        proto_row.append(proto_dropdown)

        settings_box.append(proto_row)

        # Boolean settings (toggles)
        boolean_settings = [
            ("Kill Switch", "Kill Switch"),
            ("Firewall", "Firewall"),
            ("Notify", "Notify"),
            ("Tray", "Tray"),
            ("Threat Protection Lite", "Threat Protection Lite"),
            ("LAN Discovery", "LAN Discovery"),
            ("Virtual Location", "Virtual Location"),
            ("Post-quantum VPN", "Post-quantum VPN"),
        ]

        for display_name, setting_key in boolean_settings:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.set_hexpand(True)

            label = Gtk.Label(label=display_name, xalign=0)
            label.set_hexpand(True)
            row.append(label)

            switch = Gtk.Switch()
            switch.set_valign(Gtk.Align.CENTER)
            handler_id = switch.connect("notify::active", self.on_setting_toggled, setting_key, switch)
            self.switches[setting_key] = (switch, display_name, handler_id)
            row.append(switch)

            settings_box.append(row)

        settings_container.append(settings_box)
        scrolled.set_child(settings_container)
        self.append(scrolled)

        # Load settings
        self.load_settings()

    def load_settings(self, synchronous=False):
        """Load settings. If synchronous=True, load immediately; else load in background."""
        if synchronous:
            # Synchronous load - called before window shows
            settings = self.nord.get_settings()
            self.apply_settings_to_ui(settings)
        else:
            # Asynchronous load - for updates after window is shown
            def worker():
                settings = self.nord.get_settings()
                GLib.idle_add(self.apply_settings_to_ui, settings)

            import threading
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()

    def apply_settings_to_ui(self, settings):
        """Update UI with loaded settings."""
        self.settings = settings

        # Update boolean switches - block signals while setting initial state
        for setting_key, (switch, display_name, handler_id) in self.switches.items():
            # Temporarily block signal handler
            switch.handler_block(handler_id)

            # NordVPN returns "enabled" or "disabled"
            value = settings.get(setting_key, "disabled").lower()
            switch.set_active(value == "enabled")

            # Unblock signal handler
            switch.handler_unblock(handler_id)

        # Update dropdowns - temporarily block signals
        tech_handler = self.tech_dropdown.connect("notify::selected", lambda *args: None)
        self.tech_dropdown.handler_block(tech_handler)

        technology = settings.get("Technology", "NORDLYNX").upper()
        if technology == "NORDLYNX":
            self.tech_dropdown.set_selected(0)
        else:
            self.tech_dropdown.set_selected(1)

        self.tech_dropdown.handler_unblock(tech_handler)
        self.tech_dropdown.disconnect(tech_handler)

        proto_handler = self.proto_dropdown.connect("notify::selected", lambda *args: None)
        self.proto_dropdown.handler_block(proto_handler)

        protocol = settings.get("Protocol", "TCP").upper()
        if protocol == "TCP":
            self.proto_dropdown.set_selected(0)
        else:
            self.proto_dropdown.set_selected(1)

        self.proto_dropdown.handler_unblock(proto_handler)
        self.proto_dropdown.disconnect(proto_handler)

        # Disable protocol dropdown if using NORDLYNX (protocol only works with OpenVPN)
        if technology == "NORDLYNX":
            self.proto_dropdown.set_sensitive(False)
        else:
            self.proto_dropdown.set_sensitive(True)

        return False

    def on_setting_toggled(self, switch, pspec, setting_key, widget):
        """Handle boolean setting toggle."""
        # Disable switch while command executes
        switch.set_sensitive(False)
        active = switch.get_active()
        value = "enabled" if active else "disabled"

        def worker():
            success, message = self.nord.set_setting(setting_key, value)
            GLib.idle_add(self.on_setting_done, success, switch)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_technology_changed(self, dropdown, pspec):
        """Handle technology dropdown change."""
        # Disable dropdown while command executes
        dropdown.set_sensitive(False)
        selected = dropdown.get_selected()
        technology = "NORDLYNX" if selected == 0 else "OPENVPN"

        def worker():
            success, message = self.nord.set_setting("Technology", technology)
            GLib.idle_add(self.on_technology_done, success, dropdown, selected, technology)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_protocol_changed(self, dropdown, pspec):
        """Handle protocol dropdown change."""
        # Disable dropdown while command executes
        dropdown.set_sensitive(False)
        selected = dropdown.get_selected()
        protocol = "TCP" if selected == 0 else "UDP"

        def worker():
            success, message = self.nord.set_setting("Protocol", protocol)
            GLib.idle_add(self.on_dropdown_done, success, dropdown, selected)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_setting_done(self, success, switch):
        """Handle setting change completion."""
        switch.set_sensitive(True)
        if not success:
            # Revert on failure
            switch.set_active(not switch.get_active())
        return False

    def on_dropdown_done(self, success, dropdown, selected):
        """Handle dropdown change completion."""
        dropdown.set_sensitive(True)
        if not success:
            # Revert on failure - would need to restore previous value
            pass
        return False

    def on_technology_done(self, success, dropdown, selected, technology):
        """Handle technology dropdown change completion."""
        dropdown.set_sensitive(True)
        if not success:
            # Revert on failure
            pass
        else:
            # Enable/disable protocol dropdown based on technology
            # Protocol is only available for OpenVPN
            if technology == "OPENVPN":
                self.proto_dropdown.set_sensitive(True)
            else:
                # NORDLYNX doesn't support protocol selection
                self.proto_dropdown.set_sensitive(False)
        return False

    def on_autoconnect_toggled(self, switch, param):
        """Handle auto-connect toggle."""
        enabled = switch.get_active()

        # Enable/disable dropdowns
        self.autoconnect_country_combo.set_sensitive(enabled)
        self.autoconnect_city_combo.set_sensitive(enabled)

        # Send CLI command in background
        def worker():
            if enabled:
                self.nord.run_command(["settings", "autoconnect", "on"])
            else:
                self.nord.run_command(["settings", "autoconnect", "off"])

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_autoconnect_country_changed(self, combo):
        """Handle country selection change."""
        country = combo.get_active_text()

        if not country:
            self.autoconnect_city_combo.remove_all()
            self.autoconnect_city_combo.append("", "Select City")
            return

        # Populate cities for selected country in background
        def worker():
            # country is already in underscore format from get_countries() (e.g., "United_States")
            cities = self.nord.get_cities(country)
            GLib.idle_add(self.populate_autoconnect_cities, cities)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def populate_autoconnect_cities(self, cities):
        """Populate city dropdown."""
        self.autoconnect_city_combo.remove_all()
        self.autoconnect_city_combo.append("", "Select City")
        for city in cities:
            self.autoconnect_city_combo.append(city, city)
        return False

    def on_autoconnect_city_changed(self, combo):
        """Handle city selection change."""
        # City selection is automatically saved when window closes via get_autoconnect_config()
        pass

    def get_autoconnect_config(self):
        """Return current auto-connect config."""
        return {
            "autoconnect_enabled": self.autoconnect_switch.get_active(),
            "autoconnect_country": self.autoconnect_country_combo.get_active_text() or "",
            "autoconnect_city": self.autoconnect_city_combo.get_active_text() or "",
        }
