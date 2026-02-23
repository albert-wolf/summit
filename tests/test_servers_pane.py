import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from servers_pane import ServersPane


class TestCityToCountriesMapping(unittest.TestCase):
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_load_city_to_countries_from_cache(self, mock_open, mock_exists):
        """Test loading city_to_countries from cache file."""
        import json

        # Mock cache file exists and contains data
        cache_data = {
            "version": 1,
            "city_to_countries": {
                "New_York": ["United_States"],
                "Toronto": ["Canada"]
            }
        }

        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(cache_data)

        mock_nord = Mock()
        pane = ServersPane(mock_nord)

        # Test loading
        result = pane.load_city_to_countries_from_cache()

        assert result == cache_data["city_to_countries"]
        assert "New_York" in result
        assert result["New_York"] == ["United_States"]

    @patch('builtins.open', create=True)
    def test_save_city_to_countries_to_cache(self, mock_open):
        """Test saving city_to_countries to cache file."""
        mock_nord = Mock()
        pane = ServersPane(mock_nord)

        test_mapping = {
            "New_York": ["United_States"],
            "Toronto": ["Canada"]
        }

        pane.save_city_to_countries_to_cache(test_mapping)

        # Verify file was opened for writing (open called at least once, for the write)
        assert mock_open.called

    def test_search_priority_cities_before_countries(self):
        """Test that cities have priority over countries when both match search."""
        mock_nord = Mock()
        pane = ServersPane(mock_nord)

        # Set up data where search text "York" could match city "New_York" and country "New_York_Land"
        pane.all_countries = ["United_States", "New_York_Land"]
        pane.all_cities = ["New_York", "Toronto"]
        pane.city_to_countries = {
            "New_York": ["United_States"],
            "Toronto": ["Canada"]
        }

        # Search for "york" - should prioritize city "New_York" and return ["United_States"]
        # NOT the country "New_York_Land"
        pane.search_text = "york"
        result = pane.get_countries_for_search_results()
        # Should return United_States (country that has New_York city)
        assert "United_States" in result, f"Expected United_States in {result}"
        # Should NOT prioritize New_York_Land unless it's the only match
        assert result == ["United_States"], f"Expected ['United_States'] but got {result}"

    def test_search_city_returns_matching_countries(self):
        """Test that get_countries_for_search_results returns correct countries for city searches."""
        mock_nord = Mock()
        mock_nord.get_countries.return_value = ["United_States", "Canada", "United_Kingdom"]

        pane = ServersPane(mock_nord)

        # Manually set up data
        pane.all_countries = ["United_States", "Canada", "United_Kingdom"]
        pane.all_cities = ["New_York", "Los_Angeles", "Toronto", "Vancouver", "London"]
        pane.city_to_countries = {
            "New_York": ["United_States"],
            "Los_Angeles": ["United_States"],
            "Toronto": ["Canada"],
            "Vancouver": ["Canada"],
            "London": ["United_Kingdom"]
        }

        # Test 1: Search for city "New" should return ["United_States"]
        pane.search_text = "new"
        result = pane.get_countries_for_search_results()
        assert result == ["United_States"], f"Expected ['United_States'] but got {result}"

        # Test 2: Search for city "Toronto" should return ["Canada"]
        pane.search_text = "toronto"
        result = pane.get_countries_for_search_results()
        assert result == ["Canada"], f"Expected ['Canada'] but got {result}"

        # Test 3: Search for country "United" should return ["United_Kingdom", "United_States"]
        # (priority: no cities match, so fall back to country names)
        pane.search_text = "united"
        result = pane.get_countries_for_search_results()
        expected = ["United_Kingdom", "United_States"]
        assert sorted(result) == sorted(expected), f"Expected {expected} but got {result}"

        # Test 4: Search for "Canada" as country should return ["Canada"]
        pane.search_text = "canada"
        result = pane.get_countries_for_search_results()
        assert result == ["Canada"], f"Expected ['Canada'] but got {result}"

    def test_build_city_to_countries_mapping(self):
        """Test that city_to_countries dict maps cities to their countries correctly."""
        # Mock NordManager
        mock_nord = Mock()
        mock_nord.get_countries.return_value = ["United_States", "Canada"]
        mock_nord.get_cities.side_effect = lambda country: {
            "United_States": ["New_York", "Los_Angeles"],
            "Canada": ["Toronto", "Vancouver"]
        }[country]

        # Create pane (will trigger city loading)
        pane = ServersPane(mock_nord)

        # Wait for background thread to complete (0.5s sleep + execution time)
        import time
        time.sleep(1.0)

        # Check mapping
        assert pane.city_to_countries is not None
        assert pane.city_to_countries.get("New_York") == ["United_States"]
        assert pane.city_to_countries.get("Toronto") == ["Canada"]


if __name__ == '__main__':
    unittest.main()
