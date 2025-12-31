#!/bin/bash
# Quick VPS Deployment Script for PhD Hunt Enhanced Features
# Run this on your VPS after SSHing in

echo "========================================"
echo "  PhD Hunt - VPS Deployment"
echo "========================================"
echo ""

# Step 1: Navigate to project directory
echo "Step 1: Navigating to project directory..."
cd /root/phd_agent || { echo "Error: Directory not found!"; exit 1; }
pwd

# Step 2: Check current status
echo ""
echo "Step 2: Checking current git status..."
git status

# Step 3: Pull latest changes from GitHub
echo ""
echo "Step 3: Pulling latest updates from GitHub..."
git pull origin main

# Step 4: Verify new files
echo ""
echo "Step 4: Verifying new files created..."
ls -lh faculty_scraper.py inquiry_detector.py test_new_modules.py VPS_DEPLOYMENT.md 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ New files found!"
else
    echo "⚠ Warning: Some new files may be missing"
fi

# Step 5: Run tests (optional but recommended)
echo ""
echo "Step 5: Running module tests..."
/root/phd_agent/venv/bin/python3 test_new_modules.py
TEST_RESULT=$?

# Step 6: Restart web dashboard service
echo ""
echo "Step 6: Restarting web dashboard service..."
sudo systemctl restart phd_dashboard
sleep 3

# Step 7: Check service status
echo ""
echo "Step 7: Checking service status..."
sudo systemctl status phd_dashboard --no-pager -l

# Step 8: Display access information
echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
echo "Web Dashboard URL:"
echo "  http://85.31.224.214:5000"
echo ""
echo "To check logs:"
echo "  sudo journalctl -u phd_dashboard -n 50 -f"
echo ""
echo "Test Results: "
if [ $TEST_RESULT -eq 0 ]; then
    echo "  ✅ All tests passed!"
else
    echo "  ⚠️ Some tests failed (check output above)"
fi
echo ""
echo "Next Steps:"
echo "  1. Open http://85.31.224.214:5000 in browser"
echo "  2. Login with your credentials"
echo "  3. Verify new checkboxes are visible"
echo "  4. Run a test search"
echo ""
