#!/bin/bash
set -e

PACKAGE=summit
VERSION=1.0.0
BUILD_DIR=build/${PACKAGE}

echo "=========================================="
echo "Building $PACKAGE $VERSION"
echo "=========================================="
echo ""

echo "[1/7] Cleaning previous build..."
rm -rf build/
mkdir -p build/

echo "[2/7] Creating package directory structure..."
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/${PACKAGE}/src"
mkdir -p "${BUILD_DIR}/usr/share/applications"

echo "[3/7] Copying DEBIAN control files..."
cp debian/control    "${BUILD_DIR}/DEBIAN/control"
cp debian/postinst   "${BUILD_DIR}/DEBIAN/postinst"
cp debian/changelog  "${BUILD_DIR}/DEBIAN/changelog"
cp debian/compat     "${BUILD_DIR}/DEBIAN/compat"
chmod 0755 "${BUILD_DIR}/DEBIAN/postinst"

echo "[4/7] Copying source files..."
cp src/*.py               "${BUILD_DIR}/usr/share/${PACKAGE}/src/"
cp style.css              "${BUILD_DIR}/usr/share/${PACKAGE}/"

echo "[5/7] Creating launcher wrapper..."
cat > "${BUILD_DIR}/usr/bin/${PACKAGE}" << 'LAUNCHER'
#!/bin/sh
exec python3 /usr/share/summit/src/main.py "$@"
LAUNCHER
chmod 0755 "${BUILD_DIR}/usr/bin/${PACKAGE}"

echo "[6/7] Creating desktop entry..."
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

echo "[7/7] Building .deb package..."
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "${PACKAGE}_${VERSION}_all.deb"

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo ""
echo "Package: ${PACKAGE}_${VERSION}_all.deb"
echo "Size: $(du -h ${PACKAGE}_${VERSION}_all.deb | cut -f1)"
echo ""
echo "To install:"
echo "  sudo dpkg -i ${PACKAGE}_${VERSION}_all.deb"
echo "  sudo apt-get install -f  (if dependencies need installing)"
echo ""
echo "To launch:"
echo "  summit"
echo ""
