FROM python:3.12-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies (if needed for PyInstaller)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python
RUN ln -s /usr/local/bin/python3.12 /usr/bin/python

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install PyInstaller for building
RUN pip install pyinstaller

# Copy source files
COPY . .

# Build the application
RUN pyinstaller --clean gangwar.spec

WORKDIR /app/dist
RUN chmod +x gangwar

CMD ["./gangwar"]
