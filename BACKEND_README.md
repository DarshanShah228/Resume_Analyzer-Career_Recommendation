# Resume Analyzer & Career Recommendation — Backend

This is the completed Flask backend for the project. It plugs into the
existing frontend templates (auth pages were also fixed since they were
not actually calling the backend at all — see "What was broken" below).

## 1. Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

python app.py                   # runs on http://127.0.0.1:5000
```

The SQLite database (`instance/resume_analyzer.db`) and the upload folder
(`uploads/resumes/`) are created automatically on first run.

## 2. Project structure (backend)

```
app/
  __init__.py       Flask app factory (db, login, bcrypt, blueprints)
  models.py         SQLAlchemy models (unchanged, already correct)
  routes.py         Page routes + auth (login/signup/logout) — bug fixed
  api_routes.py     NEW — JSON API used by the frontend's fetch() calls
  analyzer.py       NEW — resume text -> skills/score extraction engine
  recommender.py    NEW — role matching, skill-gap, JD compare, bullet AI
  utils.py          NEW — file validation, text extraction, JSON loaders
data/
  skills.json           master skills taxonomy (used for extraction)
  job_roles.json         target roles + their required skills
  recommendations.json   per-skill learning tips + bullet-enhancer rules
config.py           Central config (paths, upload limits, secret key)
```

## 3. What was actually broken before

1. **Login & signup didn't call Flask at all.** The `<form>` tags had no
   `method`/`action`, and inline JS did `e.preventDefault()` and checked
   a fake `localStorage` user list. Fixed: forms now `POST` normally to
   `main.login` / `main.signup`, and the JS demo logic was removed.
2. **`signup()` had a logic bug** — the validation `flash()` calls had no
   `return`, so an invalid submission fell through and could still try
   to create a user. Fixed.
3. **`analyzer.py`, `recommender.py`, `utils.py` were empty** — there was
   no real resume parsing at all, only a fake `simulateResumeParsing()`
   in the frontend. Now implemented for real (see below).
4. Static reference data (`skills.json`, `job_roles.json`,
   `recommendations.json`) was empty — now populated.

## 4. How the analysis engine works (keyword/regex based, as requested)

`app/analyzer.py` (`ResumeAnalyzer`):
- Extracts skills by matching resume text against `data/skills.json`
  (case-insensitive, whole-word/phrase regex).
- Estimates experience from explicit "X years" mentions or the widest
  date range found (e.g. `2022 - 2024`).
- Detects education via a keyword list (B.Tech, MCA, Bachelor, etc).
- Computes 4 explainable sub-scores — **ATS Format**, **Skill
  Extraction**, **Impact**, **Keywords** — plus a weighted **overall
  score**, matching the metric cards already in `resume-analysis.html`.
- Produces short "Top Strengths" / "Areas for Improvement" text.

`app/recommender.py`:
- `match_all_roles()` — ranks all roles in `job_roles.json` by % of
  required skills the resume already has.
- `skill_gap_for_role()` — have/missing skills + a learning tip per
  missing skill, for one target role.
- `compare_resume_with_jd()` — extracts skills mentioned in a pasted
  job description and compares them to the resume.
- `generate_career_recommendations()` — top-N best-fit roles.
- `enhance_bullet_point()` — rule-based resume bullet rewriter (swaps
  weak verbs for strong ones, appends a plausible impact phrase if the
  original has no numbers). No external AI API required.

## 5. JSON API (`/api/...`, all `@login_required`)

| Method | Route                     | Purpose                                   |
|--------|---------------------------|--------------------------------------------|
| POST   | `/api/resume/upload`      | multipart `file` field → parses & scores  |
| GET    | `/api/resume/latest`      | latest resume + full analysis for the user|
| GET    | `/api/roles`              | list of target roles (for dropdowns)      |
| GET    | `/api/skill-gap?role_id=` | skill gap vs one role (defaults to best)  |
| GET    | `/api/career-recommendations` | top role recommendations              |
| POST   | `/api/compare-jd`         | `{target_job_title, job_description}`     |
| GET    | `/api/jd-results/latest`  | latest JD comparison result               |
| POST   | `/api/enhance-bullet`     | `{text}` → rewritten bullet point         |
| GET    | `/api/dashboard-summary`  | counts + latest score for the dashboard   |

All endpoints return JSON and use the existing Flask-Login session
cookie (`credentials: 'same-origin'` on the frontend) — no separate
token auth needed.

## 6. Frontend wiring (already started, safe to keep or redo)

Since you said you'll take over the frontend from here, note that I:
- Fixed `login.html` / `signup.html` to really hit the backend.
- Wrote `static/js/app.js` (toast notifications + `apiGet`/`apiPost`/
  `apiUpload` fetch helpers + a `renderSkillChips` helper) — these are
  generic and safe to keep no matter how you change the pages.
- Wired `upload-resume.html`, `skill-gap.html`, `compare-jd.html`,
  `jd-results.html`, `ai-suggestions.html`, `resume-analysis.html` to
  call the real API instead of the old fake demo data. You can restyle
  these freely — the `id="..."` hooks the JS looks for are documented
  inline in each `{% block scripts %}` section.

## 7. Notes / things you may want to adjust

- Max upload size is 5 MB (`config.py: MAX_CONTENT_LENGTH`).
- Allowed resume types: pdf, docx, doc, txt.
- Scoring weights and the skill/role/tips lists in `data/*.json` are
  easily editable without touching any Python code.
