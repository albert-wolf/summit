#!/bin/bash
set -e

PACKAGE=summit
VERSION=0.8.4
BUILD_DIR=build/${PACKAGE}

DIST_DIR=dist

# Handle flatpak build
if [ "$1" == "flatpak" ]; then
    echo "=========================================="
    echo "Building Flatpak: $PACKAGE $VERSION"
    echo "=========================================="
    
    if ! command -v flatpak-builder &> /dev/null; then
        echo "Error: flatpak-builder not found."
        exit 1
    fi
    
    # Compile resources before building flatpak if needed (though manifest handles it)
    glib-compile-resources --target=src/resources/summit.gresource --sourcedir=src src/resources/summit.gresource.xml
    
    flatpak-builder --force-clean --user --install build-flatpak io.github.summit.json
    echo "Flatpak build complete!"
    exit 0
fi

echo "=========================================="
echo "Building $PACKAGE $VERSION (.deb)"
echo "=========================================="
echo ""

echo "[1/8] Cleaning previous build..."
rm -rf build/
mkdir -p build/
mkdir -p ${DIST_DIR}

echo "[2/8] Compiling Blueprints..."
for blp in src/ui/*.blp; do
    ui="${blp%.blp}.ui"
    blueprint-compiler compile --output "$ui" "$blp"
done

echo "[3/8] Compiling resources..."
glib-compile-resources --target=src/resources/summit.gresource --sourcedir=src src/resources/summit.gresource.xml

echo "[4/8] Creating package directory structure..."
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/${PACKAGE}/src"
mkdir -p "${BUILD_DIR}/usr/share/${PACKAGE}/resources"
mkdir -p "${BUILD_DIR}/usr/share/applications"

echo "[5/8] Copying DEBIAN control files..."
cp debian/control    "${BUILD_DIR}/DEBIAN/control"
cp debian/postinst   "${BUILD_DIR}/DEBIAN/postinst"
cp debian/changelog  "${BUILD_DIR}/DEBIAN/changelog"
cp debian/compat     "${BUILD_DIR}/DEBIAN/compat"
chmod 0755 "${BUILD_DIR}/DEBIAN/postinst"

echo "[6/8] Copying source and resource files..."
cp src/*.py               "${BUILD_DIR}/usr/share/${PACKAGE}/src/"
cp src/resources/summit.gresource "${BUILD_DIR}/usr/share/${PACKAGE}/resources/"

echo "[7/8] Creating launcher wrapper..."
cat > "${BUILD_DIR}/usr/bin/${PACKAGE}" << 'LAUNCHER'
#!/bin/sh
exec python3 /usr/share/summit/src/main.py "$@"
LAUNCHER
chmod 0755 "${BUILD_DIR}/usr/bin/${PACKAGE}"

echo "[8/8] Creating desktop entry..."
cat > "${BUILD_DIR}/usr/share/applications/${PACKAGE}.desktop" << 'DESKTOP'
[Desktop Entry]
Name=Summit
Comment=GTK4 NordVPN Client
Exec=summit
Icon=network-vpn
Terminal=false
Type=Application
Categories=Utility;Network;
Keywords=nordvpn;vpn;
StartupWMClass=summit
StartupNotify=true
DESKTOP

echo "[9/9] Building .deb package..."
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "${DIST_DIR}/${PACKAGE}_${VERSION}_all.deb"

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo ""
echo "Package: ${DIST_DIR}/${PACKAGE}_${VERSION}_all.deb"
echo "Size: $(du -h ${DIST_DIR}/${PACKAGE}_${VERSION}_all.deb | cut -f1)"
echo ""
echo "To install:"
echo "  sudo dpkg -i ${DIST_DIR}/${PACKAGE}_${VERSION}_all.deb"
echo "  sudo apt-get install -f  (if dependencies need installing)"
echo ""
echo "To launch:"
echo "  summit"
echo ""
