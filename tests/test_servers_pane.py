import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from servers_pane import ServersPane


class TestCityToCountriesMapping(unittest.TestCase):
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
