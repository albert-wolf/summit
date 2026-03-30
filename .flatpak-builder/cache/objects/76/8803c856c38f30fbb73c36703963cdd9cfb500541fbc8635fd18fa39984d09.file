import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from summit_manager import SummitManager


@Gtk.Template(resource_path="/io/github/summit/ui/ports_pane.ui")
class PortsPane(Gtk.Box):
    """Tab 4: Allowlisted Port Management"""

    __gtype_name__ = "PortsPane"

    ports_list = Gtk.Template.Child()
    port_spin = Gtk.Template.Child()
    proto_dropdown = Gtk.Template.Child()
    add_btn = Gtk.Template.Child()

    def __init__(self, manager: SummitManager):
        super().__init__()
        self.init_template()

        self.manager = manager
        self.ports = []

        # Load ports
        self.load_ports()

    def load_ports(self):
        """Load ports list in background thread."""

        def worker():
            settings = self.manager.get_settings()
            ports = settings.get("allowlisted_ports", [])
            GLib.idle_add(self.on_ports_loaded, ports)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_ports_loaded(self, ports):
        """Populate ports listbox with remove buttons."""
        self.ports_list.remove_all()
        self.ports = ports

        for port_entry in ports:
            row = Gtk.ListBoxRow()
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_margin_top(8)
            row_box.set_margin_bottom(8)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)

            # Port label
            label = Gtk.Label(label=port_entry, xalign=0)
            label.set_hexpand(True)
            row_box.append(label)

            # Remove button
            remove_btn = Gtk.Button(label="Remove")
            remove_btn.connect("clicked", self.on_remove_port_clicked, port_entry)
            row_box.append(remove_btn)

            row.set_child(row_box)
            self.ports_list.append(row)

        return False

    def on_remove_port_clicked(self, button, port_entry):
        """Handle port removal when remove button is clicked."""
        # Parse port entry (format: "5000 (UDP|TCP)")
        parts = port_entry.split()
        if len(parts) < 1:
            return

        port_num = parts[0]

        button.set_sensitive(False)
        button.set_label("Removing...")

        def worker():
            # Remove with no protocol specified - removes all protocols for this port
            success, message = self.manager.remove_port(int(port_num), None)
            GLib.idle_add(self.on_port_operation_done, success)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    @Gtk.Template.Callback()
    def on_add_port_clicked(self, button):
        """Add port to allowlist."""
        port_num = self.port_spin.get_value_as_int()
        if port_num < 1 or port_num > 65535:
            return

        selected = self.proto_dropdown.get_selected()
        # Map dropdown selection: 0=Both (None), 1=TCP, 2=UDP
        protocol = [None, "TCP", "UDP"][selected]

        button.set_sensitive(False)
        button.set_label("Adding...")

        def worker():
            success, message = self.manager.add_port(port_num, protocol)
            GLib.idle_add(self.on_port_operation_done, success)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_port_operation_done(self, success):
        """Handle port operation completion."""
        self.add_btn.set_sensitive(True)
        self.add_btn.set_label("Add Port")
        self.port_spin.set_value(1)
        self.proto_dropdown.set_selected(0)
        self.load_ports()
        return False
