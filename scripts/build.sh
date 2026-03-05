#!/bin/bash
# Gangwar Game Build Script
# Creates a standalone executable using PyInstaller

set -e  # Exit on any error

echo "Building Gangwar Game with PyInstaller..."
echo "Cleaning previous build artifacts..."
rm -rf build/ dist/ 2>/dev/null || true

# Create build directory
mkdir -p build

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