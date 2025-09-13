#!/bin/bash

# Simple run script for the Gangwar executable

# Check if we're in the dist directory
if [ -f "gangwar" ]; then
    echo "Running Gangwar executable..."
    ./gangwar
elif [ -f "gangwar.exe" ]; then
    echo "Running Gangwar executable..."
    ./gangwar.exe
else
    echo "Error: Gangwar executable not found in current directory."
    echo "Please run this script from the dist/ directory or ensure the executable exists."
    exit 1
fi
