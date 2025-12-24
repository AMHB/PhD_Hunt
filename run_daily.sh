#!/bin/bash
# Cron job script to run PhD Agent daily
# Add to crontab: 0 8 * * * /home/ubuntu/phd_agent/run_daily.sh

cd /home/ubuntu/phd_agent
source venv/bin/activate

# Run with virtual display (headless servers need this for Playwright)
export DISPLAY=:99
Xvfb :99 -screen 0 1280x720x24 &
XVFB_PID=$!

# Run the agent
python3 main.py >> /home/ubuntu/phd_agent/logs/phd_agent.log 2>&1

# Cleanup
kill $XVFB_PID 2>/dev/null
