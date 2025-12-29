#!/bin/bash

# Cron Wrapper Script for PhD Hunt Agent
# Ensures correct environment and logging

# Absolute paths
cd /root/phd_agent || exit 1

# Load Python environment
source venv/bin/activate

# Use specific log file
LOGFILE="/root/phd_agent/logs/cron.log"

echo "==========================================" >> "$LOGFILE"
echo "📆 Starting Daily Run: $(date)" >> "$LOGFILE"

# Run the python script
# Mode 1 (default) - uses strict filters from utils.py
python3 main.py >> "$LOGFILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ finished successfully: $(date)" >> "$LOGFILE"
else
    echo "❌ finished with error (code $EXIT_CODE): $(date)" >> "$LOGFILE"
fi

echo "==========================================" >> "$LOGFILE"
