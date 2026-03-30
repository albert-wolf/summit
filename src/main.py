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
        record.msg = re.sub(r"\b\d{1,3}(\.\d{1,3}){3}\b", "[IP_MASKED]", record.msg)
        # Mask potential emails/account names
        record.msg = re.sub(r"\b[\w\.-]+@[\w\.-]+\.\w{2,}\b", "[ACCOUNT_MASKED]", record.msg)
        return True


def setup_logging():
    log_dir = Path.home() / ".cache" / "summit"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "summit.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

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
    # Prioritize local resources for development
    resource_file = Path(__file__).parent / "resources" / "summit.gresource"
    
    # Locations to check for the resource bundle
    search_paths = [
        resource_file,
        Path("/app/share/summit/resources/summit.gresource"),    # Flatpak location
        Path("/usr/share/summit/resources/summit.gresource")    # Native system location
    ]

    for path in search_paths:
        if path.exists():
            try:
                resource = Gio.Resource.load(str(path))
                Gio.resources_register(resource)
                logger.info(f"Successfully registered resources from {path}")
                return
            except Exception as e:
                logger.error(f"Error loading resources from {path}: {e}")
    
    logger.warning("Resource file not found in any standard location.")


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

    header_bar = Gtk.Template.Child("header_bar")
    main_stack = Gtk.Template.Child("main_stack")
    toast_overlay = Gtk.Template.Child("toast_overlay")
    content_paned = Gtk.Template.Child("content_paned")
    recent_pane_container = Gtk.Template.Child("recent_pane_container")

    status_btn = Gtk.Template.Child("status_btn")
    servers_btn = Gtk.Template.Child("servers_btn")
    settings_btn = Gtk.Template.Child("settings_btn")
    ports_btn = Gtk.Template.Child("ports_btn")
    meshnet_btn = Gtk.Template.Child("meshnet_btn")

    status_pane_box = Gtk.Template.Child("status_pane_box")
    servers_pane_box = Gtk.Template.Child("servers_pane_box")
    settings_pane_box = Gtk.Template.Child("settings_pane_box")
    ports_pane_box = Gtk.Template.Child("ports_pane_box")
    meshnet_pane_box = Gtk.Template.Child("meshnet_pane_box")

    def __init__(self, app, **kwargs):
        super().__init__(application=app, **kwargs)
        self.init_template()
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

        # Initialize ToastOverlay wrapper
        self.toast_overlay_wrapper = ToastOverlay(self.toast_overlay)

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
                
                # Refresh data when switching to relevant tabs
                if tab_name == "settings" and hasattr(self, "settings_pane"):
                    self.settings_pane.load_settings()
                elif tab_name == "meshnet" and hasattr(self, "meshnet_pane"):
                    self.meshnet_pane.load_meshnet_state_async()
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
        self.add_custom_actions()

    def add_custom_actions(self):
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)

    def on_about_action(self, action, param):
        dialog = Gtk.AboutDialog()
        dialog.set_transient_for(self.window)
        dialog.set_program_name("Summit")
        dialog.set_version("0.8.3")
        dialog.set_authors(["Wolf-GitHub <Wolf-GitHub@pm.me>"])
        dialog.set_comments("A GTK4 NordVPN Client for LMDE 7")
        dialog.set_website("https://github.com/Wolf-GitHub/Summit")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_logo_icon_name("network-vpn")
        dialog.present()

    def do_startup(self, *args):
        Gtk.Application.do_startup(self)

        # Sync appearance with system settings (Light/Dark mode)
        settings = Gtk.Settings.get_default()
        
        # Apply custom styling from GResource
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
                    dialog.set_detail(
                        "Please install NordVPN first:\nsudo apt install nordvpn"
                    )
                    dialog.show(None)
                    self.quit()
                    return

                self.build_window()
                self.window.present()
            except Exception as e:
                logger.error(f"Failed to build window: {e}", exc_info=True)

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

        self.settings_pane = SettingsPane(self.manager, self.config)
        self.settings_pane.set_app_ref(self)

        self.ports_pane = PortsPane(self.manager)
        self.meshnet_pane = MeshnetPane(self.manager)
        self.meshnet_pane.set_app_ref(self)

        self.recent_pane = RecentPane(self.manager)
        self.recent_pane.set_app_ref(self)
        self.recent_pane.refresh_favorites_display()

        self.window.status_pane_box.append(self.status_pane)
        self.window.servers_pane_box.append(self.servers_pane)
        self.window.settings_pane_box.append(self.settings_pane)
        self.window.ports_pane_box.append(self.ports_pane)
        self.window.meshnet_pane_box.append(self.meshnet_pane)
        self.window.recent_pane_container.append(self.recent_pane)

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
            dialog.set_detail(
                "Please log in to NordVPN first:\nRun 'nordvpn login' in a terminal"
            )
            dialog.show(self.window)
        return False

    def load_config(self):
        defaults = {
            "window_width": 900,
            "window_height": 650,
            "last_country": "United_States",
            "last_city": "Saint_Louis",
            "poll_interval_ms": 2000,
            "autoconnect_enabled": False,
            "autoconnect_country": "",
            "autoconnect_city": "",
            "favorites": [],
        }
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                    for key, val in defaults.items():
                        if key not in self.config:
                            self.config[key] = val
            except Exception:
                self.config = defaults
        else:
            self.config = defaults

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
            logger.error(f"Failed to save config: {e}")

    def show_toast(self, message: str, is_error: bool = False):
        if self.window and hasattr(self.window, "toast_overlay_wrapper"):
            self.window.toast_overlay_wrapper.show_toast(message, is_error)

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
                logger.error(f"Poll failed: {e}")

        import threading

        threading.Thread(target=worker, daemon=True).start()
        return True

    def on_status_change(self, status):
        pass

    def on_meshnet_state_changed(self, enabled: bool):
        """Called when meshnet state is changed in the Meshnet pane."""
        # Small delay to let CLI state settle before refresh
        def refresh():
            # Refresh meshnet pane to sync its switch and peer list
            if hasattr(self, "meshnet_pane"):
                if enabled:
                    self.meshnet_pane.load_meshnet_peers()
                else:
                    self.meshnet_pane.apply_meshnet_state(False, [])
            return False

        GLib.timeout_add(1000, refresh)

    def switch_to_servers_tab(self):
        self.window.tab_buttons["servers"].set_active(True)

    def on_window_close(self, window):
        if self.poll_timer:
            GLib.source_remove(self.poll_timer)
        self.save_config()
        return False


def main():
    GLib.set_prgname("summit")
    app = SummitApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
