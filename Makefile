# Gangwar Game Makefile
# Cross-platform build system for the Gangwar game

.PHONY: all build clean distclean clean-disk install-deps run test help

# Default target
all: build

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
	@python3 -m pip install --break-system-packages -r requirements.txt
	@python3 -m pip install --break-system-packages pyinstaller

# Run the application in development mode
run:
	@echo "Running Gangwar Game in development mode..."
	@python3 app.py

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
	@python3 -c "import app; print('✓ Flask app imports successfully')"
	@python3 -c "import flask_socketio; print('✓ Flask-SocketIO available')"
	@python3 -c "import flask; print('✓ Flask available')"
	@echo "Basic tests passed!"

# Show help
help:
	@echo "Gangwar Game Build System"
	@echo "========================="
	@echo ""
	@echo "Available targets:"
	@echo "  all          - Build the application (default)"
	@echo "  build        - Build standalone executable"
	@echo "  clean        - Clean build artifacts"
	@echo "  distclean    - Clean everything including logs and config"
	@echo "  clean-disk   - Aggressive disk cleanup to free space"
	@echo "  install-deps - Install Python dependencies"
	@echo "  run          - Run in development mode"
	@echo "  run-dist     - Run the built executable"
	@echo "  test         - Run basic tests"
	@echo "  help         - Show this help"
	@echo ""
	@echo "Usage examples:"
	@echo "  make build          # Build the executable"
	@echo "  make run            # Run in development"
	@echo "  make run-dist       # Run built executable"
	@echo "  make clean && make  # Clean and rebuild"

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
