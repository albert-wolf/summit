# Project Overview: Summit

Summit is a professional, community-developed GTK4 graphical interface for the NordVPN command-line tool on Linux. Built with **Python 3** and **GTK4 (via PyGObject)**, it provides a native, 5-tab experience for managing VPN connections, security settings, ports, and Meshnet peers. 

The project follows a modern GNOME-adjacent architecture, using **Blueprint (.blp)** for UI definitions and **GResources** for asset management, ensuring a clean separation between presentation and logic.

## Building and Running

### Development Setup
The project uses **`uv`** for dependency management.

1.  **Install System Dependencies (Debian/LMDE):**
    ```bash
    sudo apt-get install python3 python3-gi gir1.2-gtk-4.0 blueprint-compiler libgirepository-2.0-dev libcairo2-dev python3-dev
    ```
2.  **Sync Environment:**
    ```bash
    uv sync
    ```

### Running from Source
Before launching, you must compile the UI templates and resources:
```bash
# Compile Blueprints to XML
for f in src/ui/*.blp; do blueprint-compiler compile --output="${f%.blp}.ui" "$f"; done

# Compile GResource
glib-compile-resources --target=src/resources/summit.gresource --sourcedir=src src/resources/summit.gresource.xml

# Run
uv run python src/main.py
```

### Packaging
*   **Debian (.deb):** Run `bash build.sh` to generate the installer.
*   **Flatpak:** Run `bash build.sh flatpak` to build and install the sandboxed version.

## Development Conventions

*   **UI Standard:** All layouts **MUST** be defined in Blueprint (`.blp`) files within `src/ui/`. Do not construct complex widget trees directly in Python.
*   **Styling:** Custom visuals (like the "card" panes) are handled via `src/resources/style.css`. Use the `.pane-box` class for content containers.
*   **Linting:** The project uses **`ruff`**. All code must be linted and formatted before commit.
    *   `uv run ruff check . --fix`
    *   `uv run ruff format .`
*   **Privacy:** Never hardcode absolute paths or personal identifiers. Use `Path.home()` for XDG-compliant file operations (~/.config/summit).
*   **Architecture:** UI components are modular "panes." All CLI logic is strictly isolated in `src/summit_manager.py`. UI files should never call `subprocess` directly.
