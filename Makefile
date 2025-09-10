# Pimpin Game Build System

.PHONY: build clean install run dist

# Install dependencies
install:
	pip install -r requirements.txt

# Run the application in development mode
run:
	python app.py

# Build the application to dist directory
build:
	./build.sh

# Create distribution
dist: build

# Clean build artifacts
clean:
	rm -rf build dist/pimpin* *.spec

# Full build and test
all: clean install build
	@echo "Build complete! Run with: ./dist/pimpin"

# Development setup
dev: install
	@echo "Development environment ready. Run with: make run"
