#!/usr/bin/env python3
import sys
import json
import warnings
import gi
import logging
import re
from pathlib import Path

# Configure Logging
class SensitiveFilter(logging.Filter):
    """Filter to mask sensitive info (IPs, emails) in logs."""
    def filter(self, record):
        if not isinstance(record.msg, str):
            return True
        # Mask IPv4
        record.msg = re.sub(r'\b\d{1,3}(\.\d{1,3}){3}\b', '[IP_MASKED]', record.msg)
        # Mask potential emails/account names
        record.msg = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', '[ACCOUNT_MASKED]', record.msg)
        return True

def setup_logging():
    log_dir = Path.home() / ".cache" / "summit"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "summit.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Console Handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.addFilter(SensitiveFilter())
    logger.addHandler(ch)

    # File Handler
    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    fh.addFilter(SensitiveFilter())
    logger.addHandler(fh)

setup_logging()
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=DeprecationWarning)

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")

from gi.repository import Gtk, Gdk, Gio, GLib

# Resource loading
def register_resources():
    resource_file = Path("/usr/share/summit/resources/summit.gresource")
    if not resource_file.exists():
        resource_file = Path(__file__).parent / "resources" / "summit.gresource"

    if resource_file.exists():
        try:
            resource = Gio.Resource.load(str(resource_file))
            resource._register()
        except Exception as e:
            logger.error(f"Error loading resources: {e}")
    else:
        logger.warning(f"Resource file not found: {resource_file}")

register_resources()

from summit_manager import SummitManager
from status_pane import StatusPane
from servers_pane import ServersPane
from settings_pane import SettingsPane
from ports_pane import PortsPane
from meshnet_pane import MeshnetPane
from recent_pane import RecentPane
from toast import ToastOverlay

@Gtk.Template(resource_path="/io/github/summit/ui/main_window.ui")
class SummitWindow(Gtk.ApplicationWindow):
    """Main application window using Gtk.Template."""

    __gtype_name__ = "SummitWindow"

    header_bar = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    content_paned = Gtk.Template.Child()
    recent_pane_container = Gtk.Template.Child()

    status_btn = Gtk.Template.Child()
    servers_btn = Gtk.Template.Child()
    settings_btn = Gtk.Template.Child()
    ports_btn = Gtk.Template.Child()
    meshnet_btn = Gtk.Template.Child()

    def __init__(self, app, **kwargs):
        super().__init__(application=app, **kwargs)
        self.app = app
        self._updating_tabs = False

        self.tab_buttons = {
            "status": self.status_btn,
            "servers": self.servers_btn,
            "settings": self.settings_btn,
            "ports": self.ports_btn,
            "meshnet": self.meshnet_btn,
        }

        for name, btn in self.tab_buttons.items():
            btn.connect("toggled", self.on_tab_button_toggled, name)

        # Initialize ToastOverlay functionality
        self.toast_overlay.__class__ = ToastOverlay
        ToastOverlay.__init__(self.toast_overlay)

    def on_tab_button_toggled(self, button: Gtk.ToggleButton, tab_name: str):
        if self._updating_tabs:
            return

        if button.get_active():
            self._updating_tabs = True
            try:
                for name, btn in self.tab_buttons.items():
                    if name != tab_name:
                        btn.set_active(False)
                self.main_stack.set_visible_child_name(tab_name)
                self.update_right_pane_visibility()
            finally:
                self._updating_tabs = False
        else:
            self._updating_tabs = True
            try:
                button.set_active(True)
            finally:
                self._updating_tabs = False

    def update_right_pane_visibility(self):
        active_tab = self.main_stack.get_visible_child_name()
        if active_tab == "status":
            self.recent_pane_container.set_visible(True)
            self.content_paned.set_position(550)
        else:
            self.recent_pane_container.set_visible(False)
            self.content_paned.set_position(9999)

class SummitApp(Gtk.Application):
    """Summit - NordVPN Client for GTK4 Application."""

    def __init__(self):
        super().__init__(application_id="io.github.summit", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.manager = SummitManager()
        self.window = None
        self.config = {}
        self.poll_timer = None

        config_dir = Path.home() / ".config" / "summit"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = config_dir / "config.json"

        self.connect("startup", self.do_startup)
        self.connect("activate", self.on_activate)

    def do_startup(self, *args):
        Gtk.Application.do_startup(self)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/io/github/summit/resources/style.css")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        if not self.window:
            try:
                self.load_config()
                if not self.manager.is_installed():
                    dialog = Gtk.AlertDialog()
                    dialog.set_message("NordVPN Not Installed")
                    dialog.set_detail_text("Please install NordVPN first:\nsudo apt install nordvpn")
                    dialog.present(None)
                    self.quit()
                    return

                self.build_window()
                self.window.present()
            except Exception as e:
                logging.error(f"Failed to build window: {e}", exc_info=True)

    def build_window(self):
        self.window = SummitWindow(app=self)
        self.window.set_default_size(
            self.config.get("window_width", 900), self.config.get("window_height", 650)
        )
        self.window.connect("close-request", self.on_window_close)

        self.status_pane = StatusPane(
            self.manager,
            on_status_change=self.on_status_change,
            on_connect_click=self.switch_to_servers_tab,
        )
        self.status_pane.set_app_ref(self)

        self.servers_pane = ServersPane(self.manager)
        self.servers_pane.set_app_ref(self)

        self.settings_pane = SettingsPane(self.manager)
        self.settings_pane.autoconnect_switch.set_active(
            self.config.get("autoconnect_enabled", False)
        )

        self.ports_pane = PortsPane(self.manager)
        self.meshnet_pane = MeshnetPane(self.manager)

        self.recent_pane = RecentPane(self.manager)
        self.recent_pane.set_app_ref(self)
        self.recent_pane.refresh_favorites_display()

        self.window.main_stack.get_child_by_name("status").append(self.status_pane)
        self.window.main_stack.get_child_by_name("servers").append(self.servers_pane)
        self.window.main_stack.get_child_by_name("settings").append(self.settings_pane)
        self.window.main_stack.get_child_by_name("ports").append(self.ports_pane)
        self.window.main_stack.get_child_by_name("meshnet").append(self.meshnet_pane)
        self.window.recent_pane_container.append(self.recent_pane)

        self.load_autoconnect_background()
        self.start_polling()
        GLib.idle_add(self.check_login_status)

    def on_activate(self, app=None):
        if self.window:
            self.window.present()

    def check_login_status(self):
        def worker():
            is_logged_in = self.manager.is_logged_in()
            GLib.idle_add(self.show_login_dialog_if_needed, is_logged_in)
        import threading
        threading.Thread(target=worker, daemon=True).start()
        return False

    def show_login_dialog_if_needed(self, is_logged_in):
        if not is_logged_in:
            dialog = Gtk.AlertDialog()
            dialog.set_message("Not Logged In")
            dialog.set_detail_text("Please log in to NordVPN first:\nRun 'nordvpn login' in a terminal")
            dialog.present(self.window)
        return False

    def load_config(self):
        defaults = {
            "window_width": 900, "window_height": 650,
            "last_country": "United_States", "last_city": "Saint_Louis",
            "poll_interval_ms": 2000, "autoconnect_enabled": False,
            "autoconnect_country": "", "autoconnect_city": "", "favorites": [],
        }
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                    for key, val in defaults.items():
                        if key not in self.config: self.config[key] = val
            except Exception: self.config = defaults
        else: self.config = defaults

    def save_config(self):
        if self.window:
            self.config["window_width"] = self.window.get_width()
            self.config["window_height"] = self.window.get_height()
        if hasattr(self, "settings_pane"):
            self.config.update(self.settings_pane.get_autoconnect_config())
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")

    def show_toast(self, message: str, is_error: bool = False):
        if self.window and hasattr(self.window, "toast_overlay"):
            self.window.toast_overlay.show_toast(message, is_error)

    def load_autoconnect_background(self):
        def worker():
            countries = self.manager.get_countries()
            saved_country = self.config.get("autoconnect_country", "")
            saved_city = self.config.get("autoconnect_city", "")
            def populate():
                combo = self.settings_pane.autoconnect_country_combo
                combo.remove_all()
                combo.append("", "Select Country")
                for c in countries: combo.append(c, c)
                if saved_country:
                    combo.handler_block(self.settings_pane.autoconnect_country_handler_id)
                    combo.set_active_id(saved_country)
                    combo.handler_unblock(self.settings_pane.autoconnect_country_handler_id)
                    cities = self.manager.get_cities(saved_country)
                    city_combo = self.settings_pane.autoconnect_city_combo
                    city_combo.remove_all()
                    city_combo.append("", "Select City")
                    for city in cities: city_combo.append(city, city)
                    if saved_city: city_combo.set_active_id(saved_city)
            GLib.idle_add(populate)
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def start_polling(self):
        interval = self.config.get("poll_interval_ms", 2000)
        self.poll_timer = GLib.timeout_add(interval, self.poll_status)

    def poll_status(self):
        def worker():
            try:
                status = self.manager.get_status()
                if hasattr(self, "status_pane"):
                    GLib.idle_add(self.status_pane.apply_status, status)
                if hasattr(self, "recent_pane"):
                    GLib.idle_add(self.recent_pane.apply_status, status)
            except Exception as e:
                logging.error(f"Poll failed: {e}")
        import threading
        threading.Thread(target=worker, daemon=True).start()
        return True

    def on_status_change(self, status): pass
    def switch_to_servers_tab(self): self.window.tab_buttons["servers"].set_active(True)
    def on_window_close(self, window):
        if self.poll_timer: GLib.source_remove(self.poll_timer)
        self.save_config()
        return False

def main():
    GLib.set_prgname("summit")
    app = SummitApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
