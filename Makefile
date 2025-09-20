# Gangwar Game Makefile
# Cross-platform build system for the Gangwar game

PHONY: all build clean distclean clean-disk install-deps run test help

# Default target
all: build

# Kill all running instances of the game
kill:
	@echo "Killing all running instances of Gangwar Game..."
	@pkill -f "python.*app.py" 2>/dev/null || true
	@pkill -f "gangwar" 2>/dev/null || true
	@pkill -f "flask" 2>/dev/null || true
	@ps aux | grep -E "(gangwar|app\.py|flask.*gangwar)" | grep -v grep | awk '{print $$2}' | xargs kill -9 2>/dev/null || true
	@echo "All running instances killed."

# Kill all instances and clean up (force stop)
killall: kill
	@echo "Force cleanup completed."

# Kill ALL Python processes (nuclear option)
kill-python:
	@echo "KILLING ALL PYTHON PROCESSES..."
	@pkill -f python 2>/dev/null || true
	@pkill -f python3 2>/dev/null || true
	@pkill -f python3.* 2>/dev/null || true
	@ps aux | grep -E "python" | grep -v grep | awk '{print $$2}' | xargs kill -9 2>/dev/null || true
	@echo "ALL PYTHON PROCESSES TERMINATED."

# Emergency kill - kills everything Python-related
emergency-kill: kill-python
	@echo "Emergency cleanup completed - all Python processes killed."

# Build the application
build:

	@echo "Building Gangwar Game..."
	@chmod +x build.sh
	@./build.sh

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build/
	@rm -rf dist/
	@find . -maxdepth 1 -name "*.spec" ! -name "gangwar.spec" -delete 2>/dev/null || true
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Clean everything including dependencies
distclean: clean
	@echo "Cleaning all generated files..."
	@rm -rf logs/
	@rm -f high_scores.json
	@rm -f .env

# Clean disk space (aggressive cleanup)
clean-disk:
	@echo "Performing aggressive disk cleanup..."
	@rm -rf build/ dist/
	@find . -maxdepth 1 -name "*.spec" ! -name "gangwar.spec" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@pip cache purge 2>/dev/null || true
	@rm -rf /tmp/* 2>/dev/null || true
	@echo "Disk cleanup completed."

# Install Python dependencies
install-deps:
	@echo "Installing Python dependencies..."
	@pip install -r requirements.txt
	@pip install pyinstaller

# Run the application in development mode
run:
	@echo "Running Gangwar Game in development mode..."
	@FLASK_ENV=development python src/app.py

# Run the built executable
run-dist:
	@echo "Running built executable..."
	@if [ -f "dist/gangwar" ]; then \
		cd dist && ./run.sh; \
	elif [ -f "dist/gangwar.exe" ]; then \
		cd dist && ./run.bat; \
	else \
		echo "No executable found. Run 'make build' first."; \
		exit 1; \
	fi

# Test the application
test:
	@echo "Testing Gangwar Game..."
	@python -c "import src.app; print('✓ Flask app imports successfully')"
	@python -c "import flask_socketio; print('✓ Flask-SocketIO available')"
	@python -c "import flask; print('✓ Flask available')"
	@python -c "import eventlet" 2>/dev/null && echo "⚠ Warning: eventlet is installed but not needed with threading mode" || echo "✓ eventlet not installed (good for Python 3.13 compatibility)"
	@echo "Basic tests passed!"

# Show help
help:
	@echo "Gangwar Game Build System"
	@echo "========================="
	@echo ""
	@echo "Available targets:"
	@echo "  all             - Build the application (default)"
	@echo "  build           - Build standalone executable"
	@echo "  clean           - Clean build artifacts"
	@echo "  distclean       - Clean everything including logs and config"
	@echo "  clean-disk      - Aggressive disk cleanup to free space"
	@echo "  install-deps    - Install Python dependencies"
	@echo "  run             - Run in development mode"
	@echo "  run-dist        - Run the built executable"
	@echo "  test            - Run basic tests"
	@echo "  kill            - Kill all running instances of the game"
	@echo "  killall         - Kill all instances and force cleanup"
	@echo "  kill-python     - Kill ALL Python processes (nuclear option)"
	@echo "  emergency-kill  - Emergency kill - kills everything Python-related"
	@echo "  help            - Show this help"
	@echo ""
	@echo "Usage examples:"
	@echo "  make build              # Build the executable"
	@echo "  make run                # Run in development"
	@echo "  make run-dist           # Run built executable"
	@echo "  make clean && make      # Clean and rebuild"
	@echo "  make kill               # Stop all running instances"
	@echo "  make killall            # Force stop everything"
	@echo "  make kill-python        # Kill ALL Python processes"
	@echo "  make emergency-kill     # Nuclear option - kills all Python"

# Development setup
setup: install-deps
	@echo "Development environment setup complete!"
	@echo "Run 'make run' to start the development server."

# Cross-platform executable creation
exe: build
	@echo "Executable created in dist/ directory"
	@echo "Run with: cd dist && ./run.sh (Linux/macOS) or ./run.bat (Windows)"

# Deployment preparation
deploy-prep: build
	@echo "Deployment files prepared in dist/ directory:"
	@ls -la dist/
	@echo ""
	@echo "For PythonAnywhere deployment:"
	@echo "1. Upload contents of dist/ to PythonAnywhere"
	@echo "2. Use pythonanywhere.py as WSGI application"
	@echo ""
	@echo "For standalone deployment:"
	@echo "1. Copy dist/ directory to target system"
	@echo "2. Run ./run.sh or ./run.bat"
