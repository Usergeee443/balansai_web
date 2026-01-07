#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories if they don't exist
mkdir -p static/css static/js templates

echo "Build completed successfully!"
