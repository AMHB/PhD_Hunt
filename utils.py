import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from jinja2 import Template

HISTORY_FILE = "job_history.json"

class StateManager:
    def __init__(self, file_path=HISTORY_FILE):
        self.file_path = file_path
        self.history = self._load_history()

    def _load_history(self):
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_history(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=4, ensure_ascii=False)

    def is_new(self, job_url):
        return job_url not in self.history

    def add_job(self, job):
        """
        job dict: {url, title, university, found_date, source, ...}
        Adds status tracking for validity
        """
        if job["url"] not in self.history:
            job["status"] = "active"  # active, expired, unknown
            job["last_checked"] = datetime.now().strftime("%Y-%m-%d")
            self.history[job["url"]] = job
            self.save_history()
            return True
        return False

    def get_all_jobs(self):
        return list(self.history.values())
    
    def get_active_jobs(self):
        """Return only jobs marked as active"""
        return [j for j in self.history.values() if j.get("status", "active") == "active"]
    
    def mark_expired(self, job_url):
        """Mark a job as expired (no longer available)"""
        if job_url in self.history:
            self.history[job_url]["status"] = "expired"
            self.history[job_url]["last_checked"] = datetime.now().strftime("%Y-%m-%d")
            self.save_history()
    
    def mark_active(self, job_url):
        """Mark a job as still active"""
        if job_url in self.history:
            self.history[job_url]["status"] = "active"
            self.history[job_url]["last_checked"] = datetime.now().strftime("%Y-%m-%d")
            self.save_history()

    async def recheck_jobs(self, page):
        """
        Recheck if previously found jobs are still valid.
        Uses Playwright page to check if URLs are still accessible.
        Returns list of still-valid jobs.
        """
        active_jobs = []
        jobs_to_check = self.get_all_jobs()
        
        print(f"Rechecking {len(jobs_to_check)} previously found positions...")
        
        for job in jobs_to_check:
            if job.get("status") == "expired":
                continue
                
            url = job.get("url", "")
            if not url:
                continue
            
            try:
                response = await page.goto(url, timeout=15000)
                
                # Check if page loaded successfully
                if response and response.status == 200:
                    # Check for common "expired" indicators
                    page_text = await page.inner_text("body")
                    expired_indicators = [
                        "position has been filled",
                        "no longer available",
                        "expired", "closed",
                        "nicht mehr verfügbar",
                        "stelle besetzt",
                        "404", "not found"
                    ]
                    
                    is_expired = any(ind in page_text.lower() for ind in expired_indicators)
                    
                    if is_expired:
                        self.mark_expired(url)
                        print(f"  ❌ Expired: {job['title'][:50]}...")
                    else:
                        self.mark_active(url)
                        active_jobs.append(job)
                else:
                    # Page returned error
                    self.mark_expired(url)
                    print(f"  ❌ Expired (HTTP {response.status if response else 'error'}): {job['title'][:50]}...")
                    
            except Exception as e:
                # Keep as unknown if we can't check
                active_jobs.append(job)
        
        print(f"  {len(active_jobs)} positions still active")
        return active_jobs


def is_phd_only(title):
    """
    STRICT filter - only returns True for explicit PhD positions.
    Excludes: PostDoc, Professor, Engineering jobs, generic pages
    """
    if not title or len(title) < 5:
        return False
    
    title_lower = title.lower()
    
    # ===== MUST EXCLUDE - Non-PhD positions =====
    exclude_keywords = [
        # PostDoc/Professor positions
        "postdoc", "post-doc", "post doc", "postdoctoral",
        "professor", "tenure", "faculty", "lecturer",
        "assistant professor", "associate professor", "full professor",
        "chair", "habilitation", "juniorprofessur",
        "w1", "w2", "w3",  # German professorship grades
        "senior researcher", "principal investigator",
        
        # Engineering/Industry jobs (NOT PhD)
        "senior engineer", "staff engineer", "lead engineer",
        "software engineer", "network engineer", "systems engineer",
        "data engineer", "devops", "developer", "programmer",
        "manager", "director", "head of", "chief",
        "technician", "techniker", "operator",
        "consultant", "analyst", "architect",
        "intern ", "internship", "praktikum", "werkstudent",
        
        # Generic/Admin positions
        "secretary", "administrative", "coordinator",
        "marketing", "sales", "hr ", "human resources",
        "accountant", "finance", "legal",
        
        # Generic university pages (not job postings)
        "welcome to", "about us", "contact us", "home page",
        "department of", "faculty of", "school of",
        "university of", "institute of",
        "news", "events", "calendar", "sitemap",
        "login", "register", "apply now", "more information",
        "read more", "click here", "learn more"
    ]
    
    for kw in exclude_keywords:
        if kw in title_lower:
            # Exception: if title explicitly mentions PhD alongside excluded term
            if "phd" in title_lower or "doktorand" in title_lower:
                # But still exclude if it's clearly not a PhD position
                if "postdoc" in title_lower or "professor" in title_lower:
                    return False
                return True
            return False
    
    # ===== MUST INCLUDE - Explicit PhD keywords =====
    phd_keywords = [
        "phd", "ph.d", "ph.d.",
        "doctoral", "doctorate",
        "doktorand", "doktorandin", "doktorarbeit",
        "promotionsstelle", "promotionsstudent",
        "dissertation",
        "research assistant (phd", "research assistant with phd",
        "(phd)", "- phd", "phd -", "phd:", ": phd",
        "wissenschaftlicher mitarbeiter (m/w/d) zur promotion",
        "wissenschaftliche mitarbeiterin zur promotion"
    ]
    
    for kw in phd_keywords:
        if kw in title_lower:
            return True
    
    # Check if "research assistant" with context suggesting PhD
    if "research assistant" in title_lower or "wissenschaftliche" in title_lower:
        # Only include if there's PhD context
        if any(ctx in title_lower for ctx in ["phd", "doctoral", "promot", "dissertation"]):
            return True
    
    # ===== DEFAULT: Return False (strict filtering) =====
    # If no explicit PhD keyword found, reject it
    return False


def is_postdoc_only(title):
    """
    STRICT filter - only returns True for PostDoc/Tenure Track/Professor positions.
    Excludes: PhD students, engineering jobs, generic pages
    """
    if not title or len(title) < 5:
        return False
    
    title_lower = title.lower()
    
    # ===== MUST EXCLUDE - Non-PostDoc positions =====
    exclude_keywords = [
        # PhD student positions (NOT PostDoc)
        "phd student", "phd position", "phd candidate",
        "doctoral student", "doctoral position",
        "doktorand", "doktorandin", "doktorarbeit",
        "promotionsstelle", "promotionsstudent",
        
        # Engineering/Industry jobs (NOT academic)
        "senior engineer", "staff engineer", "lead engineer",
        "software engineer", "network engineer", "systems engineer",
        "data engineer", "devops", "developer", "programmer",
        "manager", "director", "head of", "chief",
        "technician", "techniker", "operator",
        "consultant", "analyst", "architect",
        "intern ", "internship", "praktikum", "werkstudent",
        
        # Generic/Admin positions
        "secretary", "administrative", "coordinator",
        "marketing", "sales", "hr ", "human resources",
        "accountant", "finance", "legal",
        
        # Generic university pages (not job postings)
        "welcome to", "about us", "contact us", "home page",
        "department of", "faculty of", "school of",
        "university of", "institute of",
        "news", "events", "calendar", "sitemap",
        "login", "register", "apply now", "more information",
        "read more", "click here", "learn more"
    ]
    
    for kw in exclude_keywords:
        if kw in title_lower:
            # Exception: if title explicitly mentions postdoc alongside PhD term
            if any(pd in title_lower for pd in ["postdoc", "professor", "tenure", "faculty"]):
                return True
            return False
    
    # ===== MUST INCLUDE - Explicit PostDoc/Tenure keywords =====
    postdoc_keywords = [
        # PostDoc positions
        "postdoc", "post-doc", "post doc", "postdoctoral",
        "postdoctoral researcher", "postdoctoral fellow",
        "research fellow", "research associate",
        
        # Tenure Track / Professor positions
        "professor", "tenure", "tenure track", "tenure-track",
        "assistant professor", "associate professor", "full professor",
        "faculty", "faculty position", "lecturer", "senior lecturer",
        "juniorprofessur", "juniorprofessor",
        "w1", "w2", "w3",  # German professorship grades
        "chair", "endowed chair",
        "habilitation",
        "principal investigator", "pi position",
        "senior researcher", "senior scientist",
        "group leader", "research group leader"
    ]
    
    for kw in postdoc_keywords:
        if kw in title_lower:
            return True
    
    # Check for research positions that are likely postdoc level
    if "research" in title_lower and any(level in title_lower for level in ["senior", "fellow", "associate"]):
        return True
    
    # ===== DEFAULT: Return False (strict filtering) =====
    return False



class EmailSender:
    def __init__(self, sender_email, sender_password):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.template = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { text-align: left; padding: 10px; border-bottom: 1px solid #ddd; }
                th { background-color: #2196F3; color: white; }
                tr:hover { background-color: #f5f5f5; }
                .source { color: #666; font-size: 0.9em; }
                h2 { color: #333; }
                h3 { color: #2196F3; border-bottom: 2px solid #2196F3; padding-bottom: 5px; }
                .summary { background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .apply-btn { 
                    background-color: #4CAF50; 
                    color: white !important; 
                    padding: 8px 16px; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    display: inline-block;
                    font-weight: bold;
                }
                .apply-btn:hover { background-color: #45a049; }
                .contact-btn {
                    background-color: #FF9800;
                    color: white !important;
                    padding: 8px 16px;
                    text-decoration: none;
                    border-radius: 4px;
                    display: inline-block;
                    font-weight: bold;
                }
                .contact-btn:hover { background-color: #F57C00; }
                a { color: #2196F3; }
                .section-divider { 
                    margin: 30px 0; 
                    border-top: 3px solid #E0E0E0; 
                    padding-top: 20px;
                }
                .inquiry-badge {
                    background-color: #FF9800;
                    color: white;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 0.8em;
                    font-weight: bold;
                }
                .professor-table th { background-color: #9C27B0; }
            </style>
        </head>
        <body>
            <h2>🎓 PhD Search Report - {{ date }}</h2>
            
            <div class="summary">
                <strong>Summary:</strong> 
                {{ new_jobs|length }} new positions | 
                {{ old_jobs|length }} previously discovered (still active)
                {% if inquiry_positions %}
                | {{ inquiry_positions|length }} inquiry opportunities
                {% endif %}
                {% if professors %}
                | {{ professors|length }} professors in your field
                {% endif %}
            </div>
            
            <h3>🆕 Newly Discovered Positions</h3>
            {% if new_jobs %}
            <table>
                <tr>
                    <th>Title</th>
                    <th>University/Institute</th>
                    <th>Source</th>
                    <th>Link</th>
                </tr>
                {% for job in new_jobs %}
                <tr>
                    <td>{{ job.title[:100] }}{% if job.title|length > 100 %}...{% endif %}</td>
                    <td>{{ job.university }}</td>
                    <td class="source">{{ job.source }}</td>
                    <td>{% if job.url %}<a href="{{ job.url }}" class="apply-btn">Apply →</a>{% else %}No link{% endif %}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No new positions found today.</p>
            {% endif %}

            {% if inquiry_positions %}
            <div class="section-divider"></div>
            <h3>💡 Possible PhD/PostDoc Inquiry Positions</h3>
            <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                These professors/research groups have indicated openness to accepting new students on their webpages.
                <span class="inquiry-badge">INQUIRY OPPORTUNITY</span>
            </p>
            <table>
                <tr>
                    <th>Professor/Lab</th>
                    <th>University</th>
                    <th>Country</th>
                    <th>Research Areas</th>
                    <th>Contact</th>
                </tr>
                {% for inquiry in inquiry_positions %}
                <tr>
                    <td><strong>{{ inquiry.professor }}</strong></td>
                    <td>{{ inquiry.university }}</td>
                    <td>{{ inquiry.country }}</td>
                    <td>{{ inquiry.research_areas[:80] }}{% if inquiry.research_areas|length > 80 %}...{% endif %}</td>
                    <td>
                        {% if inquiry.url %}<a href="{{ inquiry.url }}" class="contact-btn">View Page →</a>{% endif %}
                        {% if inquiry.email and inquiry.email != 'N/A' %}<br><small>{{ inquiry.email }}</small>{% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}

            {% if professors %}
            <div class="section-divider"></div>
            <h3>👨‍🔬 Professors/Supervisors in Your Field</h3>
            <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                Faculty members whose research interests match your keywords. Consider reaching out to explore potential opportunities.
            </p>
            <table class="professor-table">
                <tr>
                    <th>Professor Name</th>
                    <th>University</th>
                    <th>Country</th>
                    <th>Research Areas</th>
                    <th>Webpage</th>
                </tr>
                {% for prof in professors %}
                <tr>
                    <td><strong>{{ prof.name }}</strong><br><small>{{ prof.title }}</small></td>
                    <td>{{ prof.university }}</td>
                    <td>{{ prof.country }}</td>
                    <td>{{ prof.research_areas[:100] }}{% if prof.research_areas|length > 100 %}...{% endif %}</td>
                    <td>
                        {% if prof.url %}<a href="{{ prof.url }}" target="_blank">Visit →</a>{% else %}N/A{% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}

            <div class="section-divider"></div>
            <h3>📂 Previously Discovered Open Positions (Still Active)</h3>
            {% if old_jobs %}
            <table>
                <tr>
                    <th>Title</th>
                    <th>University/Institute</th>
                    <th>Found Date</th>
                    <th>Source</th>
                    <th>Link</th>
                </tr>
                {% for job in old_jobs %}
                <tr>
                    <td>{{ job.title[:100] }}{% if job.title|length > 100 %}...{% endif %}</td>
                    <td>{{ job.university }}</td>
                    <td>{{ job.found_date }}</td>
                    <td class="source">{{ job.source }}</td>
                    <td>{% if job.url %}<a href="{{ job.url }}" class="apply-btn">Apply →</a>{% else %}No link{% endif %}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No previously discovered positions in database.</p>
            {% endif %}
            
            <p style="color: #999; font-size: 0.8em; margin-top: 30px;">
                Generated by PhD Headhunter Agent | Focus: Germany, Austria, Switzerland, Nordic, Netherlands, Poland, Czech, Hungary, Estonia
            </p>
        </body>
        </html>
        """

    def send_email(self, recipient_email, new_jobs, old_jobs, inquiry_positions=None, professors=None):
        today = datetime.now().strftime("%Y-%m-%d")
        
        t = Template(self.template)
        html_content = t.render(
            date=today, 
            new_jobs=new_jobs, 
            old_jobs=old_jobs,
            inquiry_positions=inquiry_positions or [],
            professors=professors or []
        )

        # Updated subject line to reflect content
        subject_parts = [f"{len(new_jobs)} new positions"]
        if inquiry_positions:
            subject_parts.append(f"{len(inquiry_positions)} inquiries")
        if professors:
            subject_parts.append(f"{len(professors)} professors")
        
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = recipient_email
        msg["Subject"] = f"🎓 PhD Search Report - {today} ({', '.join(subject_parts)})"
        
        msg.attach(MIMEText(html_content, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")
