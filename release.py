#!/usr/bin/env python3
import sys
import re
import subprocess
from pathlib import Path

def print_step(msg):
    print(f"\n\033[1;34m==>\033[0m \033[1m{msg}\033[0m")

def print_success(msg):
    print(f"\033[1;32m✓\033[0m {msg}")

def print_error(msg):
    print(f"\033[1;31m✗ Error:\033[0m {msg}")
    sys.exit(1)

def run_command(cmd, shell=False):
    res = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    if res.returncode != 0:
        print_error(f"Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}\nStderr: {res.stderr.strip()}")
    return res.stdout.strip()

def extract_changelog_notes(version):
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        return f"Release v{version}"
    
    content = changelog_path.read_text()
    header = f"## v{version}"
    if header not in content:
        return f"Release v{version}"
    
    start_idx = content.find(header)
    # Move past the header line
    notes_start = content.find("\n", start_idx) + 1
    
    # Find the next version header
    next_header_idx = content.find("\n## v", notes_start)
    if next_header_idx != -1:
        notes = content[notes_start:next_header_idx].strip()
    else:
        notes = content[notes_start:].strip()
        
    return notes

def main():
    if len(sys.argv) < 2:
        print_error("Missing version argument. Usage: ./release.py <version_string> (e.g. ./release.py 0.9.2)")
    
    new_version = sys.argv[1].strip().lstrip("v")
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print_error(f"Invalid SemVer version string: '{new_version}'. Must be in X.Y.Z format.")
        
    print_step(f"Starting release pipeline for v{new_version}")

    # 1. Sync Version in all required files
    print_step("Synchronizing version references...")
    
    # pyproject.toml
    pyproject_path = Path("pyproject.toml")
    pyproject_content = pyproject_path.read_text()
    pyproject_content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', pyproject_content, count=1)
    pyproject_path.write_text(pyproject_content)
    print_success("Synced pyproject.toml")

    # build.sh
    build_path = Path("build.sh")
    build_content = build_path.read_text()
    build_content = re.sub(r'VERSION=[^\n]+', f'VERSION={new_version}', build_content, count=1)
    build_path.write_text(build_content)
    print_success("Synced build.sh")

    # debian/control
    control_path = Path("debian/control")
    control_content = control_path.read_text()
    control_content = re.sub(r'Version: [^\n]+', f'Version: {new_version}', control_content, count=1)
    control_path.write_text(control_content)
    print_success("Synced debian/control")

    # src/main.py
    main_path = Path("src/main.py")
    main_content = main_path.read_text()
    main_content = re.sub(r'dialog\.set_version\("[^"]+"\)', f'dialog.set_version("{new_version}")', main_content, count=1)
    main_path.write_text(main_content)
    print_success("Synced src/main.py")

    # src/ui/main_window.blp
    blp_path = Path("src/ui/main_window.blp")
    blp_content = blp_path.read_text()
    blp_content = re.sub(r'label: "Summit [^"]+";', f'label: "Summit {new_version}";', blp_content, count=1)
    blp_path.write_text(blp_content)
    print_success("Synced src/ui/main_window.blp")

    # README.md (Title header on line 1, and installation deb file package string)
    readme_path = Path("README.md")
    readme_content = readme_path.read_text()
    # Replace line 1 title header
    lines = readme_content.splitlines()
    if lines and lines[0].startswith("# Summit"):
        lines[0] = f"# Summit — GTK4 NordVPN GUI (v{new_version})"
    readme_content = "\n".join(lines) + "\n"
    # Replace installation examples (e.g. summit_0.9.1_all.deb)
    readme_content = re.sub(r'summit_\d+\.\d+\.\d+_all\.deb', f'summit_{new_version}_all.deb', readme_content)
    readme_path.write_text(readme_content)
    print_success("Synced README.md title & installation instructions")

    # uv lockfile synchronization
    print_step("Updating package lockfile...")
    run_command(["uv", "lock"])
    print_success("Synced uv.lock")

    # 2. Quality Gate (Lints & Tests)
    print_step("Executing Quality Gate (ruff check & pytest)...")
    run_command(["uv", "run", "ruff", "check", "src/", "tests/"])
    print_success("Code linting checks passed successfully.")
    
    run_command(["uv", "run", "pytest", "tests/"])
    print_success("All automated unit tests passed successfully.")

    # 2.5. Automated Visual Asset Generation (Screenshots)
    print_step("Executing Automated Visual Asset Generation (Screenshots)...")
    run_command(["uv", "run", "python3", "src/main.py", "--mock-status", "--screenshot-mode"])
    print_success("Visual assets generated and updated in docs/screenshots/")

    # 3. Pristine Build packaging
    print_step("Compiling resources and building Debian package...")
    run_command(["./build.sh"])
    deb_file = Path(f"dist/summit_{new_version}_all.deb")
    if not deb_file.exists():
        print_error(f"Expected build artifact not found: {deb_file}")
    print_success(f"Successfully generated build artifact: {deb_file}")

    # 4. Git committing and tagging
    print_step("Staging and committing release version bump...")
    run_command(["git", "add", "-A"])
    run_command(["git", "commit", "-m", f"chore: release v{new_version}", "-m", "Co-authored-by: Gemini CLI <218195315+gemini-cli@users.noreply.github.com>"])
    print_success("Staged and committed version changes.")

    print_step(f"Creating Git annotated release tag v{new_version}...")
    # Delete local tag if it already exists to avoid clashes
    subprocess.run(["git", "tag", "-d", f"v{new_version}"], capture_output=True)
    run_command(["git", "tag", "-a", f"v{new_version}", "-m", f"Release v{new_version}"])
    print_success(f"Tagged commit with v{new_version}")

    # 5. Push to GitHub
    print_step("Pushing commits and tags to GitHub...")
    run_command(["git", "push", "origin", "main", "--tags"])
    print_success("Remote GitHub repository updated successfully.")

    # 6. GitHub Release Asset Creation
    print_step("Extracting release notes and creating GitHub Release...")
    notes = extract_changelog_notes(new_version)
    
    temp_notes_file = Path("temp_release_notes.md")
    temp_notes_file.write_text(notes)
    
    try:
        # Delete remote release if it exists to allow overriding
        subprocess.run(["gh", "release", "delete", f"v{new_version}", "-y", "--cleanup-tag"], capture_output=True)
        # Create fresh release
        run_command([
            "gh", "release", "create", f"v{new_version}",
            str(deb_file),
            "--title", f"v{new_version}",
            "--notes-file", str(temp_notes_file)
        ])
        print_success(f"GitHub Release page created with uploaded build artifact!")
    finally:
        if temp_notes_file.exists():
            temp_notes_file.unlink()

    print(f"\n\033[1;32m==================================================\033[0m")
    print(f"\033[1;32mRelease v{new_version} published in one fell swoop!\033[0m")
    print(f"\033[1;32m==================================================\033[0m\n")

if __name__ == "__main__":
    main()
