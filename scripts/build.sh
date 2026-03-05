#!/bin/bash
# Gangwar Game Build Script
# Creates a standalone executable using PyInstaller

set -e  # Exit on any error

echo "Building Gangwar Game with PyInstaller..."
echo "Cleaning previous build artifacts..."
rm -rf build/ dist/ 2>/dev/null || true

# Create build directory
mkdir -p build

# Build PyInstaller bootloader if not present
PYINSTALLER_PATH=$(dirname $(python3 -c "import PyInstaller; print(PyInstaller.__file__)"))
BOOTLOADER_DIR="$PYINSTALLER_PATH/bootloader/Linux-64bit-intel"
BOOTLOADER_PATH="$BOOTLOADER_DIR/run"
if [ ! -f "$BOOTLOADER_PATH" ]; then
  echo "PyInstaller bootloader not found. Building it..."
  TEMP_DIR="/tmp/pyinstaller_build"
  rm -rf "$TEMP_DIR"
  git clone https://github.com/pyinstaller/pyinstaller.git "$TEMP_DIR"
  cd "$TEMP_DIR"/bootloader
  python3 ./waf distclean all --target-arch=64bit
  cd -
  mkdir -p "$BOOTLOADER_DIR"
  cp "$TEMP_DIR/bootloader/build/release/run" "$BOOTLOADER_DIR/"
  cp "$TEMP_DIR/bootloader/build/debug/run_d" "$BOOTLOADER_DIR/"
  rm -rf "$TEMP_DIR"
  echo "Bootloader built and copied to $BOOTLOADER_DIR"
fi

# Build the executable
echo "Running PyInstaller..."
pyinstaller --onefile --name gangwar --add-data "src/templates:templates" --add-data "src/static:static" --add-data "model:model" --windowed src/main.py

# Move the executable to bin/
echo "Moving executable to bin/ directory..."
mkdir -p bin/gangwar
mv dist/gangwar bin/gangwar/
cp -r build/gangwar/* bin/gangwar/ 2>/dev/null || true

# Create run script
cat > bin/gangwar/run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./gangwar
EOF
chmod +x bin/gangwar/run.sh

# Create run.bat for Windows
cat > bin/gangwar/run.bat << 'EOF'
@echo off
cd /d "%~dp0"
gangwar.exe
EOF

echo "Build completed successfully!"
echo "Executable created at: bin/gangwar/gangwar"
ls -lh bin/gangwar/