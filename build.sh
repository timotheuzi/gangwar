#!/bin/bash

# Pimpin Game Build Script - Local Build Version
# This script builds the application locally using PyInstaller

echo "Building Pimpin Game locally..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Delete and recreate dist directory
echo "Deleting and recreating dist/ directory..."
rm -rf dist
mkdir -p dist

# Create run.sh script in dist
cat > dist/run.sh << 'EOF'
#!/bin/bash

# Simple run script for the Gangwar executable

# Kill any existing instances of gangwar
echo "Checking for existing gangwar instances..."
if pgrep -f gangwar > /dev/null; then
    echo "Killing existing gangwar instances..."
    pkill -f gangwar
    sleep 2  # Wait for processes to terminate
fi

# Check if we're in the dist directory
if [ -f "gangwar" ]; then
    echo "Running Gangwar executable..."
    ./gangwar &
    EXECUTABLE_PID=$!
    sleep 3  # Wait a bit to see if it starts
    if kill -0 $EXECUTABLE_PID 2>/dev/null; then
        echo "Gangwar executable started successfully."
        wait $EXECUTABLE_PID
    else
        echo "Gangwar executable failed to start. Falling back to Python..."
        kill $EXECUTABLE_PID 2>/dev/null || true
        cd ..
        python app.py
    fi
elif [ -f "gangwar.exe" ]; then
    echo "Running Gangwar executable..."
    ./gangwar.exe &
    EXECUTABLE_PID=$!
    sleep 3  # Wait a bit to see if it starts
    if kill -0 $EXECUTABLE_PID 2>/dev/null; then
        echo "Gangwar executable started successfully."
        wait $EXECUTABLE_PID
    else
        echo "Gangwar executable failed to start. Falling back to Python..."
        kill $EXECUTABLE_PID 2>/dev/null || true
        cd ..
        python app.py
    fi
else
    echo "Error: Gangwar executable not found in current directory."
    echo "Falling back to Python..."
    cd ..
    python app.py
fi
EOF

# Make run.sh executable
chmod +x dist/run.sh

# Copy deployment scripts to dist
cp pythonanywhere.py dist/ 2>/dev/null || echo "pythonanywhere.py not found"

# Clean previous build directory (outside dist)
echo "Cleaning previous build..."
rm -rf build

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
