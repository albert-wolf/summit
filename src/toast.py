import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib


class ToastOverlay(Gtk.Overlay):
    """Toast notification overlay for success/error messages."""

    def __init__(self):
        super().__init__()
        self.toast_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_box.set_halign(Gtk.Align.CENTER)
        self.toast_box.set_valign(Gtk.Align.END)
        self.toast_box.set_margin_bottom(24)
        self.toast_box.set_margin_start(12)
        self.toast_box.set_margin_end(12)
        self.add_overlay(self.toast_box)

        self.active_toast = None
        self.toast_timeout = None

    def show_toast(self, message: str, is_error: bool = False, duration: int = None):
        """Show a toast notification.

        Args:
            message: Text to display
            is_error: If True, show red styling; if False, show green
            duration: Auto-dismiss after N ms (default 3000 for success, 5000 for error)
        """
        # Remove existing toast if any
        if self.active_toast:
            self.toast_box.remove(self.active_toast)
            if self.toast_timeout:
                GLib.source_remove(self.toast_timeout)

        # Create new toast
        toast = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toast.add_css_class("pane-box")
        toast.set_margin_top(12)
        toast.set_margin_bottom(12)
        toast.set_margin_start(16)
        toast.set_margin_end(16)

        label = Gtk.Label(label=message)
        label.set_wrap(True)
        label.set_max_width_chars(50)
        if is_error:
            label.add_css_class("error-text")
        toast.append(label)

        self.toast_box.append(toast)
        self.active_toast = toast

        # Auto-dismiss
        duration = duration or (5000 if is_error else 3000)
        self.toast_timeout = GLib.timeout_add(duration, self.dismiss_toast)

    def dismiss_toast(self):
        """Remove current toast."""
        if self.active_toast:
            self.toast_box.remove(self.active_toast)
            self.active_toast = None
        self.toast_timeout = None
        return False
