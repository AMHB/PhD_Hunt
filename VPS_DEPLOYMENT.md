# VPS Deployment Instructions for PhD Hunt Enhanced

## Prerequisites
- SSH access to your VPS
- Git installed on VPS
- Project cloned at `/root/phd_agent`
- Python virtual environment set up

## Deployment Steps

### 1. Connect to VPS
```bash
ssh root@your-vps-ip
```

### 2. Navigate to Project Directory
```bash
cd /root/phd_agent
```

### 3. Pull Latest Changes from GitHub
```bash
git pull origin main
```

Expected output:
```
remote: Enumerating objects: 14, done.
remote: Counting objects: 100% (14/14), done.
Receiving objects: 100% (9/9), done.
Resolving deltas: 100% (5/5), done.
From https://github.com/AMHB/PhD_Hunt
   d92749b..fb30422  main -> origin/main
Updating d92749b..fb30422
Fast-forward
 faculty_scraper.py    | 398 ++++++++++++++++++++++++
 inquiry_detector.py   | 275 ++++++++++++++++
 llm_verifier.py       | 94 ++++++
 main.py               | 198 ++++++------
 test_new_modules.py   | 156 +++++++++
 utils.py              | 125 ++++++--
 web_dashboard.py      | 101 ++++--
 7 files changed, 1248 insertions(+), 119 deletions(-)
```

### 4. Verify New Files Created
```bash
ls -lah | grep -E "(faculty|inquiry|test)"
```

Should show:
- `faculty_scraper.py`
- `inquiry_detector.py`
- `test_new_modules.py`

### 5. Test New Modules (Optional but Recommended)
```bash
/root/phd_agent/venv/bin/python3 test_new_modules.py
```

Expected output:
```
================================================================================
 PhD HUNT ENHANCED MODULES - TEST SUITE
================================================================================

============================================================
TEST 1: Inquiry Detector
============================================================

✓ Test 1a - Positive Signal Detection:
  Has signal: True
  Patterns matched: 2
  Signal strength: 2

✓ Test 1b - Negative Signal Rejection:
  Has signal: False (should be False)

✓ Test 1c - Contact Extraction:
  Email: smith@university.edu

✓ Test 1d - Page Relevance:
  Is faculty page relevant: True

============================================================
✅ Inquiry Detector Tests Complete
============================================================

[... more test output ...]

✅ ALL TESTS COMPLETED SUCCESSFULLY!
```

### 6. Restart Web Dashboard Service
```bash
sudo systemctl restart phd_dashboard
sudo systemctl status phd_dashboard
```

Expected output:
```
● phd_dashboard.service - PhD Headhunter Web Dashboard
     Loaded: loaded (/etc/systemd/system/phd_dashboard.service; enabled)
     Active: active (running) since ...
```

### 7. Check Service Logs (Optional)
```bash
sudo journalctl -u phd_dashboard -n 50 -f
```

Press `Ctrl+C` to exit log view.

### 8. Test Web Dashboard
Open browser and navigate to:
```
http://your-vps-ip:5000
```

**Login** with your credentials

**Verify new UI elements:**
- [ ] Three checkboxes visible: "Open Positions", "Inquiry Positions", "Professors"
- [ ] "Open Positions" is checked by default
- [ ] Position Type dropdown at top (PhD / PostDoc)
- [ ] All existing fields still present

### 9. Run Test Search
1. Enter keywords (e.g., "machine learning, computer vision")
2. Check all three search type boxes
3. Enter your email
4. Click "Run PhD Agent Now"
5. Wait for completion (~20-30 minutes for all three types)
6. Check email for results

### 10. Verify Email Content
Email should contain:
- ✅ **🆕 Newly Discovered Positions** section
- ✅ **💡 Possible PhD/PostDoc Inquiry Positions** section (if found)
- ✅ **👨‍🔬 Professors/Supervisors in Your Field** section (if found)
- ✅ **📂 Previously Discovered Open Positions** section (filtered)

## Troubleshooting

### Issue: "git pull" shows merge conflicts

**Solution:**
```bash
git stash
git pull origin main
git stash pop
```

If conflicts remain, manually resolve them or:
```bash
git reset --hard origin/main  # WARNING: Discards local changes!
```

### Issue: Service won't restart

**Check logs:**
```bash
sudo journalctl -u phd_dashboard -n 100
```

**Common fixes:**
```bash
# Kill any orphan processes
sudo pkill -f "python.*web_dashboard.py"

# Restart service
sudo systemctl restart phd_dashboard
```

### Issue: Web dashboard shows old UI (no checkboxes)

**Hard refresh browser:**
- Chrome/Firefox: `Ctrl + Shift + R`
- Safari: `Cmd + Shift + R`

**Clear browser cache:**
- Chrome: Settings → Privacy → Clear browsing data

**Verify file was updated:**
```bash
grep "searchOpen" web_dashboard.py
```

Should return matches.

### Issue: Import errors when running test script

**Solution:**
```bash
# Ensure you're using venv Python
/root/phd_agent/venv/bin/python3 test_new_modules.py

# If still fails, check dependencies
/root/phd_agent/venv/bin/pip install -r requirements.txt
```

## Rollback Procedure (If Needed)

If new version causes issues, rollback to previous commit:

```bash
cd /root/phd_agent
git log --oneline -n 5  # Find previous commit hash
git checkout <previous-commit-hash>
sudo systemctl restart phd_dashboard
```

To return to latest:
```bash
git checkout main
git pull origin main
sudo systemctl restart phd_dashboard
```

## Post-Deployment Checklist

- [ ] Git pull completed successfully
- [ ] New files visible in directory
- [ ] Test script passes all tests
- [ ] Web dashboard service running
- [ ] UI shows new checkboxes
- [ ] Test search submitted successfully
- [ ] Email received with new sections
- [ ] No errors in service logs

## Support

If you encounter issues:
1. Check `/var/log/phd_dashboard.log` for errors
2. Run test script to isolate problem
3. Check GitHub for latest updates
4. Contact: amehrb@gmail.com

---

**Deployment completed successfully!** 🚀

The PhD Hunt project now supports:
- ✅ Enhanced validation with LLM relevance scoring
- ✅ Faculty/professor discovery
- ✅ Inquiry opportunity detection  
- ✅ Selectable email content via web dashboard

**Estimated API costs:** $2.50/year (well under $10 budget)
