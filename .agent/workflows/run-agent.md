---
description: How to run the PhD Headhunter Agent
---

# Running the PhD Headhunter Agent

// turbo-all

## Steps

1. Navigate to the project directory:
```powershell
cd "c:\Users\Ali\My Drive (amehrb@gmail.com)\My_Repos\PhD_Agent"
```

2. Run the agent:
```powershell
python main.py
```

3. If you need to install dependencies:
```powershell
pip install -r requirements.txt
```

4. Install Playwright browsers (if needed):
```powershell
python -m playwright install chromium
```

## Notes
- The agent runs with `headless=False` so you can solve CAPTCHAs if needed
- Results are stored in `job_history.json`
- Email is sent to the address configured in `.env`
