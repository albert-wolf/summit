import gi
import logging

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from summit_manager import SummitManager

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/summit/ui/servers_pane.ui")
class ServersPane(Gtk.Box):
    """Tab 2: Country and City Selection"""

    __gtype_name__ = "ServersPane"

    search_entry = Gtk.Template.Child()
    country_list = Gtk.Template.Child()
    city_list = Gtk.Template.Child()
    favorite_btn = Gtk.Template.Child()
    connect_btn = Gtk.Template.Child()
    country_scrolled = Gtk.Template.Child()

    def __init__(self, manager: SummitManager):
        super().__init__()
        self.init_template()

        self.manager = manager
        self.selected_country = None
        self.selected_city = None
        self.search_text = ""
        self.all_countries = []
        self.all_cities = []
        self.city_to_countries = {}  # Maps city name to list of countries
        self.app_ref = None

        # Connect country_list manually to get the handler ID
        self._country_selected_handler_id = self.country_list.connect(
            "row-selected", self.on_country_selected
        )

        # Try to load cached city_to_countries for instant startup
        cached_mapping = self.load_city_to_countries_from_cache()
        if cached_mapping:
            self.city_to_countries = cached_mapping
            # Also pre-populate all_cities from cache keys so search works immediately
            self.all_cities = sorted(cached_mapping.keys())
        # Then load fresh cities in background (will update cache if changed)

        # Load countries and all cities in background
        self.load_countries()
        self.load_all_cities()

    def set_app_ref(self, app):
        """Set reference to app for showing toasts."""
        self.app_ref = app

    @Gtk.Template.Callback()
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
        if hasattr(self.app_ref, "recent_pane"):
            self.app_ref.recent_pane.refresh_favorites_display()

    def load_countries(self):
        """Load countries list in background thread."""

        def worker():
            countries = self.manager.get_countries()
            GLib.idle_add(self.on_countries_loaded, countries)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def load_all_cities(self):
        """Load all cities from all countries in parallel for searching."""

        def worker():
            try:
                import time

                # Wait a bit to let UI settle after window appears
                time.sleep(0.5)

                countries = self.manager.get_countries()
                all_cities = set()
                city_to_countries = {}  # Build mapping: city -> list of countries

                # Load cities in parallel (max 4 concurrent requests to avoid daemon socket saturation)
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {
                        executor.submit(self.manager.get_cities, country): country
                        for country in countries
                    }
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            country = futures[future]
                            cities = future.result()
                            all_cities.update(cities)

                            # Build city_to_countries mapping
                            for city in cities:
                                if city not in city_to_countries:
                                    city_to_countries[city] = []
                                city_to_countries[city].append(country)
                        except Exception as e:
                            logger.warning(f"Error loading cities for {futures[future]}: {e}")

                # Always update all_cities and mapping from fresh fetch
                self.all_cities = sorted(list(all_cities))

                if city_to_countries != self.city_to_countries:
                    self.city_to_countries = city_to_countries
                    # Save directly on background thread (no GTK widgets touched)
                    self.save_city_to_countries_to_cache(city_to_countries)
                    logger.info("City cache updated with fresh data")
                else:
                    logger.info("City cache is up-to-date")

                # Refresh search display on main thread once cities are loaded
                if self.search_text:
                    GLib.idle_add(self.refresh_countries_display)
                    GLib.idle_add(self.refresh_cities_display)
                    GLib.idle_add(
                        lambda: self.select_countries_by_name(
                            self.get_countries_for_search_results()
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to load all cities: {e}")

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    @Gtk.Template.Callback()
    def on_search_changed(self, search_entry):
        """Filter countries and cities by search text."""
        self.search_text = search_entry.get_text().lower()
        self.refresh_cities_display()

        # Auto-highlight countries that contain matching cities (don't rebuild the list)
        countries_to_select = self.get_countries_for_search_results()
        self.select_countries_by_name(countries_to_select)

    def refresh_countries_display(self):
        """Always show all countries. Search does not filter this list."""
        self.country_list.remove_all()
        for country in self.all_countries:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=country, xalign=0)
            label.set_hexpand(True)
            row.set_child(label)
            self.country_list.append(row)

    def refresh_cities_display(self):
        """Refresh city list based on search."""
        self.city_list.remove_all()

        # When searching, show all matching cities; when not searching, show cities from selected country
        if self.search_text:
            # Search mode: show matching cities from all countries
            for city in self.all_cities:
                if self.search_text in city.lower():
                    row = Gtk.ListBoxRow()
                    label = Gtk.Label(label=city, xalign=0)
                    label.set_hexpand(True)
                    row.set_child(label)
                    self.city_list.append(row)
        elif self.selected_country:
            # Normal mode: show cities from selected country
            for city in self.all_cities:
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=city, xalign=0)
                label.set_hexpand(True)
                row.set_child(label)
                self.city_list.append(row)

    def select_countries_by_name(self, country_names):
        """Select multiple countries in the listbox without triggering row-selected signal.

        Args:
            country_names: List of country names to select
        """
        if not country_names:
            self.country_list.unselect_all()
            return

        country_names_lower = [name.lower() for name in country_names]

        # Block the row-selected signal to prevent on_country_selected from clearing search
        self.country_list.handler_block(self._country_selected_handler_id)

        first_match_row = None
        try:
            row_index = 0
            while True:
                row = self.country_list.get_row_at_index(row_index)
                if not row:
                    break

                label = row.get_child()
                if isinstance(label, Gtk.Label):
                    country = label.get_label().lower()
                    if country in country_names_lower:
                        self.country_list.select_row(row)
                        if first_match_row is None:
                            first_match_row = row
                row_index += 1
        finally:
            self.country_list.handler_unblock(self._country_selected_handler_id)

        # Scroll to first matched country so user can see the highlight (without stealing focus)
        if first_match_row:

            def scroll_to_row():
                alloc = first_match_row.get_allocation()
                vadj = self.country_scrolled.get_vadjustment()
                if alloc.height > 0:
                    vadj.set_value(max(0, alloc.y - alloc.height))
                return False

            GLib.idle_add(scroll_to_row)

    def get_countries_for_search_results(self):
        """Get list of countries that should be selected based on current search.

        Returns:
            List of country names to auto-select
        """
        if not self.search_text:
            return []

        # Step 1: Find matching cities
        matching_cities = [city for city in self.all_cities if self.search_text in city.lower()]

        if matching_cities:
            # Step 2: Extract countries for matching cities
            countries = set()
            for city in matching_cities:
                if city in self.city_to_countries:
                    countries.update(self.city_to_countries[city])
            return sorted(list(countries))
        else:
            # Step 3: If no cities match, find matching countries
            matching_countries = [
                country for country in self.all_countries if self.search_text in country.lower()
            ]
            return matching_countries

    def on_countries_loaded(self, countries):
        """Populate countries listbox."""
        self.all_countries = countries
        self.refresh_countries_display()
        return False

    def on_country_selected(self, listbox, row):
        """Load cities when country is selected."""
        if row:
            # Clear search when country is explicitly selected
            self.search_text = ""
            self.search_entry.set_text("")

            country_label = row.get_child()
            self.selected_country = country_label.get_label()
            self.selected_city = None
            self.city_list.remove_all()
            self.load_cities(self.selected_country)
            self.connect_btn.set_sensitive(True)
        else:
            self.selected_country = None
            self.selected_city = None
            self.city_list.remove_all()
            self.connect_btn.set_sensitive(False)

    def load_cities(self, country):
        """Load cities for selected country."""

        def worker():
            cities = self.manager.get_cities(country)
            GLib.idle_add(self.on_cities_loaded, cities)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_cities_loaded(self, cities):
        """Populate cities listbox."""
        self.all_cities = cities
        self.refresh_cities_display()
        return False

    def load_city_to_countries_from_cache(self):
        """Load city_to_countries mapping from cache file."""
        import json
        import os

        cache_path = os.path.expanduser("~/.config/summit/server_cache.json")

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                if data.get("version") == 1:
                    return data.get("city_to_countries", {})
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

        return None

    def save_city_to_countries_to_cache(self, city_to_countries):
        """Save city_to_countries mapping to cache file."""
        import json
        import os
        from datetime import datetime

        cache_path = os.path.expanduser("~/.config/summit/server_cache.json")
        cache_dir = os.path.dirname(cache_path)

        # Ensure directory exists
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

        cache_data = {
            "version": 1,
            "city_to_countries": city_to_countries,
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        try:
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    @Gtk.Template.Callback()
    def on_city_selected(self, listbox, row):
        """Update selected city. In search mode, also derive the country from the mapping."""
        if row:
            city_label = row.get_child()
            self.selected_city = city_label.get_label()
            self.favorite_btn.set_sensitive(True)
            self.connect_btn.set_sensitive(True)

            # In search mode, selected_country may not be set — derive it from the mapping
            if self.search_text and not self.selected_country:
                countries = self.city_to_countries.get(self.selected_city, [])
                if len(countries) == 1:
                    self.selected_country = countries[0]
        else:
            self.selected_city = None
            self.favorite_btn.set_sensitive(False)

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
            success, message = self.manager.connect(country, city)
            GLib.idle_add(self.on_connect_done, success, message, self.connect_btn)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    @Gtk.Template.Callback()
    def on_connect_clicked(self, button):
        """Connect to selected country/city."""
        self._do_connect(self.selected_country, self.selected_city)

    def on_connect_done(self, success, message, button):
        """Handle connection completion."""
        button.set_sensitive(True)
        button.set_label("Connect to Selected")
        return False
