#!/bin/bash

# Pimpin Game Build Script - Local Build Version
# This script builds the application locally using PyInstaller

echo "Building Pimpin Game locally..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Create dist directory if it doesn't exist
mkdir -p dist

# Copy deployment scripts to dist
cp pythonanywhere.py dist/ 2>/dev/null || echo "pythonanywhere.py not found"
cp run.sh dist/ 2>/dev/null || echo "run.sh not found"

# Make run.sh executable if it exists in dist
if [ -f "dist/run.sh" ]; then
    chmod +x dist/run.sh
fi

# Clean previous build
echo "Cleaning previous build..."
rm -rf build dist/gangwar dist/gangwar.exe

# Build the application
echo "Building application with PyInstaller..."
pyinstaller --clean gangwar.spec

# Generate environment variables file
echo "Generating environment variables file..."
python generate_env.py

# Check if build was successful
if [ -f "dist/gangwar" ] || [ -f "dist/gangwar.exe" ]; then
    echo "Build successful! Files created in dist/ directory:"
    ls -la dist/

    # Make the executable runnable
    if [ -f "dist/gangwar" ]; then
        chmod +x dist/gangwar
        echo "Made executable runnable: ./dist/gangwar"
    fi

    if [ -f "dist/gangwar.exe" ]; then
        chmod +x dist/gangwar.exe
        echo "Made executable runnable: ./dist/gangwar.exe"
    fi

    echo ""
    echo "To run the application:"
    echo "./dist/gangwar"
    echo "or"
    echo "./dist/gangwar.exe  (on Windows)"
    echo ""
    echo "The executable is standalone and requires no external Python installation or libraries."
    echo ""
    echo "For PythonAnywhere deployment:"
    echo "Upload the contents of the dist/ directory to PythonAnywhere"
    echo "Use pythonanywhere.py as your WSGI application file"
else
    echo "Build failed! Check the output above for errors."
    exit 1
fi
