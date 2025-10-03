#!/bin/bash

# Gangwar Game Launcher
# Proper executable management with process cleanup and fallback support
# Supports automatic killing of existing processes and cross-platform execution

set -e  # Exit on any error

# Function to detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        CYGWIN*|MINGW*|MSYS*) echo "windows";;
        *)          echo "unknown";;
    esac
}

# Function to check if a process is running
is_process_running() {
    local pid=$1
    if [ "$(detect_os)" = "windows" ]; then
        # Windows check
        tasklist /FI "PID eq $pid" 2>NUL | grep -q "$pid" && return 0 || return 1
    else
        # Unix-like systems
        kill -0 "$pid" 2>/dev/null
    fi
}

# Function to clean up gangwar processes
cleanup_gangwar_processes() {
    echo "Checking for and cleaning up existing gangwar processes..."

    # Kill any existing gangwar processes
    if pgrep -f gangwar >/dev/null 2>&1; then
        echo "Killing existing gangwar processes..."
        pkill -f gangwar
        sleep 2  # Wait for processes to terminate cleanly
        if pgrep -f gangwar >/dev/null 2>&1; then
            echo "Force killing remaining gangwar processes..."
            pkill -9 -f gangwar
            sleep 1
        fi
    fi
}

# Function to find Python executable
find_python() {
    # Try different Python executables in order of preference
    for python_cmd in python3 python python3.9 python3.8 python3.7; do
        if command -v "$python_cmd" >/dev/null 2>&1; then
            if "$python_cmd" -c "import sys; print(sys.version_info[:2]); sys.exit(0)" >/dev/null 2>&1; then
                echo "$python_cmd"
                return 0
            fi
        fi
    done
    echo "python3"  # fallback, even if not found
    return 1
}

# Function to check Python dependencies
check_python_deps() {
    local python_cmd=${1:-python3}
    echo "Checking Python dependencies using $python_cmd..."

    if "$python_cmd" -c "import flask, flask_socketio" 2>/dev/null; then
        return 0
    fi

    echo "Required dependencies not found. Installing with pip..."
    if ! "$python_cmd" -m pip install -r requirements.txt --quiet; then
        echo "Error: Failed to install Python dependencies."
        echo "Try installing manually: $python_cmd -m pip install -r requirements.txt"
        return 1
    fi

    echo "Dependencies installed successfully."
    return 0
}

# Function to parse command line arguments
parse_args() {
    PORT_ARG=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port|-p)
                PORT_ARG="--port=$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
}

# Main execution
echo "Gangwar Game Launcher"
echo "======================"
echo "OS Detected: $(detect_os)"
echo "Timestamp: $(date)"
echo ""

# Parse command line arguments
parse_args "$@"

# Kill any existing processes that might be using our ports (5000 or specified)
echo "Checking for and killing existing server processes..."
pids=$(lsof -ti :5000 2>/dev/null || true)
if [ -n "$pids" ]; then
    echo "Killing processes on port 5000: $pids"
    kill -9 $pids 2>/dev/null || true
    sleep 1
fi

# Clean up any existing processes
cleanup_gangwar_processes

# Determine executable name based on OS
OS_TYPE=$(detect_os)
EXECUTABLE_NAME=""

if [ "$OS_TYPE" = "windows" ]; then
    if [ -f "gangwar.exe" ]; then
        EXECUTABLE_NAME="gangwar.exe"
    elif [ -f "gangwar" ]; then
        EXECUTABLE_NAME="gangwar"
    fi
else
    if [ -f "gangwar" ]; then
        EXECUTABLE_NAME="gangwar"
    elif [ -f "gangwar.exe" ]; then
        EXECUTABLE_NAME="gangwar.exe"
    fi
fi

# Try to run the executable
if [ -n "$EXECUTABLE_NAME" ]; then
    echo "Found executable: $EXECUTABLE_NAME"
    echo "Launching Gangwar executable..."
    echo ""

    # Make sure it's executable (Linux/macOS)
    chmod +x "$EXECUTABLE_NAME" 2>/dev/null || true

    # Run the executable in background and capture PID for monitoring
    ./"$EXECUTABLE_NAME" &
    EXECUTABLE_PID=$!

    echo "Executable started with PID: $EXECUTABLE_PID"

    # Monitor startup for a few seconds
    for i in {1..10}; do
        sleep 1
        if ! is_process_running "$EXECUTABLE_PID"; then
            echo ""
            echo "❌ Executable failed to start or crashed."
            echo "Falling back to Python..."
            echo ""
            break
        elif [ $i -eq 2 ]; then
            echo "✅ Executable appears to be running. You can now access http://localhost:5000"
            echo "Press Ctrl+C to stop the launcher (game will continue running in background)"
            echo ""
            break
        fi
    done

    # If executable is still running, let it continue and exit the launcher
    if is_process_running "$EXECUTABLE_PID"; then
        echo "Launcher exiting. Game is running in background."
        exit 0
    fi
else
    echo "No packaged executable found."
fi

# Fallback to Python if executable failed or wasn't found
echo "Attempting to run with Python..."

PYTHON_EXE=$(find_python)
echo "Using Python interpreter: $PYTHON_EXE"

# Find the absolute path to the project root (where src/app.py is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"

if [ ! -f "${PROJECT_ROOT}/src/app.py" ]; then
    echo "Error: src/app.py not found in ${PROJECT_ROOT}. Please ensure you're in a valid gangwar project directory."
    exit 1
fi

# Check Python dependencies
if ! check_python_deps "$PYTHON_EXE"; then
    exit 1
fi

echo ""
echo "Starting Gangwar with Python..."
echo "The application should be available at: http://localhost:5000"
echo "Press Ctrl+C to stop."
echo ""

# Change to project root and start the Python application
cd "$PROJECT_ROOT"
exec "$PYTHON_EXE" "src/app.py" $PORT_ARG
