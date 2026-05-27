import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gi
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

# Register resources if they exist for tests
resource_path = os.path.join(
    os.path.dirname(__file__), "..", "src", "resources", "summit.gresource"
)
if os.path.exists(resource_path):
    try:
        resource = Gio.Resource.load(resource_path)
        Gio.resources_register(resource)
    except Exception:
        pass

from summit_manager import SummitManager
from status_pane import StatusPane


class TestSummitManagerReconnect(unittest.TestCase):
    @patch("summit_manager.SummitManager.run_command")
    def test_reconnect_bare(self, mock_run):
        """Test reconnect without arguments falls back to bare connect."""
        mock_run.return_value = ("Success", "", 0)
        manager = SummitManager()
        
        success, message = manager.reconnect()
        
        assert success is True
        mock_run.assert_called_with(["connect"])

    @patch("summit_manager.SummitManager.run_command")
    def test_reconnect_with_target(self, mock_run):
        """Test reconnect with arguments targets specific country and city."""
        mock_run.return_value = ("Success", "", 0)
        manager = SummitManager()
        
        success, message = manager.reconnect("United_States", "Saint_Louis")
        
        assert success is True
        mock_run.assert_called_with(["connect", "United_States", "Saint_Louis"])


class TestStatusPaneReconnectPersistence(unittest.TestCase):
    def setUp(self):
        self.mock_manager = Mock()
        self.pane = StatusPane(self.mock_manager)
        self.mock_app = Mock()
        self.mock_app.config = {
            "last_country": "",
            "last_city": "",
        }
        self.pane.set_app_ref(self.mock_app)

    def test_apply_status_persists_location(self):
        """Test apply_status writes successful connection to config."""
        status_data = {
            "Status": "Connected",
            "Country": "United States",
            "City": "Saint Louis",
            "Server": "us1234",
        }
        
        self.pane.apply_status(status_data)
        
        assert self.mock_app.config["last_country"] == "United_States"
        assert self.mock_app.config["last_city"] == "Saint_Louis"
        assert self.mock_app.save_config.called

    def test_apply_status_ignores_unknown(self):
        """Test apply_status does not save 'Unknown' values to config."""
        status_data = {
            "Status": "Connected",
            "Country": "Unknown",
            "City": "Unknown",
            "Server": "unknown-server",
        }
        
        self.pane.apply_status(status_data)
        
        assert self.mock_app.config["last_country"] == ""
        assert self.mock_app.config["last_city"] == ""
        assert not self.mock_app.save_config.called

    @patch("threading.Thread")
    def test_on_reconnect_clicked_uses_config(self, mock_thread):
        """Test on_reconnect_clicked reads config and calls reconnect with targets."""
        self.mock_manager.reconnect.return_value = (True, "Success")
        self.mock_app.config["last_country"] = "United_States"
        self.mock_app.config["last_city"] = "Saint_Louis"
        
        mock_button = Mock()
        self.pane.on_reconnect_clicked(mock_button)
        
        # Verify thread was started
        assert mock_thread.called
        
        # Extract the worker function from thread call
        worker_func = mock_thread.call_args[1]["target"]
        
        # Run worker function
        worker_func()
        
        # Verify manager.reconnect was called with the config targets
        self.mock_manager.reconnect.assert_called_with("United_States", "Saint_Louis")
