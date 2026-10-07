#!/usr/bin/env bash
# Build a portable AppImage (M5; kept working so tags never ship a broken build).
#
#   ./scripts/build-appimage.sh
#   VERSION=0.1.0 ./scripts/build-appimage.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "${ROOT}"

VERSION="${VERSION:-$(python3 -c "import sys; sys.path.insert(0,'src'); \
import fatih_kalem; print(fatih_kalem.__version__)")}"
ARCH="${ARCH:-x86_64}"
BUILD_DIR="${ROOT}/build/appdir"
DIST_DIR="${ROOT}/dist"
APP_NAME="fatih-kalem"
APPIMAGE="${DIST_DIR}/${APP_NAME}-${VERSION}-${ARCH}.AppImage"

echo "==> Fatih Kalem ${VERSION} (${ARCH})"

command -v pyinstaller >/dev/null 2>&1 || {
  echo "pyinstaller is required: pip install pyinstaller" >&2
  exit 1
}
command -v appimagetool >/dev/null 2>&1 || \
  command -v appimagetool-x86_64.AppImage >/dev/null 2>&1 || {
    echo "appimagetool is required: https://github.com/AppImage/AppImageKit/releases" >&2
    exit 1
  }

echo "==> Cleaning"
rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

echo "==> Freezing (onedir: faster start, smaller image than onefile)"
pyinstaller \
  --noconfirm \
  --clean \
  --name "${APP_NAME}" \
  --distpath "${ROOT}/build/dist" \
  --workpath "${ROOT}/build/work" \
  --specpath "${ROOT}/build" \
  --windowed \
  --onedir \
  --osx-bundle-identifier org.fatihkalem.linux \
  --paths "${ROOT}/src" \
  --collect-submodules fatih_kalem \
  # Qt modules we never use - dropping them roughly halves the image.
  --exclude-module PyQt6.QtWebEngineCore \
  --exclude-module PyQt6.QtWebEngineWidgets \
  --exclude-module PyQt6.QtQuick \
  --exclude-module PyQt6.QtQml \
  --exclude-module PyQt6.Qt3DCore \
  --exclude-module PyQt6.QtMultimedia \
  --exclude-module PyQt6.QtNetwork \
  --exclude-module PyQt6.QtSql \
  --exclude-module PyQt6.QtTest \
  --exclude-module PyQt6.QtDesigner \
  --exclude-module PyQt6.QtHelp \
  --exclude-module PyQt6.QtBluetooth \
  --exclude-module PyQt6.QtCharts \
  --exclude-module PyQt6.QtDataVisualization \
  --exclude-module PyQt6.QtOpenGL \
  --exclude-module PyQt6.QtPdf \
  --exclude-module PyQt6.QtSerialPort \
  --exclude-module PyQt6.QtSensors \
  --exclude-module PyQt6.QtSpatialAudio \
  --exclude-module PyQt6.QtTextToSpeech \
  --exclude-module PyQt6.QtWebChannel \
  --exclude-module PyQt6.QtWebSockets \
  src/fatih_kalem/__main__.py

APPDIR="${ROOT}/build/dist/${APP_NAME}"
echo "==> Assembling AppDir"
mkdir -p "${BUILD_DIR}"
cp -r "${APPDIR}/"* "${BUILD_DIR}/"

install -Dm644 packaging/fatih-kalem.desktop \
  "${BUILD_DIR}/${APP_NAME}.desktop"
sed -i "s|Exec=${APP_NAME} %U|Exec=${APP_NAME}|" "${BUILD_DIR}/${APP_NAME}.desktop"
install -Dm644 assets/icon.svg "${BUILD_DIR}/${APP_NAME}.svg"
install -Dm644 assets/metainfo.xml "${BUILD_DIR}/${APP_NAME}.metainfo.xml"
install -Dm644 LICENSE "${BUILD_DIR}/usr/share/doc/${APP_NAME}/LICENSE"
install -Dm644 NOTICE "${BUILD_DIR}/usr/share/doc/${APP_NAME}/NOTICE"

cat >"${BUILD_DIR}/AppRun" <<'APPRUN'
#!/usr/bin/env bash
# AppRun: PyInstaller onedir bundles put everything next to this file.
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}:${PATH}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec "${HERE}/fatih-kalem" "$@"
APPRUN
chmod +x "${BUILD_DIR}/AppRun"

echo "==> Running desktop-file validation"
desktop-file-validate "${BUILD_DIR}/${APP_NAME}.desktop" || true

echo "==> Packaging"
if command -v appimagetool >/dev/null 2>&1; then
  ARCH="${ARCH}" appimagetool "${BUILD_DIR}" "${APPIMAGE}"
else
  appimagetool-x86_64.AppImage "${BUILD_DIR}" "${APPIMAGE}"
fi

chmod +x "${APPIMAGE}"
echo
echo "Built: ${APPIMAGE}  ($(du -h "${APPIMAGE}" | cut -f1))"
echo "Test it with: ${APPIMAGE} --print-session"