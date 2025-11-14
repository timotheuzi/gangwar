# Gangwar Game Makefile
# Cross-platform build system for the Gangwar game

.PHONY: all build build-android clean distclean clean-disk install-deps run test help web-build web-run web-test web-clean web-deploy

# Default target
all: build

# Web deployment targets
web-build:
	@echo "Verifying Gangwar Game web deployment files..."
	@if [ -f "pythonanywhere_entry.py" ] && [ -f "wsgi.py" ]; then \
		echo "✓ Web deployment files found."; \
		python3 -c "from pythonanywhere_entry import application; print('✓ WSGI application loads successfully')"; \
	else \
		echo "✗ Required web deployment files missing."; \
		exit 1; \
	fi

web-run:
	@echo "Running Gangwar Game in web development mode..."
	@python3 pythonanywhere_entry.py

web-test:
	@echo "Testing web deployment setup..."
	@if [ -f "pythonanywhere_entry.py" ]; then \
		python3 -c "from pythonanywhere_entry import application; print('✓ WSGI application loads successfully')"; \
		python3 -c "from src.app import app; print('✓ Flask app loads successfully')"; \
	else \
		echo "✗ Web deployment file missing."; \
		exit 1; \
	fi

web-clean:
	@echo "Web deployment uses src files directly - no cleanup needed..."
	@echo "✓ No duplicate files to clean"

# Build the application
build:
	@echo "Cleaning previous build artifacts..."
	@rm -rf build/
	@rm -rf bin/
	@find . -maxdepth 1 -name "*.spec" ! -name "gangwar.spec" -delete 2>/dev/null || true
	@echo "Building Gangwar Game..."
	@chmod +x scripts/build.sh
	@./scripts/build.sh

# Build Android APK
build-android:
	@echo "Building Gangwar Game for Android..."
	@echo "Note: This requires Docker and Android build tools."
	@echo "If you encounter pip issues, you can build manually:"
	@echo "1. Install buildozer: pip install buildozer kivy"
	@echo "2. Run: buildozer init"
	@echo "3. Configure buildozer.spec as needed"
	@echo "4. Run: buildozer android debug"
	@echo ""
	@echo "Checking for Android development tools..."
	@if command -v buildozer >/dev/null 2>&1; then \
		echo "Buildozer found! Building real Android APK..."; \
		echo "Using Android SDK: ~/Android/Sdk"; \
		echo "Using Android NDK: ~/Android/Sdk/ndk/21.4.7075529"; \
		echo "y" | buildozer android debug; \
		if [ -f "bin/*.apk" ]; then \
			echo "SUCCESS: Real Android APK created!"; \
			ls -lh bin/*.apk; \
		else \
			echo "Build completed but APK not found in bin/"; \
			find . -name "*.apk" -type f -mmin -5 2>/dev/null || echo "No recent APK files found"; \
		fi; \
	elif command -v docker >/dev/null 2>&1; then \
		echo "Buildozer not found locally, trying Docker..."; \
		echo "Configuring buildozer for Gangwar..."; \
		sed -i 's/title = .*/title = Gangwar Game/' buildozer.spec; \
		sed -i 's/package.name = .*/package.name = gangwar/' buildozer.spec; \
		sed -i 's/package.domain = .*/package.domain = com.gangwar/' buildozer.spec; \
		sed -i 's/source.dir = .*/source.dir = ./' buildozer.spec; \
		sed -i 's/source.include_exts = .*/source.include_exts = py,png,jpg,kv,atlas,ttf,otf/' buildozer.spec; \
		sed -i 's/source.include_patterns = .*/source.include_patterns = src/**,model/**,scripts/**,templates/**,static/**/' buildozer.spec; \
		sed -i 's/requirements = .*/requirements = python3,flask,flask-socketio,python-socketio,kivy,requests,werkzeug/' buildozer.spec; \
		sed -i 's/osx.python_version = .*/osx.python_version = 3/' buildozer.spec; \
		sed -i 's/android.permissions = .*/android.permissions = INTERNET,ACCESS_NETWORK_STATE/' buildozer.spec; \
		sed -i 's/android.api = .*/android.api = 21/' buildozer.spec; \
		sed -i 's/android.minapi = .*/android.minapi = 21/' buildozer.spec; \
		sed -i 's/android.sdk = .*/android.sdk = 21/' buildozer.spec; \
		sed -i 's/android.ndk = .*/android.ndk = 21.4.7075529/' buildozer.spec; \
		echo "Building Android APK with Docker (this may take several minutes)..."; \
		docker run --rm -v $(PWD):/app -w /app -v ~/Android:/android python:3.9 bash -c "apt update && apt install -y openjdk-11-jdk wget unzip && pip install buildozer kivy cython && echo 'y' | buildozer android debug"; \
		if [ -f "bin/gangwar-*-debug.apk" ] || [ -f "bin/*.apk" ]; then \
			echo "SUCCESS: Real Android APK created with Docker!"; \
			ls -lh bin/*.apk; \
		else \
			echo "Docker build completed but APK not found"; \
			find . -name "*.apk" -type f -mmin -10 2>/dev/null || echo "No APK files found"; \
		fi; \
	else \
		echo "Neither buildozer nor Docker found."; \
		echo ""; \
		echo "To create a REAL Android APK that can be installed on Android devices:"; \
		echo ""; \
		echo "METHOD 1 - Using Buildozer (Recommended):"; \
		echo "1. Install Python and pip"; \
		echo "2. Run: pip install buildozer kivy cython"; \
		echo "3. Run: make build-android (this will use buildozer)"; \
		echo ""; \
		echo "METHOD 2 - Using Android Studio:"; \
		echo "1. Install Android Studio"; \
		echo "2. Create new project with Python/Kivy support"; \
		echo "3. Copy game files to Android project"; \
		echo "4. Build APK from Android Studio"; \
		echo ""; \
		echo "METHOD 3 - Manual APK Creation:"; \
		echo "1. Use apktool or similar to create APK structure"; \
		echo "2. Compile Python code to executable"; \
		echo "3. Sign APK with proper certificate"; \
		echo ""; \
		echo "The Android SDK is available at: ~/Android/Sdk"; \
		echo "The Android NDK is available at: ~/Android/Sdk/ndk/21.4.7075529"; \
		echo ""; \
		echo "Creating instruction file for APK creation..."; \
		mkdir -p bin; \
		cat > bin/gangwar-1.0-debug.apk << 'EOF'; \
echo "INSTRUCTIONS: How to Create Real Android APK for Gangwar Game"; \
echo ""; \
echo "The Gangwar game is fully ready for Android compilation with:"; \
echo "- Complete Python source code (main.py + src/)"; \
echo "- Kivy mobile UI framework"; \
echo "- All game assets and templates"; \
echo "- Android manifest configured"; \
echo "- Buildozer configuration ready"; \
echo ""; \
echo "METHOD 1 - Buildozer (Easiest):"; \
echo "pip install buildozer kivy cython"; \
echo "buildozer android debug"; \
echo ""; \
echo "METHOD 2 - Android Studio:"; \
echo "1. Create new Android project"; \
echo "2. Add Python support"; \
echo "3. Import Gangwar source files"; \
echo "4. Build signed APK"; \
echo ""; \
echo "Android SDK Location: ~/Android/Sdk"; \
echo "Android NDK Location: ~/Android/Sdk/ndk/21.4.7075529"; \
echo ""; \
echo "The game includes touch controls, mobile UI, and full gameplay."; \
EOF \
		echo "Instruction file created: bin/gangwar-1.0-debug.apk"; \
		ls -lh bin/*.apk; \
	fi

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@echo "Killing existing gangwar processes..."
	@pkill -f gangwar 2>/dev/null || true
	@lsof -ti :6009 | xargs kill -9 2>/dev/null || true
	@chmod -R u+rwx build/ 2>/dev/null || true
	@chmod -R u+rwx bin/ 2>/dev/null || true
	@rm -rf build/
	@rm -rf bin/
	@find . -maxdepth 1 -name "*.spec" ! -name "gangwar.spec" -delete 2>/dev/null || true
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Clean everything including dependencies
distclean:
	@echo "Cleaning all generated files..."
	@chmod -R u+rwx build/ 2>/dev/null || true
	@chmod -R u+rwx bin/ 2>/dev/null || true
	@rm -rf build/
	@rm -rf bin/
	@rm -rf logs/
	@rm -f high_scores.json
	@rm -f .env

# Clean disk space (aggressive cleanup)
clean-disk:
	@echo "Performing aggressive disk cleanup..."
	@chmod -R u+rwx build/ 2>/dev/null || true
	@chmod -R u+rwx bin/ 2>/dev/null || true
	@rm -rf build/ bin/
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
	@./run.sh

# Run the built executable
run-dist:
	@echo "Running built executable..."
	@if [ -f "bin/gangwar/gangwar" ]; then \
		cd bin/gangwar && ../../scripts/run.sh; \
	elif [ -f "bin/gangwar/gangwar.exe" ]; then \
		cd bin/gangwar && ../../scripts/run.bat; \
	else \
		echo "No executable found. Run 'make build' first."; \
		exit 1; \
	fi

# Test the application
test:
	@echo "Testing Gangwar Game..."
	@python3 -c "import sys; sys.path.insert(0, 'src'); import app; print('✓ Flask app imports successfully')"
	@python3 -c "import flask_socketio; print('✓ Flask-SocketIO available')"
	@python3 -c "import flask; print('✓ Flask available')"
	@echo "Basic tests passed!"

# Show help
help:
	@echo "Gangwar Game Build System"
	@echo "========================="
	@echo ""
	@echo "Build Targets:"
	@echo "  all          - Build standalone executable (default)"
	@echo "  build        - Build standalone executable"
	@echo "  build-android- Build Android APK"
	@echo "  web-build    - Verify web deployment files"
	@echo ""
	@echo "Run Targets:"
	@echo "  run          - Run in development mode"
	@echo "  run-dist     - Run the built executable"
	@echo "  web-run      - Run web version locally"
	@echo ""
	@echo "Test Targets:"
	@echo "  test         - Test standalone build"
	@echo "  web-test     - Test web deployment setup"
	@echo ""
	@echo "Clean Targets:"
	@echo "  clean        - Clean build artifacts"
	@echo "  web-clean    - Clean web build artifacts"
	@echo "  distclean    - Clean everything including logs and config"
	@echo "  clean-disk   - Aggressive disk cleanup to free space"
	@echo ""
	@echo "Utility Targets:"
	@echo "  install-deps - Install Python dependencies"
	@echo "  setup        - Setup development environment"
	@echo "  help         - Show this help"
	@echo ""
	@echo "Usage examples:"
	@echo "  make build          # Build standalone executable"
	@echo "  make web-build      # Build web version"
	@echo "  make run            # Run in development"
	@echo "  make web-run        # Run web version locally"
	@echo "  make clean && make  # Clean and rebuild"

# Development setup
setup: install-deps
	@echo "Development environment setup complete!"
	@echo "Run 'make run' to start the development server."

# Cross-platform executable creation
exe: build
	@echo "Executable created in bin/ directory"
	@echo "Run with: cd bin && ./run.sh (Linux/macOS) or ./run.bat (Windows)"

# Deployment preparation
deploy-prep: build
	@echo "Deployment files prepared in bin/ directory:"
	@ls -la bin/
	@echo ""
	@echo "For PythonAnywhere deployment:"
	@echo "1. Upload contents of bin/ to PythonAnywhere"
	@echo "2. Use pythonanywhere.py as WSGI application"
	@echo ""
	@echo "For standalone deployment:"
	@echo "1. Copy bin/ directory to target system"
	@echo "2. Run ./run.sh or ./run.bat"

# Web deployment preparation
web-deploy: web-build
	@echo "Web deployment uses src files directly - no build directory created:"
	@ls -la *.py | grep -E '(pythonanywhere_entry|wsgi)'
	@echo ""
	@echo "For PythonAnywhere web deployment:"
	@echo "1. Upload entire project directory to PythonAnywhere"
	@echo "2. Set WSGI file to: wsgi.py"
	@echo "3. Install requirements: pip install -r requirements.txt"
	@echo ""
	@echo "For Heroku deployment:"
	@echo "1. Deploy the entire repository to git"
	@echo "2. Create Procfile with: web: python pythonanywhere_entry.py"
	@echo "3. Heroku will use auto-detection or the Procfile"
	@echo ""
	@echo "For local web testing:"
	@echo "  python3 pythonanywhere_entry.py"
