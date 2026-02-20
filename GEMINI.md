# GEMINI.md: Summit Project Manifest (v2.1)

Summit is a professional GTK4 interface for the NordVPN CLI, built for LMDE 7.

## 1. STRATEGIC ALIGNMENT
- **Global Compliance:** Strictly follows the **Global Development Manifest (WOLF v2.1)**.
- **Protocol:** Adheres to the **Logical Atomic Protocol** for clean, milestone-based history.
- **UI Standard:** Pure **GTK4 (`Gtk.HeaderBar`)** with Blueprint (`.blp`) UI definitions and GResources.

## 2. PROJECT ARCHITECTURE
- **Component Model:** Modular "panes" (src/ui/) with a 5-tab native experience.
- **Logic Isolation:** All NordVPN CLI logic must be strictly isolated in `src/summit_manager.py`. 
- **Privacy Policy:** XDG-compliant file operations only (~/.config/summit). Local-first design.
- **Styling:** Custom "card" visuals managed via `src/resources/style.css` using the `.pane-box` class.

## 3. BUILDING & VALIDATION
- **Dependency Tool:** **`uv`** for Python environment and dependency management.
- **Build System:** `./build.sh` is the single entry point for linting, testing, and packaging (Debian/Flatpak).
- **Validation:** 
    1. Compile Blueprints (`blueprint-compiler`)
    2. Compile GResources (`glib-compile-resources`)
    3. Run App (`uv run python src/main.py`)
- **Packaging:** Native Debian (`.deb`) build is the primary target for distribution.

## 4. VERSIONING & STATUS
- **Core Version:** 1.0.0 (Release Candidate)
- **Status:** Active Maintenance. Prioritize stable NordVPN CLI integration.
