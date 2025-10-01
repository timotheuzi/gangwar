#!/bin/bash

# Script to build and run the Gangwar project in a Docker container

echo "Building Gangwar Docker image (clean build)..."
docker build --no-cache -t gangwar .

if [ $? -eq 0 ]; then
    echo "Build successful. Running the container..."
    echo "The application will be accessible at http://localhost:7777"
    echo "Press Ctrl+C to stop the container."

    # Run the container in the background
    docker run -p 7777:7777 --rm gangwar &
    CONTAINER_PID=$!

    # Wait a moment for the app to start
    sleep 3

    # Open the browser
    if command -v xdg-open > /dev/null; then
        xdg-open http://localhost:7777
    elif command -v open > /dev/null; then
        open http://localhost:7777
    elif command -v start > /dev/null; then
        start http://localhost:7777
    else
        echo "Please open your browser and navigate to http://localhost:7777"
    fi

    # Wait for the container to finish
    wait $CONTAINER_PID
else
    echo "Build failed!"
    exit 1
fi
