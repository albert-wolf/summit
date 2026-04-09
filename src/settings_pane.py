import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
import threading
import logging
from summit_manager import SummitManager

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/summit/ui/settings_pane.ui")
class SettingsPane(Gtk.Box):
    """Tab 3: NordVPN Settings"""

    __gtype_name__ = "SettingsPane"

    killswitch_switch = Gtk.Template.Child()
    firewall_switch = Gtk.Template.Child()
    autoconnect_switch = Gtk.Template.Child()
    autoconnect_location_dropdown = Gtk.Template.Child()
    autoconnect_city_dropdown = Gtk.Template.Child()
    lan_discovery_switch = Gtk.Template.Child()
    virtual_location_switch = Gtk.Template.Child()
    threat_protection_lite_switch = Gtk.Template.Child()
    obfuscate_switch = Gtk.Template.Child()
    notify_switch = Gtk.Template.Child()
    technology_dropdown = Gtk.Template.Child()
    protocol_dropdown = Gtk.Template.Child()

    def __init__(self, manager: SummitManager, config: dict):
        super().__init__()
        try:
            self.init_template()
        except Exception as e:
            logger.error(f"Failed to initialize template for SettingsPane: {e}")
            raise

        self.manager = manager
        self.app = None
        self.config = config
        self.settings = {}
        self._is_loading = False

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
        }

        # Store handler IDs for blocking
        self.handler_ids = {}

        # Connect switches
        for key, switch in self.switch_map.items():
            if switch:
                handler_id = switch.connect("notify::active", self.on_setting_toggled, key)
                self.handler_ids[key] = handler_id

        # Initialize technology dropdown
        self.tech_strings = ["NordLynx", "OpenVPN"]
        self.tech_model = Gtk.StringList.new(self.tech_strings)
        self.technology_dropdown.set_model(self.tech_model)
        self.tech_handler_id = self.technology_dropdown.connect(
            "notify::selected", self.on_technology_changed
        )

        # Initialize protocol dropdown
        self.proto_strings = ["UDP", "TCP"]
        self.proto_model = Gtk.StringList.new(self.proto_strings)
        self.protocol_dropdown.set_model(self.proto_model)
        self.proto_handler_id = self.protocol_dropdown.connect(
            "notify::selected", self.on_protocol_changed
        )

        # Initialize auto-connect location dropdown
        self.location_strings = ["Random"]
        self.location_model = Gtk.StringList.new(self.location_strings)
        self.autoconnect_location_dropdown.set_model(self.location_model)
        self.loc_handler_id = self.autoconnect_location_dropdown.connect(
            "notify::selected", self.on_autoconnect_location_changed
        )

        # Initialize auto-connect city dropdown
        self.city_strings = ["Any City"]
        self.city_model = Gtk.StringList.new(self.city_strings)
        self.autoconnect_city_dropdown.set_model(self.city_model)
        self.city_handler_id = self.autoconnect_city_dropdown.connect(
            "notify::selected", self.on_autoconnect_city_changed
        )

        # Load settings and locations
        self.load_initial_data()

    def set_app_ref(self, app):
        """Set reference to the main application."""
        self.app = app

    def load_initial_data(self):
        """Load settings and country list."""

        def worker():
            settings = self.manager.get_settings()
            countries = self.manager.get_countries()
            GLib.idle_add(self.apply_initial_data, settings, countries)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def apply_initial_data(self, settings, countries):
        """Update UI with loaded data."""
        self._is_loading = True
        try:
            # Update locations dropdown
            self.autoconnect_location_dropdown.handler_block(self.loc_handler_id)
            self.location_strings = ["Random"] + sorted(countries)
            new_model = Gtk.StringList.new(self.location_strings)
            self.autoconnect_location_dropdown.set_model(new_model)
            self.location_model = new_model
            self.autoconnect_location_dropdown.handler_unblock(self.loc_handler_id)

            # Apply settings
            self.apply_settings_to_ui(settings)
        finally:
            self._is_loading = False
        return False

    def load_settings(self, synchronous=False):
        """Load settings. If synchronous=True, load immediately; else load in background."""
        if synchronous:
            settings = self.manager.get_settings()
            self._is_loading = True
            try:
                self.apply_settings_to_ui(settings)
            finally:
                self._is_loading = False
        else:

            def worker():
                settings = self.manager.get_settings()
                GLib.idle_add(self._apply_settings_idle, settings)

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()

    def _apply_settings_idle(self, settings):
        self._is_loading = True
        try:
            self.apply_settings_to_ui(settings)
        finally:
            self._is_loading = False
        return False

    def apply_settings_to_ui(self, settings):
        """Update UI with loaded settings."""
        self.settings = settings
        self._is_loading = True

        try:
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
            if tech == "NORDLYNX":
                self.technology_dropdown.set_selected(0)
            elif tech == "OPENVPN":
                self.technology_dropdown.set_selected(1)
            self.technology_dropdown.handler_unblock(self.tech_handler_id)

            # Update protocol
            self.protocol_dropdown.handler_block(self.proto_handler_id)
            proto = settings.get("Protocol", "UDP").upper()
            if proto == "UDP":
                self.protocol_dropdown.set_selected(0)
            elif proto == "TCP":
                self.protocol_dropdown.set_selected(1)
            self.protocol_dropdown.handler_unblock(self.proto_handler_id)

            # Update Auto-connect Location and City
            self.autoconnect_location_dropdown.handler_block(self.loc_handler_id)
            self.autoconnect_city_dropdown.handler_block(self.city_handler_id)

            ac_value = settings.get("Auto-connect", "disabled")
            ac_enabled = ac_value.lower().startswith("enabled")

            # Decouple selection from enabled state: Always prefer config/last selection
            # Try to parse CLI output first (rarely has location details)
            country_match = None
            city_match = None

            ac_clean = ac_value.replace("(", " ").replace(")", " ").replace(",", " ")
            parts = ac_clean.split()
            if len(parts) > 1:
                country_match = parts[1]
                if len(parts) > 2:
                    city_match = parts[2]

            # Fallback to persistent config (ALWAYS, even if disabled)
            if not country_match:
                country_match = self.config.get("autoconnect_country")
            if not city_match:
                city_match = self.config.get("autoconnect_city")

            if country_match:
                try:
                    idx = self.location_strings.index(country_match)
                    self.autoconnect_location_dropdown.set_selected(idx)
                    # Load cities to restore selection
                    self._load_autoconnect_cities(country_match, city_match, trigger_apply=False)
                except ValueError:
                    self.autoconnect_location_dropdown.set_selected(0)
                    self._update_city_dropdown([])
            else:
                self.autoconnect_location_dropdown.set_selected(0)
                self._update_city_dropdown([])

            self.autoconnect_location_dropdown.handler_unblock(self.loc_handler_id)
            self.autoconnect_city_dropdown.handler_unblock(self.city_handler_id)

            # Sensitivity
            self.protocol_dropdown.set_sensitive(tech == "OPENVPN")
            self.autoconnect_location_dropdown.set_sensitive(ac_enabled)
            self.autoconnect_city_dropdown.set_sensitive(
                ac_enabled and self.autoconnect_location_dropdown.get_selected() > 0
            )
        finally:
            self._is_loading = False

        return False

    def on_setting_toggled(self, switch, pspec, setting_key):
        """Handle boolean setting toggle."""
        if self._is_loading:
            return

        switch.set_sensitive(False)
        active = switch.get_active()
        value = "on" if active else "off"

        # Special handling for Auto-connect to include location if enabled
        if setting_key == "Auto-connect" and active:
            loc_idx = self.autoconnect_location_dropdown.get_selected()
            if loc_idx > 0:  # Not "Random"
                location = self.location_strings[loc_idx]
                value = f"on {location}"
                city_idx = self.autoconnect_city_dropdown.get_selected()
                if city_idx > 0:  # Not "Any City"
                    city = self.city_strings[city_idx]
                    value = f"on {location} {city}"

        def worker():
            success, message = self.manager.set_setting(setting_key, value)
            GLib.idle_add(self.on_setting_done, success, switch, setting_key)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_setting_done(self, success, switch, setting_key):
        """Handle setting change completion."""
        switch.set_sensitive(True)
        if not success:
            handler_id = self.handler_ids.get(setting_key)
            if handler_id:
                switch.handler_block(handler_id)
                switch.set_active(not switch.get_active())
                switch.handler_unblock(handler_id)
        else:
            # Update sensitivity of location dropdown if Auto-connect changed
            if setting_key == "Auto-connect":
                active = switch.get_active()
                self.autoconnect_location_dropdown.set_sensitive(active)
                loc_selected = self.autoconnect_location_dropdown.get_selected() > 0
                self.autoconnect_city_dropdown.set_sensitive(active and loc_selected)
        return False

    def on_technology_changed(self, dropdown, pspec):
        """Handle technology dropdown change."""
        if self._is_loading:
            return

        idx = dropdown.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return

        technology = self.tech_strings[idx].upper()
        dropdown.set_sensitive(False)

        def worker():
            success, message = self.manager.set_setting("Technology", technology)
            GLib.idle_add(self.on_technology_done, success, dropdown, technology)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_technology_done(self, success, dropdown, technology):
        """Handle technology dropdown change completion."""
        dropdown.set_sensitive(True)
        if success:
            self.protocol_dropdown.set_sensitive(technology == "OPENVPN")
        return False

    def on_protocol_changed(self, dropdown, pspec):
        """Handle protocol dropdown change."""
        if self._is_loading:
            return

        idx = dropdown.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return

        protocol = self.proto_strings[idx].upper()
        dropdown.set_sensitive(False)

        def worker():
            success, message = self.manager.set_setting("Protocol", protocol)
            GLib.idle_add(self.on_dropdown_done, success, dropdown)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_autoconnect_location_changed(self, dropdown, pspec):
        """Handle auto-connect location change."""
        if self._is_loading:
            return

        loc_idx = dropdown.get_selected()
        if loc_idx == Gtk.INVALID_LIST_POSITION:
            return

        location = self.location_strings[loc_idx]

        if location == "Random":
            self._update_city_dropdown([])
            self.autoconnect_city_dropdown.set_sensitive(False)
            if self.autoconnect_switch.get_active():
                self._apply_autoconnect("on")
        else:
            self.autoconnect_city_dropdown.set_sensitive(self.autoconnect_switch.get_active())
            # trigger_apply=True when user manually changes it
            self._load_autoconnect_cities(location, trigger_apply=True)

    def _load_autoconnect_cities(self, country, select_city=None, trigger_apply=False):
        """Load cities for auto-connect country selection."""

        def worker():
            cities = self.manager.get_cities(country)
            GLib.idle_add(
                self._on_autoconnect_cities_loaded, cities, country, select_city, trigger_apply
            )

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_autoconnect_cities_loaded(self, cities, country, select_city, trigger_apply):
        """Update city dropdown after loading."""
        self._update_city_dropdown(cities, select_city)

        # Only trigger an actual NordVPN set command if this was a user change
        if trigger_apply and self.autoconnect_switch.get_active():
            value = f"on {country}"
            idx = self.autoconnect_city_dropdown.get_selected()
            if idx > 0:
                city = self.city_strings[idx]
                value = f"on {country} {city}"
            self._apply_autoconnect(value)
        return False

    def _update_city_dropdown(self, cities, select_city=None):
        """Update the city dropdown model."""
        self.autoconnect_city_dropdown.handler_block(self.city_handler_id)
        self.city_strings = ["Any City"] + sorted(cities)
        new_model = Gtk.StringList.new(self.city_strings)
        self.autoconnect_city_dropdown.set_model(new_model)
        self.city_model = new_model

        if select_city:
            try:
                idx = self.city_strings.index(select_city)
                self.autoconnect_city_dropdown.set_selected(idx)
            except ValueError:
                self.autoconnect_city_dropdown.set_selected(0)
        else:
            self.autoconnect_city_dropdown.set_selected(0)

        self.autoconnect_city_dropdown.handler_unblock(self.city_handler_id)

    def on_autoconnect_city_changed(self, dropdown, pspec):
        """Handle auto-connect city change."""
        if self._is_loading:
            return

        if not self.autoconnect_switch.get_active():
            return

        loc_idx = self.autoconnect_location_dropdown.get_selected()
        if loc_idx <= 0:
            return

        country = self.location_strings[loc_idx]
        city_idx = dropdown.get_selected()

        value = f"on {country}"
        if city_idx > 0:
            city = self.city_strings[city_idx]
            value = f"on {country} {city}"

        self._apply_autoconnect(value)

    def _apply_autoconnect(self, value):
        """Set auto-connect setting."""
        self.autoconnect_location_dropdown.set_sensitive(False)
        self.autoconnect_city_dropdown.set_sensitive(False)

        def worker():
            success, message = self.manager.set_setting("Auto-connect", value)
            GLib.idle_add(self._on_autoconnect_apply_done, success)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_autoconnect_apply_done(self, success):
        """Finish auto-connect apply."""
        self.autoconnect_location_dropdown.set_sensitive(True)
        loc_selected = self.autoconnect_location_dropdown.get_selected() > 0
        self.autoconnect_city_dropdown.set_sensitive(loc_selected)
        return False

    def on_dropdown_done(self, success, dropdown):
        """Handle dropdown change completion."""
        dropdown.set_sensitive(True)
        return False

    def get_autoconnect_config(self):
        """Return current auto-connect config."""
        loc_idx = self.autoconnect_location_dropdown.get_selected()
        location = self.location_strings[loc_idx] if loc_idx > 0 else None
        city_idx = self.autoconnect_city_dropdown.get_selected()
        city = self.city_strings[city_idx] if city_idx > 0 else None
        return {
            "autoconnect_enabled": self.autoconnect_switch.get_active(),
            "autoconnect_country": location,
            "autoconnect_city": city,
        }
