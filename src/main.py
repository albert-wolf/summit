#!/usr/bin/env python3
import sys
import os
import json
import warnings
import gi

warnings.filterwarnings("ignore", category=DeprecationWarning)

gi.require_version('Gtk', '4.0')
gi.require_version('Gio', '2.0')

from gi.repository import Gtk, Gio, GLib, Gdk
from pathlib import Path

# Try to import Adwaita for better theme detection
try:
    gi.require_version('Adw', '1')
    from gi.repository import Adw
    HAS_ADWAITA = True
except (ValueError, ImportError):
    HAS_ADWAITA = False

from summit_manager import NordManager
from status_pane import StatusPane
from servers_pane import ServersPane
from settings_pane import SettingsPane
from ports_pane import PortsPane
from meshnet_pane import MeshnetPane
from recent_pane import RecentPane
from toast import ToastOverlay


class SummitApp(Gtk.Application):
    """Summit - NordVPN Client for GTK4 Application."""

    def __init__(self):
        super().__init__(
            application_id="io.github.summit",
            flags=Gio.ApplicationFlags.NON_UNIQUE
        )
        self.nord = NordManager()
        self.window = None
        self.config = {}
        self.poll_timer = None
        self._updating_tabs = False

        # Config path
        config_dir = Path.home() / ".config" / "summit"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = config_dir / "config.json"

        self.connect("startup", self.do_startup)
        self.connect("activate", self.on_activate)

    def do_startup(self, *args):
        """Called during startup. Create window here."""
        Gtk.Application.do_startup(self)
        self.load_css()

        # Listen for system theme changes
        if HAS_ADWAITA:
            try:
                style_manager = Adw.StyleManager.get_default()
                if style_manager:
                    style_manager.connect("notify::dark", self.on_theme_changed)
            except Exception:
                pass

        if not self.window:
            try:
                self.load_config()
                # Check nordvpn installed
                if not self.nord.is_installed():
                    dialog = Gtk.AlertDialog()
                    dialog.set_message("NordVPN Not Installed")
                    dialog.set_detail_text("Please install NordVPN first:\nsudo apt install nordvpn")
                    dialog.present(self.window if self.window else None)
                    self.quit()
                    return

                self.build_window()
                # Show window immediately without waiting for data to load
                self.window.present()

                # Do all post-show work in background thread to keep UI responsive
                def load_all():
                    import threading
                    # Restore window state
                    GLib.idle_add(self.restore_window_state)
                    # Update pane visibility
                    GLib.idle_add(self.update_right_pane_visibility)
                    # Load initial pane data (settings, status, etc.)
                    self.load_initial_pane_data()
                    # Reapply CSS (slow, do it last)
                    GLib.idle_add(self.reapply_css)

                thread = threading.Thread(target=load_all, daemon=True)
                thread.start()
            except Exception as e:
                print(f"[ERROR] Failed to build window: {e}")
                import traceback
                traceback.print_exc()

    def on_activate(self, app=None):
        """Called when app is activated."""
        if self.window:
            self.window.present()
            GLib.idle_add(self.restore_window_state)
            GLib.idle_add(self.update_right_pane_visibility)  # Update visibility after window shows
            # Reapply CSS after window is shown to override any theme defaults
            GLib.idle_add(self.reapply_css)

    def load_css(self):
        """Load CSS styling."""
        debug_log = Path("/tmp/summit_css_debug.log")
        try:
            with open(debug_log, "w") as f:
                f.write("=== CSS Loading Debug ===\n")

                css_provider = Gtk.CssProvider()
                script_dir = Path(__file__).parent

                # Try to load from bundled style.css
                css_locations = [
                    script_dir / ".." / "style.css",
                    Path.home() / ".config" / "summit" / "style.css",
                    script_dir / "style.css",
                ]

                css_file = None
                for loc in css_locations:
                    exists = loc.exists()
                    f.write(f"Checking: {loc} - exists: {exists}\n")
                    if exists:
                        css_file = loc
                        break

                if css_file:
                    f.write(f"Loading from: {css_file.resolve()}\n")
                    try:
                        css_provider.load_from_path(str(css_file.resolve()))
                        f.write(f"Loaded successfully\n")
                    except Exception as e:
                        f.write(f"Error loading file: {e}\n")
                else:
                    f.write(f"No file found, using inline fallback\n")
                    # Inline fallback
                    css_provider.load_from_string(self.get_inline_css())

                display = Gdk.Display.get_default()
                if display:
                    Gtk.StyleContext.add_provider_for_display(
                        display, css_provider,
                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                    )
                    f.write(f"Provider added to display\n")
                else:
                    f.write(f"ERROR: Could not get display\n")

                # Add highest-priority headerbar theme override
                headerbar_provider = Gtk.CssProvider()
                headerbar_provider.load_from_string(
                    "headerbar.dark-mode { background-color: #222226; color: #e0e0e0; } "
                    "headerbar.light-mode { background-color: #ebebed; color: #333333; }"
                )
                if display:
                    # Use highest priority to ensure headerbar colors apply
                    Gtk.StyleContext.add_provider_for_display(
                        display, headerbar_provider,
                        Gtk.STYLE_PROVIDER_PRIORITY_USER
                    )
                    f.write(f"Headerbar provider added to display with PRIORITY_USER\n")
        except Exception as e:
            import traceback
            with open(debug_log, "a") as f:
                f.write(f"ERROR: {e}\n")
                f.write(traceback.format_exc())

    def get_inline_css(self) -> str:
        """Inline CSS fallback."""
        return """
        window {
            background-color: #1a1a1a;
            color: #e0e0e0;
        }
        button {
            background-color: #353535;
            color: #e0e0e0;
        }
        button:hover {
            background-color: #454545;
        }
        """

    def load_config(self):
        """Load configuration with defaults."""
        defaults = {
            "window_width": 900,
            "window_height": 650,
            "last_country": "United_States",
            "last_city": "Saint_Louis",
            "active_tab": 0,
            "poll_interval_ms": 2000,
            "autoconnect_enabled": False,
            "autoconnect_country": "",
            "autoconnect_city": "",
            "favorites": [],
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                    # Merge with defaults
                    for key, val in defaults.items():
                        if key not in self.config:
                            self.config[key] = val
            except Exception:
                self.config = defaults
        else:
            self.config = defaults

    def save_config(self):
        """Save configuration to file."""
        if self.window:
            self.config["window_width"] = self.window.get_width()
            self.config["window_height"] = self.window.get_height()
            if hasattr(self, 'stack'):
                # Convert tab name back to index
                tab_names = ["status", "servers", "settings", "ports", "meshnet"]
                active_name = self.stack.get_visible_child_name()
                self.config["active_tab"] = tab_names.index(active_name) if active_name in tab_names else 0

        # Save auto-connect settings
        if hasattr(self, 'settings_pane'):
            autoconnect_config = self.settings_pane.get_autoconnect_config()
            self.config.update(autoconnect_config)

        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")

    def show_toast(self, message: str, is_error: bool = False):
        """Show a toast notification from any pane."""
        if hasattr(self, 'toast_overlay'):
            self.toast_overlay.show_toast(message, is_error)

    def get_is_dark_mode(self) -> bool:
        """Detect if dark theme is active. Tries Adwaita first, then theme name."""
        # Try Adwaita style manager first (most reliable)
        if HAS_ADWAITA:
            try:
                style_manager = Adw.StyleManager.get_default()
                if style_manager:
                    is_dark = style_manager.get_dark()
                    return is_dark
            except Exception as e:
                pass

        # Fallback to checking GTK theme name
        settings = Gtk.Settings.get_default()
        if settings:
            # First try the prefer-dark-theme setting
            prefer_dark = settings.get_property("gtk-application-prefer-dark-theme")
            if prefer_dark is not None:
                return prefer_dark is True

            # Try to detect from theme name
            theme_name = settings.get_property("gtk-theme-name")
            if theme_name:
                # Check if theme name indicates dark mode
                is_dark = "dark" in theme_name.lower()
                return is_dark

        # Default to light mode if detection fails (LMDE uses light themes by default)
        return False

    def on_theme_changed(self, *args):
        """Handle system theme changes at runtime."""
        if not self.window:
            return

        is_dark = self.get_is_dark_mode()

        # Update window CSS classes
        if is_dark:
            self.window.remove_css_class("light-theme")
        else:
            self.window.add_css_class("light-theme")

        # Update headerbar CSS classes and reapply inline CSS
        if hasattr(self, 'header_bar'):
            if is_dark:
                self.header_bar.remove_css_class("light-mode")
                self.header_bar.add_css_class("dark-mode")
            else:
                self.header_bar.remove_css_class("dark-mode")
                self.header_bar.add_css_class("light-mode")

        # Force style context reset on window and recursively on all children
        self._reset_style_recursive(self.window)

    def _reset_style_recursive(self, widget):
        """Recursively reset style on widget and all children to force CSS recalculation."""
        try:
            widget.reset_style()
        except Exception:
            pass

        # Recursively reset style on all child widgets
        child = widget.get_first_child()
        while child:
            self._reset_style_recursive(child)
            child = child.get_next_sibling()

    def build_window(self):
        """Build the main window."""
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("Summit")
        self.window.set_default_size(
            self.config.get("window_width", 900),
            self.config.get("window_height", 650)
        )
        self.window.connect("close-request", self.on_window_close)

        # Apply theme class to window
        is_dark_mode = self.get_is_dark_mode()
        if not is_dark_mode:
            self.window.add_css_class("light-theme")

        # Stack to replace notebook (for page switching)
        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # Add panes to stack BEFORE creating HeaderBar
        # (so panes exist when button activation fires)

        # Tab 1: Status Pane
        self.status_pane = StatusPane(
            self.nord,
            on_status_change=self.on_status_change,
            on_connect_click=self.switch_to_servers_tab
        )
        self.status_pane.set_app_ref(self)
        self.stack.add_named(self.status_pane, "status")

        # Tab 2: Servers Pane
        self.servers_pane = ServersPane(self.nord)
        self.servers_pane.set_app_ref(self)
        self.stack.add_named(self.servers_pane, "servers")

        # Tab 3: Settings Pane
        self.settings_pane = SettingsPane(self.nord)
        self.stack.add_named(self.settings_pane, "settings")

        # Load auto-connect state
        self.settings_pane.autoconnect_switch.set_active(self.config.get("autoconnect_enabled", False))

        # Populate auto-connect countries in background
        def load_autoconnect_data():
            countries = self.nord.get_countries()
            saved_country = self.config.get("autoconnect_country", "")
            saved_city = self.config.get("autoconnect_city", "")

            def populate():
                self.settings_pane.autoconnect_country_combo.remove_all()
                self.settings_pane.autoconnect_country_combo.append("", "Select Country")
                for country in countries:
                    self.settings_pane.autoconnect_country_combo.append(country, country)

                # Restore country selection
                if saved_country:
                    # saved_country is in underscore format (e.g., "United_States")
                    # Combo was populated with countries from get_countries() which also use underscores

                    # Block the signal handler to prevent it from loading cities asynchronously
                    # while we're already loading them synchronously for restore
                    self.settings_pane.autoconnect_country_combo.handler_block(
                        self.settings_pane.autoconnect_country_handler_id
                    )
                    self.settings_pane.autoconnect_country_combo.set_active_id(saved_country)
                    self.settings_pane.autoconnect_country_combo.handler_unblock(
                        self.settings_pane.autoconnect_country_handler_id
                    )

                    # Now load cities for this country
                    cities = self.nord.get_cities(saved_country)
                    self.settings_pane.autoconnect_city_combo.remove_all()
                    self.settings_pane.autoconnect_city_combo.append("", "Select City")
                    for city in cities:
                        self.settings_pane.autoconnect_city_combo.append(city, city)
                    # Restore city selection
                    if saved_city:
                        self.settings_pane.autoconnect_city_combo.set_active_id(saved_city)

            GLib.idle_add(populate)

        import threading
        thread = threading.Thread(target=load_autoconnect_data, daemon=True)
        thread.start()

        # Tab 4: Ports Pane
        self.ports_pane = PortsPane(self.nord)
        self.stack.add_named(self.ports_pane, "ports")

        # Tab 5: Meshnet Pane
        self.meshnet_pane = MeshnetPane(self.nord)
        self.stack.add_named(self.meshnet_pane, "meshnet")

        # HeaderBar with tab buttons - set as window titlebar
        self.header_bar = self.build_headerbar()
        self.window.set_titlebar(self.header_bar)

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Horizontal paned: stack on left, recent connections on right
        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_paned.set_wide_handle(True)
        self.content_paned.set_position(550)

        # Recent Connections Pane (created but only added to paned when on Status tab)
        self.recent_pane = RecentPane(self.nord)
        self.recent_pane.set_app_ref(self)
        self.recent_pane.refresh_favorites_display()

        # Set initial page based on config
        tab_map = ["status", "servers", "settings", "ports", "meshnet"]
        initial_tab = tab_map[self.config.get("active_tab", 0)]
        self.stack.set_visible_child_name(initial_tab)

        self.content_paned.set_start_child(self.stack)

        # Update visibility for the initial page
        self.update_right_pane_visibility()

        self.content_paned.set_vexpand(True)
        self.content_paned.set_hexpand(True)
        main_box.append(self.content_paned)

        # Wrap main content with toast overlay
        self.toast_overlay = ToastOverlay()
        self.toast_overlay.set_child(main_box)
        self.window.set_child(self.toast_overlay)

        # Check login status
        if not self.nord.is_logged_in():
            dialog = Gtk.AlertDialog()
            dialog.set_message("Not Logged In")
            dialog.set_detail_text("Please log in to NordVPN first:\nRun 'nordvpn login' in a terminal")
            dialog.present(self.window)

        # Start polling (initial pane data loads in background after window shows)
        self.start_polling()

    def load_initial_pane_data(self):
        """Load initial data for all panes in background after window shows."""
        # Load settings asynchronously
        if hasattr(self, 'settings_pane'):
            self.settings_pane.load_settings(synchronous=False)
        # Load status for status pane
        if hasattr(self, 'status_pane'):
            self.status_pane.update_status()
        # Meshnet state is loaded in __init__ synchronously
        # Load ports for ports pane
        if hasattr(self, 'ports_pane'):
            self.ports_pane.load_ports()

    def build_headerbar(self) -> Gtk.HeaderBar:
        """Create HeaderBar with tab toggle buttons."""
        header = Gtk.HeaderBar()
        header.add_css_class("headerbar")
        header.set_show_title_buttons(True)
        header.set_title_widget(Gtk.Box())  # suppress centered default title

        # Title label packed to the left
        title_label = Gtk.Label(label="Summit")
        title_label.add_css_class("app-title")
        header.pack_start(title_label)

        # Tab buttons in a box
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tab_box.add_css_class("tab-button-group")

        self.tab_buttons = {}
        tabs = [
            ("Status", "status"),
            ("Servers", "servers"),
            ("Settings", "settings"),
            ("Ports", "ports"),
            ("Meshnet", "meshnet"),
        ]

        for i, (label, name) in enumerate(tabs):
            btn = Gtk.ToggleButton(label=label)
            btn.add_css_class("tab-button")
            if i == 0:
                btn.add_css_class("first-tab")
            if i == len(tabs) - 1:
                btn.add_css_class("last-tab")

            btn.connect("toggled", self.on_tab_button_toggled, name)
            tab_box.append(btn)
            self.tab_buttons[name] = btn

        # Set initial button active
        initial_tab = self.config.get("active_tab", 0)
        initial_name = tabs[initial_tab][1]
        self.tab_buttons[initial_name].set_active(True)

        header.pack_start(tab_box)

        # Hamburger menu button (File, Help)
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Menu")

        # Create menu
        menu = Gio.Menu()

        # File menu
        file_menu = Gio.Menu()
        file_menu.append("_Quit", "app.quit")
        menu.append_submenu("_File", file_menu)

        # Help menu
        help_menu = Gio.Menu()
        help_menu.append("_About", "app.about")
        menu.append_submenu("_Help", help_menu)

        # Register actions
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *args: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", lambda *args: self.show_about())
        self.add_action(about_action)

        # Set menu on button
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        # Detect theme and apply CSS class + programmatic styling
        is_dark_mode = self.get_is_dark_mode()

        if is_dark_mode:
            header.add_css_class("dark-mode")
        else:
            header.add_css_class("light-mode")

        # Debug: print all CSS classes on headerbar
        classes = header.get_css_classes()

        # Try to force style update
        header.queue_draw()

        return header

    def on_tab_button_toggled(self, button: Gtk.ToggleButton, tab_name: str):
        """Handle tab button toggle."""
        # Prevent infinite recursion when updating tab buttons
        if self._updating_tabs:
            return

        if button.get_active():
            self._updating_tabs = True
            try:
                # Deactivate all other buttons
                for name, btn in self.tab_buttons.items():
                    if name != tab_name:
                        btn.set_active(False)

                # Switch to the new tab
                self.stack.set_visible_child_name(tab_name)
                self.update_right_pane_visibility()
            finally:
                self._updating_tabs = False
        else:
            # Prevent deactivating the active button
            self._updating_tabs = True
            try:
                button.set_active(True)
            finally:
                self._updating_tabs = False

    def build_menubar(self) -> Gtk.PopoverMenuBar:
        """Create application menu."""
        menu = Gio.Menu()

        # File menu
        file_menu = Gio.Menu()
        file_menu.append("_Quit", "app.quit")
        menu.append_submenu("_File", file_menu)

        # Help menu
        help_menu = Gio.Menu()
        help_menu.append("_About", "app.about")
        menu.append_submenu("_Help", help_menu)

        # Register actions
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *args: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", lambda *args: self.show_about())
        self.add_action(about_action)

        return Gtk.PopoverMenuBar.new_from_model(menu)

    def show_about(self):
        """Show about dialog."""
        about = Gtk.AboutDialog(transient_for=self.window)
        about.set_program_name("Summit")
        about.set_version("1.0.0")
        about.set_comments(
            "An unofficial GTK4 wrapper for the NordVPN CLI.\n\n"
            "⚠️ DISCLAIMER: This is NOT affiliated with, authorized by, or endorsed by NordVPN. "
            "This is a community-developed third-party tool. "
            "See DISCLAIMER.md for full legal details."
        )
        about.set_authors(["albert-wolf"])
        about.set_logo_icon_name("network-vpn")
        about.set_website_label("GitHub Repository")
        about.set_website("https://github.com/albert-wolf/summit")
        about.present()

    def restore_window_state(self):
        """Restore window state after mapping."""
        return False

    def reapply_css(self):
        """Reapply CSS after window is shown to override theme defaults."""
        self.load_css()
        return False

    def start_polling(self):
        """Start status polling every 2 seconds."""
        interval = self.config.get("poll_interval_ms", 2000)
        self.poll_timer = GLib.timeout_add(interval, self.poll_status)

    def poll_status(self):
        """Poll VPN status (runs in main thread)."""
        if hasattr(self, 'status_pane'):
            self.status_pane.update_status()
        if hasattr(self, 'recent_pane'):
            self.recent_pane.update_status()
        return True  # Keep polling

    def on_status_change(self, status):
        """Callback when status changes (for future use)."""
        pass

    def switch_to_servers_tab(self):
        """Switch to servers tab."""
        self.tab_buttons["servers"].set_active(True)

    def on_notebook_page_changed(self, notebook, page, page_num):
        """Handle tab changes - show/hide right pane."""
        self.update_right_pane_visibility(page_num)

    def update_right_pane_visibility(self, page_num=None):
        """Show right pane only on Status tab."""
        if not hasattr(self, 'recent_pane') or not hasattr(self, 'content_paned') or not hasattr(self, 'stack'):
            return

        # Get current tab from stack
        active_tab = self.stack.get_visible_child_name()

        # Only show on Status tab
        if active_tab == "status":
            # Add recent pane as right child if not already there
            if self.content_paned.get_end_child() != self.recent_pane:
                self.content_paned.set_end_child(self.recent_pane)
        else:
            # Remove recent pane from right side on all other tabs
            if self.content_paned.get_end_child() == self.recent_pane:
                self.content_paned.set_end_child(None)

    def on_window_close(self, window):
        """Handle window close."""
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
