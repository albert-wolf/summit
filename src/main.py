#!/usr/bin/env python3
import sys
import json
import subprocess
import shutil
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
        Path("/app/share/summit/resources/summit.gresource"),  # Flatpak location
        Path("/usr/share/summit/resources/summit.gresource"),  # Native system location
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
from toast import ToastOverlay


def get_version():
    try:
        import importlib.metadata

        return importlib.metadata.version("summit")
    except Exception:
        try:
            pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
            if not pyproject_path.exists():
                pyproject_path = Path(__file__).parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "r") as f:
                    content = f.read()
                m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    return m.group(1)
        except Exception:
            pass
    return "0.9.2"


@Gtk.Template(resource_path="/io/github/summit/ui/main_window.ui")
class SummitWindow(Gtk.ApplicationWindow):
    """Main application window using Gtk.Template."""

    __gtype_name__ = "SummitWindow"

    header_bar = Gtk.Template.Child("header_bar")
    main_stack = Gtk.Template.Child("main_stack")
    toast_overlay = Gtk.Template.Child("toast_overlay")
    app_title_label = Gtk.Template.Child("app_title_label")

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

        # Dynamically set headerbar app title with version
        self.app_title_label.set_label(f"Summit {get_version()}")

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


class SummitApp(Gtk.Application):
    """Summit - NordVPN Client for GTK4 Application."""

    def __init__(self):
        super().__init__(application_id="io.github.summit", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.manager = SummitManager()

        # Check for mock status flag (used for automated screenshots and privacy)
        if "--mock-status" in sys.argv:
            self.manager.is_logged_in = lambda: True
            self.manager.is_installed = lambda: True
            self.manager.get_status = lambda: {
                "Status": "Connected",
                "Country": "United States",
                "City": "Las Vegas",
                "IP": "198.51.100.45",
                "Current protocol": "UDP",
                "Current technology": "NordLynx",
                "Server": "us1425",
                "Uptime": "02:14:35",
                "Transfer": "14.2 MB Up / 158.4 MB Down",
            }
            self.manager.get_meshnet_peers = lambda: (False, [])
            self.manager.get_this_device_info = lambda: None

            # Prevent connect/disconnect actions from running actual commands
            self.manager.connect = lambda country, city=None: (True, "Mock Connect Success")
            self.manager.disconnect = lambda: (True, "Mock Disconnect Success")
            self.manager.reconnect = lambda country=None, city=None: (
                True,
                "Mock Reconnect Success",
            )

        self.window = None
        self.config = {}
        self.poll_timer = None
        self._is_polling = False

        # Set up Network Monitor to capture network changes instantly
        self.network_monitor = Gio.NetworkMonitor.get_default()
        if self.network_monitor:
            self.network_monitor.connect("network-changed", self.on_network_changed)

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
        dialog.set_version(get_version())
        dialog.set_authors(["Wolf-GitHub <Wolf-GitHub@pm.me>"])
        dialog.set_comments("A GTK4 NordVPN Client for LMDE 7")
        dialog.set_website("https://github.com/Wolf-GitHub/Summit")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_logo_icon_name("network-vpn")
        dialog.present()

    def do_startup(self, *args):
        Gtk.Application.do_startup(self)

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
                    dialog.set_detail("Please install NordVPN first:\nsudo apt install nordvpn")
                    dialog.show(None)
                    self.quit()
                    return

                self.build_window()
                self.window.present()

                if "--screenshot-mode" in sys.argv:
                    GLib.timeout_add(3000, self.take_screenshot_step, 0)
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

        self.window.status_pane_box.append(self.status_pane)
        self.window.servers_pane_box.append(self.servers_pane)
        self.window.settings_pane_box.append(self.settings_pane)
        self.window.ports_pane_box.append(self.ports_pane)
        self.window.meshnet_pane_box.append(self.meshnet_pane)

        # Track window focus state to pause/resume polling
        self.window.connect("notify::is-active", self.on_window_active_changed)

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
            dialog.set_detail("Please log in to NordVPN first:\nRun 'nordvpn login' in a terminal")
            dialog.show(self.window)
        return False

    def load_config(self):
        defaults = {
            "window_width": 900,
            "window_height": 650,
            "last_country": "United_States",
            "last_city": "Saint_Louis",
            "poll_interval_ms": 10000,
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
        # Only start if safety polling timer is not already active
        if not self.poll_timer:
            interval = self.config.get("poll_interval_ms", 10000)
            if interval < 10000:
                interval = 10000
            self.poll_timer = GLib.timeout_add(interval, self._safety_poll_callback)
            logger.info(f"Safety polling started at {interval}ms interval.")

    def _safety_poll_callback(self):
        self.poll_status()
        return True

    def stop_polling(self):
        if self.poll_timer:
            GLib.source_remove(self.poll_timer)
            self.poll_timer = None
            logger.info("Safety polling stopped.")

    def resume_polling(self):
        logger.info("Resuming polling due to window activation.")
        self.start_polling()
        self.poll_status()

    def pause_polling(self):
        logger.info("Pausing polling due to window defocus.")
        self.stop_polling()

    def poll_status(self):
        if getattr(self, "_is_polling", False):
            return
        self._is_polling = True

        def worker():
            try:
                status = self.manager.get_status()
                if hasattr(self, "status_pane"):
                    GLib.idle_add(self.status_pane.apply_status, status)
            except Exception as e:
                logger.error(f"Poll failed: {e}")
            finally:
                self._is_polling = False

        import threading

        threading.Thread(target=worker, daemon=True).start()

    def on_window_active_changed(self, window, pspec):
        is_active = window.get_property("is-active")
        logger.info(f"Window active state changed: {is_active}")
        if is_active:
            self.resume_polling()
        else:
            self.pause_polling()

    def on_network_changed(self, monitor, network_available):
        logger.info(
            f"Network changed: available={network_available}. Triggering immediate status poll."
        )
        self.poll_status()

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
        self.stop_polling()
        self.save_config()
        return False

    def take_screenshot_step(self, step):
        tabs = ["status", "servers", "settings", "ports", "meshnet"]
        if step >= len(tabs):
            self.quit()
            return False

        tab_name = tabs[step]
        logger.info(f"Screenshot mode - cycling to tab: {tab_name}")
        self.window.tab_buttons[tab_name].set_active(True)

        def capture():
            try:
                screenshot_dir = Path(__file__).parent.parent / "docs" / "screenshots"
                screenshot_dir.mkdir(parents=True, exist_ok=True)

                output_path = screenshot_dir / f"{tab_name}.png"

                # Check for available screenshot tools in order of preference
                if shutil.which("maim"):
                    try:
                        window_id = (
                            subprocess.check_output(
                                ["xdotool", "search", "--onlyvisible", "--class", "summit"]
                            )
                            .decode()
                            .strip()
                            .split("\n")[0]
                        )
                        subprocess.run(["maim", "-i", window_id, str(output_path)], check=True)
                        logger.info(f"Captured screen using maim: {output_path}")
                    except Exception:
                        subprocess.run(["maim", str(output_path)], check=True)
                        logger.info(f"Captured screen using full maim fallback: {output_path}")
                elif shutil.which("scrot"):
                    subprocess.run(["scrot", "-u", str(output_path)], check=True)
                    logger.info(f"Captured screen using scrot: {output_path}")
                elif shutil.which("gnome-screenshot"):
                    # -w takes active window
                    subprocess.run(["gnome-screenshot", "-w", "-f", str(output_path)], check=True)
                    logger.info(f"Captured screen using gnome-screenshot: {output_path}")
                elif shutil.which("cinnamon-screenshot"):
                    # -w takes active window
                    subprocess.run(
                        ["cinnamon-screenshot", "-w", "-f", str(output_path)], check=True
                    )
                    logger.info(f"Captured screen using cinnamon-screenshot: {output_path}")
                else:
                    logger.error(
                        "Error: no screenshot utility (maim, scrot, gnome-screenshot, cinnamon-screenshot) found."
                    )
            except Exception as e:
                logger.error(f"Screenshot capture failed: {e}")

            # Queue next step
            GLib.timeout_add(1000, self.take_screenshot_step, step + 1)

        # Allow GTK 1 second to render the tab completely before snapping
        GLib.timeout_add(1000, capture)
        return False


def main():
    GLib.set_prgname("summit")
    app = SummitApp()
    # Filter out custom arguments so GTK's strict CLI parser doesn't intercept them
    gtk_args = [arg for arg in sys.argv if arg not in ("--mock-status", "--screenshot-mode")]
    return app.run(gtk_args)


if __name__ == "__main__":
    sys.exit(main())
