import gi
import logging
import threading
from datetime import datetime

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from summit_manager import SummitManager

logger = logging.getLogger(__name__)


class StatusPane(Gtk.Box):
    """Tab 1: VPN Status, Telemetry Dashboard, and Integrated Lists."""

    __gtype_name__ = "StatusPane"

    def __init__(self, manager: SummitManager, on_status_change=None, on_connect_click=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=32)
        self.set_margin_top(32)
        self.set_margin_bottom(32)
        self.set_margin_start(32)
        self.set_margin_end(32)

        self.manager = manager
        self.on_status_change = on_status_change
        self.on_connect_click = on_connect_click
        self.app_ref = None
        self.current_status = None
        self.last_server = None
        self.connection_history = []
        self.current_connection = None

        # Build UI Components
        self._build_hero_section()
        self._build_telemetry_dashboard()
        self._build_list_section()

        # Initial Refresh
        GLib.idle_add(self.refresh_lists)

    def set_app_ref(self, app):
        """Set reference to app for config and toasts."""
        self.app_ref = app

    def _build_hero_section(self):
        """Build the top hero section with status icons and connect button."""
        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        hero_box.set_halign(Gtk.Align.CENTER)

        # Status indicator stack (Shows only active state)
        self.hero_stack = Gtk.Stack()
        self.hero_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.hero_stack.set_halign(Gtk.Align.CENTER)

        # 1. Unsecured State Page
        unsecured_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        unsecured_hbox.set_halign(Gtk.Align.CENTER)
        unsecured_hbox.set_valign(Gtk.Align.CENTER)

        self.unsecured_circle = Gtk.Box()
        self.unsecured_circle.add_css_class("hero-circle")
        self.unsecured_circle.add_css_class("unsecured")
        self.unsecured_circle.set_halign(Gtk.Align.CENTER)
        self.unsecured_circle.set_valign(Gtk.Align.CENTER)
        unsecured_hbox.append(self.unsecured_circle)

        self.unsecured_label = Gtk.Label(label="UNSECURED")
        self.unsecured_label.add_css_class("hero-label")
        unsecured_hbox.append(self.unsecured_label)
        self.hero_stack.add_named(unsecured_hbox, "unsecured")

        # 2. Connected State Page
        connected_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        connected_hbox.set_halign(Gtk.Align.CENTER)
        connected_hbox.set_valign(Gtk.Align.CENTER)

        # Overlay to place pulsing ring BEHIND the circle
        connected_overlay = Gtk.Overlay()
        connected_overlay.set_halign(Gtk.Align.CENTER)
        connected_overlay.set_valign(Gtk.Align.CENTER)

        self.pulsing_ring = Gtk.Box()
        self.pulsing_ring.add_css_class("pulsing-ring")
        self.pulsing_ring.set_halign(Gtk.Align.CENTER)
        self.pulsing_ring.set_valign(Gtk.Align.CENTER)
        connected_overlay.set_child(self.pulsing_ring)

        self.connected_circle = Gtk.Box()
        self.connected_circle.add_css_class("hero-circle")
        self.connected_circle.add_css_class("connected")
        self.connected_circle.set_halign(Gtk.Align.CENTER)
        self.connected_circle.set_valign(Gtk.Align.CENTER)
        connected_overlay.add_overlay(self.connected_circle)

        connected_hbox.append(connected_overlay)

        self.connected_label = Gtk.Label(label="CONNECTED")
        self.connected_label.add_css_class("hero-label")
        connected_hbox.append(self.connected_label)
        self.hero_stack.add_named(connected_hbox, "connected")

        # 3. Connecting State Page
        connecting_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        connecting_hbox.set_halign(Gtk.Align.CENTER)
        connecting_hbox.set_valign(Gtk.Align.CENTER)

        self.connecting_spinner = Gtk.Spinner()
        self.connecting_spinner.set_size_request(70, 70)
        connecting_hbox.append(self.connecting_spinner)

        self.connecting_label = Gtk.Label(label="CONNECTING...")
        self.connecting_label.add_css_class("hero-label")
        connecting_hbox.append(self.connecting_label)
        self.hero_stack.add_named(connecting_hbox, "connecting")

        hero_box.append(self.hero_stack)

        # Button Row
        btn_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_hbox.set_halign(Gtk.Align.CENTER)

        # Linked Control Pill (Fusion of Connect and Reconnect)
        self.control_pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.control_pill.add_css_class("linked")

        self.connect_btn = Gtk.Button(label="Connect")
        self.connect_btn.add_css_class("btn-connect")
        self.connect_btn.set_margin_start(0)
        self.connect_btn.set_margin_end(0)
        self.connect_btn.connect("clicked", self.on_connect_clicked)
        self.control_pill.append(self.connect_btn)

        self.reconnect_btn = Gtk.Button()
        self.reconnect_btn.set_icon_name("view-refresh-symbolic")
        self.reconnect_btn.add_css_class("btn-refresh")
        self.reconnect_btn.set_margin_start(0)
        self.reconnect_btn.set_margin_end(0)
        self.reconnect_btn.connect("clicked", self.on_reconnect_clicked)
        self.control_pill.append(self.reconnect_btn)

        btn_hbox.append(self.control_pill)
        hero_box.append(btn_hbox)
        self.append(hero_box)

    def _build_telemetry_dashboard(self):
        """Build the two-column telemetry cards."""
        dashboard_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        dashboard_hbox.set_halign(Gtk.Align.CENTER)

        # Left Column: Network State
        self.network_grid = self._create_telemetry_card(
            "Network State",
            [("Public IP", "ip_val"), ("Protocol (UDP/TCP)", "proto_val"), ("Tech", "tech_val")],
        )
        dashboard_hbox.append(self.network_grid)

        # Right Column: Session State
        self.session_grid = self._create_telemetry_card(
            "Session State",
            [
                ("Server ID", "server_val"),
                ("Uptime", "uptime_val"),
                ("Transfer (Up/Down)", "transfer_val"),
            ],
        )
        dashboard_hbox.append(self.session_grid)

        self.append(dashboard_hbox)

    def _create_telemetry_card(self, title, rows):
        """Helper to create a styled nested telemetry card."""
        # Outer Card: Encloses both Title and the Inner Frame
        outer_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer_card.add_css_class("telemetry-card-outer")

        label_title = Gtk.Label(label=title)
        label_title.add_css_class("heading")
        label_title.set_xalign(0)
        label_title.set_margin_start(4)
        outer_card.append(label_title)

        # Inner Frame: Encloses only the data grid
        inner_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        inner_frame.add_css_class("telemetry-card-inner")

        grid = Gtk.Grid(row_spacing=12, column_spacing=48)
        grid.set_margin_top(4)
        grid.set_margin_bottom(4)
        setattr(self, f"{title.lower().replace(' ', '_')}_grid", grid)

        for i, (name, attr_name) in enumerate(rows):
            name_label = Gtk.Label(label=name)
            name_label.set_halign(Gtk.Align.START)
            name_label.set_xalign(0)
            name_label.set_opacity(0.8)
            grid.attach(name_label, 0, i, 1, 1)

            val_label = Gtk.Label(label="—")
            val_label.set_halign(Gtk.Align.END)
            val_label.set_hexpand(True)
            val_label.set_xalign(1)
            val_label.set_markup("<b>—</b>")
            grid.attach(val_label, 1, i, 1, 1)
            setattr(self, attr_name, val_label)

        inner_frame.append(grid)
        outer_card.append(inner_frame)
        return outer_card

    def _build_list_section(self):
        """Build the segmented control and stack for Favorites/Recent."""
        list_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        list_vbox.set_vexpand(True)

        # Segmented Control
        segment_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        segment_hbox.set_halign(Gtk.Align.CENTER)
        segment_hbox.set_homogeneous(True)  # Force 50/50 split
        segment_hbox.add_css_class("linked")

        self.fav_seg_btn = Gtk.ToggleButton(label="Favorites")
        self.fav_seg_btn.add_css_class("segment-button")
        self.fav_seg_btn.set_active(True)

        self.recent_seg_btn = Gtk.ToggleButton(label="Recent")
        self.recent_seg_btn.add_css_class("segment-button")
        self.recent_seg_btn.set_group(self.fav_seg_btn)

        segment_hbox.append(self.fav_seg_btn)
        segment_hbox.append(self.recent_seg_btn)
        list_vbox.append(segment_hbox)

        # Stack
        self.list_stack = Gtk.Stack()
        self.list_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # Favorites List
        self.fav_listbox = Gtk.ListBox()
        self.fav_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        fav_scroll = Gtk.ScrolledWindow()
        fav_scroll.set_child(self.fav_listbox)
        fav_scroll.set_vexpand(True)
        self.list_stack.add_titled(fav_scroll, "favorites", "Favorites")

        # Recent List
        self.recent_listbox = Gtk.ListBox()
        self.recent_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        recent_scroll = Gtk.ScrolledWindow()
        recent_scroll.set_child(self.recent_listbox)
        recent_scroll.set_vexpand(True)
        self.list_stack.add_titled(recent_scroll, "recent", "Recent")

        list_vbox.append(self.list_stack)
        self.append(list_vbox)

        # Connect signals
        self.fav_seg_btn.connect(
            "toggled",
            lambda b: (
                self.list_stack.set_visible_child_name("favorites") if b.get_active() else None
            ),
        )
        self.recent_seg_btn.connect(
            "toggled",
            lambda b: self.list_stack.set_visible_child_name("recent") if b.get_active() else None,
        )

    def apply_status(self, status):
        """Update UI based on NordVPN status."""
        if not status:
            self._update_ui_disconnected()
            return False

        state = status.get("Status", "Disconnected").lower()
        self.current_status = status

        if state == "connected":
            self._update_ui_connected(status)

            # History tracking logic
            server = status.get("Server", "Unknown")
            city = status.get("City", "Unknown")
            country = status.get("Country", "Unknown")

            self.current_connection = {
                "country": country.replace(" ", "_"),
                "city": city.replace(" ", "_"),
            }

            if server != self.last_server:
                self.add_history_entry(
                    f"{city} - {country}",
                    self.current_connection["country"],
                    self.current_connection["city"],
                    server,
                )
                self.last_server = server
        elif state == "connecting":
            self._update_ui_connecting()
        else:
            self._update_ui_disconnected()
            self.last_server = None
            self.current_connection = None

        # Refresh lists to update highlights
        self.refresh_lists()

        if self.on_status_change:
            self.on_status_change(status)
        return False

    def _update_ui_disconnected(self):
        """Set UI to Disconnected state."""
        self.connecting_spinner.stop()
        self.hero_stack.set_visible_child_name("unsecured")

        self.connect_btn.set_label("Connect")
        self.connect_btn.set_sensitive(True)
        self.connect_btn.remove_css_class("destructive-action")
        self.connect_btn.add_css_class("btn-connect")

        # Clear telemetry
        self.ip_val.set_markup("<b>—</b>")
        self.proto_val.set_markup("<b>—</b>")
        self.tech_val.set_markup("<b>—</b>")
        self.server_val.set_markup("<b>—</b>")
        self.uptime_val.set_markup("<b>—</b>")
        self.transfer_val.set_markup("<b>—</b>")

    def _update_ui_connecting(self):
        """Set UI to Connecting state."""
        self.hero_stack.set_visible_child_name("connecting")
        self.connecting_spinner.start()

        self.connect_btn.set_label("Connecting...")
        self.connect_btn.set_sensitive(False)

    def _update_ui_connected(self, status):
        """Set UI to Connected state."""
        self.connecting_spinner.stop()
        self.hero_stack.set_visible_child_name("connected")

        city = status.get("City", "VPN")
        self.connected_label.set_markup(f"<b>CONNECTED TO {city.upper()}</b>")

        self.connect_btn.set_label("Disconnect")
        self.connect_btn.set_sensitive(True)
        # Clear all possible action classes first
        self.connect_btn.remove_css_class("btn-connect")
        self.connect_btn.remove_css_class("suggested-action")
        self.connect_btn.add_css_class("destructive-action")

        # Update telemetry
        self.ip_val.set_markup(f"<b>{status.get('IP', '—')}</b>")
        self.proto_val.set_markup(f"<b>{status.get('Current protocol', '—')}</b>")
        self.tech_val.set_markup(f"<b>{status.get('Current technology', '—')}</b>")
        self.server_val.set_markup(f"<b>{status.get('Server', '—')}</b>")
        self.uptime_val.set_markup(f"<b>{status.get('Uptime', '—')}</b>")
        self.transfer_val.set_markup(f"<b>{status.get('Transfer', '—')}</b>")

    def on_connect_clicked(self, button):
        """Handle main button click."""
        if button.get_label() == "Connect":
            if self.on_connect_click:
                self.on_connect_click()
        else:
            self.on_disconnect_clicked()

    def on_disconnect_clicked(self):
        """Execute disconnect."""
        self.connect_btn.set_sensitive(False)
        self.connect_btn.set_label("Disconnecting...")

        def worker():
            success, message = self.manager.disconnect()
            GLib.idle_add(self.on_action_done, success, message, "Connect")

        threading.Thread(target=worker, daemon=True).start()

    def on_reconnect_clicked(self, button):
        """Execute reconnect."""
        button.set_sensitive(False)

        def worker():
            success, message = self.manager.reconnect()
            GLib.idle_add(self.on_action_done, success, message)

        threading.Thread(target=worker, daemon=True).start()

    def on_action_done(self, success, message, next_label=None):
        """Handle completion of connect/disconnect/reconnect."""
        self.connect_btn.set_sensitive(True)
        self.reconnect_btn.set_sensitive(True)
        if next_label:
            self.connect_btn.set_label(next_label)

        if not success and self.app_ref:
            self.app_ref.show_toast(message, is_error=True)

        # Trigger immediate status poll
        if self.app_ref:
            self.app_ref.poll_status()
        return False

    def add_history_entry(self, text, country, city, server):
        """Add to connection history (migrated from RecentPane)."""
        entry = {
            "text": text,
            "country": country,
            "city": city,
            "server": server,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        self.connection_history.insert(0, entry)
        if len(self.connection_history) > 10:
            self.connection_history = self.connection_history[:10]
        self.refresh_lists()

    def refresh_lists(self):
        """Refresh Favorites and Recent listboxes."""
        self._refresh_favorites()
        self._refresh_recent()

    def _refresh_favorites(self):
        self.fav_listbox.remove_all()
        if not self.app_ref:
            return

        favorites = self.app_ref.config.get("favorites", [])
        if not favorites:
            self.fav_listbox.append(self._create_empty_row("No favorites added yet."))
            return

        for fav in favorites:
            self.fav_listbox.append(self._create_card_row(fav, is_favorite=True))

    def _refresh_recent(self):
        self.recent_listbox.remove_all()
        if not self.connection_history:
            self.recent_listbox.append(self._create_empty_row("No recent connections."))
            return

        for entry in self.connection_history:
            self.recent_listbox.append(self._create_card_row(entry, is_favorite=False))

    def _create_empty_row(self, text):
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=text)
        label.set_margin_top(20)
        label.set_opacity(0.5)
        row.set_child(label)
        return row

    def _create_card_row(self, data, is_favorite):
        """Create a styled card for the lists."""
        row = Gtk.ListBoxRow()
        row.add_css_class("card-row")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)
        hbox.set_margin_start(12)
        hbox.set_margin_end(12)

        # Text labels
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_hexpand(True)

        name = data.get("text") or f"{data.get('city')} - {data.get('country')}"
        name_label = Gtk.Label(label=name)
        name_label.set_xalign(0)
        name_label.set_markup(f"<b>{name}</b>")
        vbox.append(name_label)

        if not is_favorite:
            time_label = Gtk.Label(label=data.get("time"))
            time_label.set_xalign(0)
            time_label.set_opacity(0.6)
            vbox.append(time_label)

        hbox.append(vbox)

        # Action Buttons
        actions_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        connect_btn = Gtk.Button()
        connect_btn.set_icon_name("network-vpn-symbolic")
        connect_btn.add_css_class("flat")
        connect_btn.set_tooltip_text("Connect")
        connect_btn.connect("clicked", lambda *_: self._on_list_connect(data))
        actions_hbox.append(connect_btn)

        expand_btn = Gtk.Button()
        expand_btn.set_icon_name("go-next-symbolic")
        expand_btn.add_css_class("flat")
        expand_btn.set_tooltip_text("Details")
        actions_hbox.append(expand_btn)

        if is_favorite:
            remove_btn = Gtk.Button()
            remove_btn.set_icon_name("window-close-symbolic")
            remove_btn.add_css_class("flat")
            remove_btn.connect("clicked", lambda *_: self._on_remove_favorite(data))
            actions_hbox.append(remove_btn)

        hbox.append(actions_hbox)
        row.set_child(hbox)
        return row

    def _on_list_connect(self, data):
        """Handle connect click from list card."""
        country = data.get("country")
        city = data.get("city")

        self.connect_btn.set_sensitive(False)
        self.connect_btn.set_label("Connecting...")

        def worker():
            success, message = self.manager.connect(country, city)
            GLib.idle_add(self.on_action_done, success, message)

        threading.Thread(target=worker, daemon=True).start()

    def _on_remove_favorite(self, data):
        """Remove from favorites."""
        if not self.app_ref:
            return
        favorites = self.app_ref.config.get("favorites", [])
        if data in favorites:
            favorites.remove(data)
            self.app_ref.config["favorites"] = favorites
            self.app_ref.save_config()
            self.refresh_lists()
            self.app_ref.show_toast("Removed from favorites")
