#!/bin/bash
# Start the multi-threaded drive daemon from repo root.
# Usage: ./start_drive.sh [--log /tmp/drive.log]
set -e
cd "$(dirname "$0")"
source venv/bin/activate
LOG=${1:-/tmp/drive.log}
rm -f /tmp/drive.sock
python -u drive/daemon.py > "$LOG" 2>&1 &
PID=$!
echo "drive daemon started PID=$PID log=$LOG"
until grep -q "ready" "$LOG" 2>/dev/null; do sleep 0.5; done
grep -E "\[drive_daemon\]|\[sensor\]|\[lidar\]|\[vision\]" "$LOG" | grep -v "INFO\|WARN\|libcamera\|libpisp" | head -10
