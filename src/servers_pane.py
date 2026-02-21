import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from summit_manager import NordManager


class ServersPane(Gtk.Box):
    """Tab 2: Country and City Selection"""

    def __init__(self, nord: NordManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.nord = nord
        self.selected_country = None
        self.selected_city = None
        self.search_text = ""
        self.all_countries = []
        self.all_cities = []
        self.app_ref = None

        # Search bar
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_box.set_margin_bottom(8)

        search_label = Gtk.Label(label="Search:")
        search_label.set_size_request(60, -1)
        search_box.append(search_label)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Filter countries & cities...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_box.append(self.search_entry)

        self.append(search_box)

        # Paned layout: countries on left, cities on right
        paned_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        paned_container.add_css_class("pane-box")
        paned_container.set_margin_top(8)
        paned_container.set_margin_bottom(8)
        paned_container.set_margin_start(8)
        paned_container.set_margin_end(8)

        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.paned.set_wide_handle(True)
        self.paned.set_position(450)
        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        # Left: Countries list
        countries_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        countries_box.set_hexpand(True)
        countries_box.set_vexpand(True)
        countries_label = Gtk.Label(label="Countries")
        countries_label.add_css_class("heading")
        countries_box.append(countries_label)

        self.countries_listbox = Gtk.ListBox()
        self.countries_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.countries_listbox.set_hexpand(True)
        self.countries_listbox.set_vexpand(True)
        self.countries_listbox.connect("row-selected", self.on_country_selected)

        countries_scrolled = Gtk.ScrolledWindow()
        countries_scrolled.set_child(self.countries_listbox)
        countries_scrolled.set_vexpand(True)
        countries_scrolled.set_hexpand(True)
        countries_box.append(countries_scrolled)

        self.paned.set_start_child(countries_box)

        # Right: Cities list
        cities_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cities_box.set_hexpand(True)
        cities_box.set_vexpand(True)
        cities_label = Gtk.Label(label="Cities")
        cities_label.add_css_class("heading")
        cities_box.append(cities_label)

        self.cities_listbox = Gtk.ListBox()
        self.cities_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.cities_listbox.set_hexpand(True)
        self.cities_listbox.set_vexpand(True)
        self.cities_listbox.connect("row-selected", self.on_city_selected)

        cities_scrolled = Gtk.ScrolledWindow()
        cities_scrolled.set_child(self.cities_listbox)
        cities_scrolled.set_vexpand(True)
        cities_scrolled.set_hexpand(True)
        cities_box.append(cities_scrolled)

        # Favorite button
        fav_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fav_button_box.set_margin_top(8)

        self.favorite_button = Gtk.Button(label="★ Add to Favorites")
        self.favorite_button.set_sensitive(False)
        self.favorite_button.connect("clicked", self.on_add_favorite_clicked)
        fav_button_box.append(self.favorite_button)

        cities_box.append(fav_button_box)

        self.paned.set_end_child(cities_box)
        self.paned.set_vexpand(True)
        self.paned.set_hexpand(True)
        paned_container.append(self.paned)
        self.append(paned_container)

        # Connect button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_margin_top(12)

        self.connect_btn = Gtk.Button(label="Connect to Selected")
        self.connect_btn.connect("clicked", self.on_connect_clicked)
        self.connect_btn.set_sensitive(False)
        button_box.append(self.connect_btn)

        self.append(button_box)

        # Load countries in background
        self.load_countries()

    def set_app_ref(self, app):
        """Set reference to app for showing toasts."""
        self.app_ref = app

    def on_add_favorite_clicked(self, button):
        """Add current country/city selection to favorites."""
        if not self.selected_country or not self.selected_city:
            if self.app_ref:
                self.app_ref.show_toast("Please select both country and city", is_error=True)
            return

        # Check if already favorite
        favorites = self.app_ref.config.get("favorites", [])
        new_fav = {"country": self.selected_country, "city": self.selected_city}

        if new_fav in favorites:
            if self.app_ref:
                self.app_ref.show_toast("Already in favorites", is_error=True)
            return

        # Add to config
        favorites.append(new_fav)
        self.app_ref.config["favorites"] = favorites
        self.app_ref.save_config()

        if self.app_ref:
            self.app_ref.show_toast(f"Added to favorites: {self.selected_city}")

        # Notify sidebar to refresh
        if hasattr(self.app_ref, 'recent_pane'):
            self.app_ref.recent_pane.refresh_favorites_display()

    def load_countries(self):
        """Load countries list in background thread."""
        def worker():
            countries = self.nord.get_countries()
            GLib.idle_add(self.on_countries_loaded, countries)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_search_changed(self, search_entry):
        """Filter countries and cities by search text."""
        self.search_text = search_entry.get_text().lower()
        self.refresh_countries_display()
        self.refresh_cities_display()

    def refresh_countries_display(self):
        """Refresh country list based on search."""
        self.countries_listbox.remove_all()
        for country in self.all_countries:
            if self.search_text in country.lower():
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=country, xalign=0)
                label.set_hexpand(True)
                row.set_child(label)
                self.countries_listbox.append(row)

    def refresh_cities_display(self):
        """Refresh city list based on search."""
        self.cities_listbox.remove_all()

        # When searching, show all matching cities; when not searching, show cities from selected country
        if self.search_text:
            # Search mode: show matching cities from all countries
            for city in self.all_cities:
                if self.search_text in city.lower():
                    row = Gtk.ListBoxRow()
                    label = Gtk.Label(label=city, xalign=0)
                    label.set_hexpand(True)
                    row.set_child(label)
                    self.cities_listbox.append(row)
        elif self.selected_country:
            # Normal mode: show cities from selected country
            for city in self.all_cities:
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=city, xalign=0)
                label.set_hexpand(True)
                row.set_child(label)
                self.cities_listbox.append(row)

    def on_countries_loaded(self, countries):
        """Populate countries listbox."""
        self.all_countries = countries
        self.refresh_countries_display()
        return False

    def on_country_selected(self, listbox, row):
        """Load cities when country is selected."""
        if row:
            country_label = row.get_child()
            self.selected_country = country_label.get_label()
            self.selected_city = None
            self.cities_listbox.remove_all()
            self.load_cities(self.selected_country)
            self.connect_btn.set_sensitive(True)
        else:
            self.selected_country = None
            self.selected_city = None
            self.cities_listbox.remove_all()
            self.connect_btn.set_sensitive(False)

    def load_cities(self, country):
        """Load cities for selected country."""
        def worker():
            cities = self.nord.get_cities(country)
            GLib.idle_add(self.on_cities_loaded, cities)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_cities_loaded(self, cities):
        """Populate cities listbox."""
        self.all_cities = cities
        self.refresh_cities_display()
        return False

    def on_city_selected(self, listbox, row):
        """Update selected city."""
        if row:
            city_label = row.get_child()
            self.selected_city = city_label.get_label()
            self.favorite_button.set_sensitive(True)
        else:
            self.selected_city = None
            self.favorite_button.set_sensitive(False)

    def _do_connect(self, country, city=None):
        """Shared connection logic for button and double-click handlers.

        Args:
            country: Country to connect to (e.g., "United_States")
            city: Optional city to connect to (e.g., "New_York")
        """
        if not country:
            return

        self.connect_btn.set_label("Connecting...")

        def worker():
            success, message = self.nord.connect(country, city)
            GLib.idle_add(self.on_connect_done, success, message, self.connect_btn)

        import threading
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_connect_clicked(self, button):
        """Connect to selected country/city."""
        self._do_connect(self.selected_country, self.selected_city)

    def on_connect_done(self, success, message, button):
        """Handle connection completion."""
        button.set_sensitive(True)
        button.set_label("Connect to Selected")
        return False

