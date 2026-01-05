# PhD Hunt - AI-Powered Academic Headhunter

**PhD Hunt** is an advanced, autonomous agent designed to revolutionize the search for academic positions (PhD and PostDoc). Unlike traditional aggregators, this agent actively crawls university websites, navigates global job portals, and uses Large Language Models (LLMs) to verify the relevance and authenticity of each opportunity.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![AI-Powered](https://img.shields.io/badge/AI-GPT--4o-orange)

## 🚀 Key Features

-   **Multi-Source Aggregation**:
    -   Scrapes major global portals (e.g., OwlIndex, PhDScanner, ScholarshipDB, AcademicPositions).
    -   Specialized scrapers for **German** (35+ institutions) and **Finnish** (12+ institutions) universities.
-   **Deep University Crawling**:
    -   Goes beyond job boards by crawling faculty and department pages (`/jobs`, `/vacancies`, `/career`).
    -   Uses a heuristic-based crawler to navigate up to 4 levels deep.
-   **AI-Powered Verification**:
    -   Integrates **GPT-4o-mini** to analyze job descriptions.
    -   Filters out non-PhD roles, generic announcements, and irrelevant listings with high precision (<5% false positive rate).
-   **Modern Web Dashboard**:
    -   A premium, Apple-inspired interface to manage searches and view system status.
    -   Features glassmorphism design, dark mode, and real-time status updates.
-   **Smart Notifications**:
    -   Sends detailed email reports grouped by "New Discoveries", "Inquiry Opportunities", and "Professors".

## 🛠️ Methodology

The system operates on a multi-stage pipeline:

1.  **Discovery**:
    -   The agent initializes a set of targeted scrapers (Global Portals & University Specific).
    -   It uses a breadth-first search (BFS) strategy to traverse university websites, identifying pages likely to contain job listings.
2.  **Extraction**:
    -   HTML content is parsed to extract job titles, links, and dates.
    -   Pattern matching detects "Contact for Inquiry" opportunities on faculty pages.
3.  **Verification (The Brain)**:
    -   Potential matches are sent to the LLM (GPT-4o-mini).
    -   The LLM scores the position on relevance (0-10) and confirms if it matches the user's specific criteria (e.g., "PhD only").
4.  **Reporting**:
    -   Verified positions are deduplicated and stored.
    -   An email summary is compiled and sent to the user.

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/AMHB/PhD_Hunt.git
    cd PhD_Hunt
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    -   Create a `.env` file in the root directory.
    -   Add your API keys and credentials (see Configuration section).

## ⚙️ Configuration

Create a `.env` file with the following variables. **Do not share this file.**

```ini
# API Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Email Settings
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
```

## 🖥️ Usage

### Web Dashboard
Run the dashboard to manage the agent via a GUI:
```bash
python web_dashboard.py
```
Access at `http://localhost:5000`.

### Command Line
Run the agent directly from the terminal:
```bash
python main.py --keywords "Machine Learning, NLP" --recipient "me@example.com"
```

## 👨‍💻 Author

Written by **Ali Mehrban**.
