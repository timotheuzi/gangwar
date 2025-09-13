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
