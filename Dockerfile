FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies and Playwright browsers
# We need to install system dependencies for Playwright
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium

COPY . .

# Run the application
CMD ["python", "main.py"]
