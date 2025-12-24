#!/bin/bash
# VPS Initial Setup Script for GitHub CI/CD
# Run this ONCE on the VPS to set up Git repo

cd /root/phd_agent

# Initialize git repo (if not already)
if [ ! -d ".git" ]; then
    git init
    git remote add origin https://github.com/YOUR_USERNAME/PhD_Agent.git
    echo "Git repo initialized. Update the remote URL with your actual repo!"
else
    echo "Git repo already exists"
fi

# Create .gitignore
cat > .gitignore << 'EOF'
# Virtual environment
venv/

# Local files
.env
job_history.json
logs/
*.log
__pycache__/
*.pyc

# IDE
.vscode/
.idea/
EOF

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Push your code to GitHub"
echo "2. Set these secrets in GitHub repo settings:"
echo "   - VPS_HOST: 85.31.224.214"
echo "   - VPS_USER: root"
echo "   - VPS_PASSWORD: (your password)"
echo ""
echo "3. Run: git pull origin main"
