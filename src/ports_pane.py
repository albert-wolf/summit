import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from summit_manager import SummitManager


class PortsPane(Gtk.Box):
    """Tab 4: Allowlisted Port Management"""

    def __init__(self, manager: SummitManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.manager = nord
        self.ports = []

        # Title
        title = Gtk.Label(label="Allowlisted Ports")
        title.add_css_class("heading")
        self.append(title)

        # Ports list with border
        ports_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ports_container.add_css_class("pane-box")
        ports_container.set_margin_top(8)
        ports_container.set_margin_bottom(8)
        ports_container.set_margin_start(8)
        ports_container.set_margin_end(8)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self.ports_listbox = Gtk.ListBox()
        self.ports_listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled.set_child(self.ports_listbox)
        ports_container.append(scrolled)
        self.append(ports_container)

        # Add port section
        add_port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_port_box.set_margin_top(12)

        self.port_entry = Gtk.Entry()
        self.port_entry.set_placeholder_text("Port (1-65535)")
        self.port_entry.set_width_chars(15)
        add_port_box.append(self.port_entry)

        self.protocol_dropdown = Gtk.DropDown.new_from_strings(["Both", "TCP", "UDP"])
        add_port_box.append(self.protocol_dropdown)

        self.add_btn = Gtk.Button(label="Add Port")
        self.add_btn.connect("clicked", self.on_add_port_clicked)
        add_port_box.append(self.add_btn)

        self.append(add_port_box)

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
        self.ports_listbox.remove_all()
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
            self.ports_listbox.append(row)

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

    def on_add_port_clicked(self, button):
        """Add port to allowlist."""
        port_text = self.port_entry.get_text().strip()
        if not port_text or not port_text.isdigit():
            return

        port_num = int(port_text)
        if port_num < 1 or port_num > 65535:
            return

        selected = self.protocol_dropdown.get_selected()
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
        self.port_entry.set_text("")
        self.protocol_dropdown.set_selected(0)
        self.load_ports()
        return False
