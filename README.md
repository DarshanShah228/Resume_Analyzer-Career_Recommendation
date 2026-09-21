# 🚀 CareerAI - Resume Analyzer & Career Recommendation System

An intelligent, full-stack web application designed to analyze resumes, compute ATS (Applicant Tracking System) compatibility scores, identify skill gaps, compare resumes against Job Descriptions (JDs), and provide AI-driven career recommendations and bullet point enhancements.

---

## 👥 Group Project Members

1. **Abhay Shihora**
2. **Darshan Shah**
3. **Khushal Bamniya**

---

## ✨ Key Features

### 📄 Resume Parsing & ATS Scoring
- **Multi-Format Support**: Upload resumes in standard **PDF** (`.pdf`) and Word (`.docx`) formats.
- **Explainable Sub-Scores**: Calculates an overall ATS score along with 4 explainable sub-metrics:
  - 📐 **Format Score**: Verifies section layout, readability, and formatting.
  - 🛠️ **Skill Extraction Score**: Detects technical and soft skills against a taxonomy.
  - ⚡ **Impact Score**: Evaluates quantifiable achievements, action verbs, and metrics.
  - 🔑 **Keyword Match Score**: Evaluates keyword density and industry terminology.
- **Actionable Insights**: Automatically highlights top candidate strengths and specific areas for improvement.

### 🎯 Skill Gap Analysis & Learning Pathways
- **Role Target Selection**: Choose from various industry job roles (Software Engineer, Data Scientist, Full Stack Developer, DevOps Engineer, etc.).
- **Missing Skills Identification**: Displays matched skills vs. missing skills for the chosen role.
- **Learning Tips**: Provides tailored, actionable learning advice and resources for each missing skill.

### 🔄 Job Description (JD) Comparison
- **Direct JD Matching**: Paste any job description to compare it against your latest analyzed resume.
- **Match Percentage**: Generates a breakdown of matching skills, missing requirements, and overall alignment score.

### ✨ AI Bullet Point Enhancer
- **Resume Impact Boost**: Transform weak resume bullet points into strong, metric-driven statements using active verbs and quantifiable results.

### 👑 Comprehensive Admin Panel & Reports
- **User Management**: Search, promote/demote user roles (Admin vs. Candidate), and manage user accounts.
- **Real-Time Platform Analytics**: View registered user growth, uploaded resumes, analysis records, and JD comparisons.
- **Interactive Reports**: Chart.js data visualizations for score distributions, top missing skills, and popular career roles with one-click **PDF Export / Print**.

### 📱 Responsive Mobile-First Design
- **Cross-Device Support**: Fully optimized for Mobile, Tablet, and Desktop displays.
- **Offcanvas Drawer & Bottom Nav**: Mobile navigation drawer and fixed quick-action bottom navbar for small screens.

---

## 🛠️ Tech Stack

- **Backend Framework**: Python 3.11+, Flask 3.0.3
- **Database & ORM**: SQLite, Flask-SQLAlchemy 3.1.1
- **Security & Authentication**: Flask-Login 0.6.3, Flask-Bcrypt 1.0.1, python-dotenv
- **Document Processing**: PyPDF 4.3.1, python-docx 1.1.2
- **Frontend & Styling**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 4.6.2, Google Material Symbols
- **Data Visualization**: Chart.js 4.x

---

## 📂 Project Structure

```
Resume_Analyzer&Career_Recommendation/
├── app/
│   ├── __init__.py          # Flask app factory, extension init (DB, Login, Bcrypt)
│   ├── models.py            # SQLAlchemy database schemas (User, Resume, Analysis, etc.)
│   ├── routes.py            # Main application page & auth routes
│   ├── api_routes.py        # RESTful JSON API endpoints
│   ├── analyzer.py          # Resume parsing, skill extraction & ATS scoring engine
│   ├── recommender.py       # Career role matching, skill gap & JD compare logic
│   └── utils.py             # File validation & document text extractor helpers
├── data/
│   ├── skills.json          # Master skills taxonomy dictionary
│   ├── job_roles.json       # Industry target roles & required skill sets
│   └── recommendations.json # Skill learning tips & bullet enhancer rule definitions
├── static/
│   ├── css/
│   │   ├── styles.css        # Core stylesheet (Corporate Modernism & responsive rules)
│   │   └── admin_reports.css # Admin reports styling & print stylesheet
│   └── js/
│       ├── app.js           # Fetch API helpers, toast notifications, & core utilities
│       ├── auth.js          # Client-side form handlers
│       └── analyzer.js      # Interactive dashboard & analysis UI scripts
├── templates/
│   ├── base.html            # Base layout template for user panel
│   ├── index.html           # Landing page
│   ├── login.html           # User login page
│   ├── signup.html          # User registration page
│   ├── dashboard.html       # Candidate dashboard
│   ├── upload-resume.html   # Drag & drop resume uploader
│   ├── resume-analysis.html # Detailed ATS analysis view
│   ├── skill-gap.html       # Skill gap breakdown & learning pathways
│   ├── compare-jd.html      # Job description comparison page
│   ├── ai-suggestions.html  # AI bullet enhancer & tips page
│   └── admin/
│       ├── admin_base.html      # Base layout for admin portal
│       ├── admin.html           # User management portal
│       ├── admin_dashboard.html # Admin platform overview & activity feed
│       └── admin_reports.html   # Analytics dashboard with Chart.js charts
├── uploads/                 # Storage for uploaded candidate resumes
├── instance/                # Local SQLite database location (`resume_analyzer.db`)
├── .env                     # Environment variables configuration
├── config.py                # Application configuration settings
├── requirements.txt         # Python package dependencies
├── app.py                   # Application entry point
└── README.md                # Project documentation
```

---

## ⚙️ Installation & Local Setup

### 1. Prerequisites
- **Python 3.11** or higher installed on your system.
- **Git** (optional, for cloning).

### 2. Clone or Extract the Project
```bash
cd "Resume_Analyzer&Career_Recommendation"
```

### 3. Create & Activate Virtual Environment

**On Windows (PowerShell / Command Prompt):**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Create a `.env` file in the root directory (or use default development fallback):
```env
SECRET_KEY=your_secret_key_here
FLASK_ENV=development
```

### 6. Run the Application
```bash
python app.py
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

*(Note: The database tables and upload directories will be created automatically on the first launch.)*

---

## 📡 Key API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/resume/upload` | Upload and process resume file (`.pdf`/`.docx`) |
| `GET` | `/api/resume/latest` | Retrieve candidate's latest uploaded resume and analysis |
| `GET` | `/api/roles` | Fetch list of target industry career roles |
| `GET` | `/api/skill-gap?role_id=` | Retrieve skill gap analysis for a specific target role |
| `GET` | `/api/career-recommendations` | Get top recommended career paths based on extracted skills |
| `POST` | `/api/compare-jd` | Compare candidate resume against a job description |
| `POST` | `/api/enhance-bullet` | Enhance and format a resume bullet point |
| `GET` | `/api/dashboard-summary` | Retrieve metric counts and scores for user dashboard |
| `GET` | `/api/admin/dashboard` | (*Admin Only*) Retrieve platform-wide system statistics |

---

## 📜 License & Acknowledgments

Developed as a group project for **Resume Analysis & Career Recommendation**. Built with Python, Flask, Bootstrap, and open-source NLP keyword extraction techniques.
