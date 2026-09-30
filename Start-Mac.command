#!/bin/bash
# Double-click this file to start Mason Lab on a Mac.
cd "$(dirname "$0")"
echo "Installing / updating what Mason Lab needs (first time takes a minute)..."
python3 -m pip install --quiet --user -r requirements.txt
if [ ! -f config.yaml ]; then
  python3 -m mason_lab setup
fi
echo ""
echo "Mason Lab is running. Leave this window open. Press Ctrl+C to stop."
caffeinate -i python3 -m mason_lab run
