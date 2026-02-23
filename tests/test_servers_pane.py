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

        # Verify file was opened for writing
        mock_open.assert_called_once()

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
