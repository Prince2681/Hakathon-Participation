# 🚀 CareerPilot AI
### AI-Powered Agentic Career Assistant

> An AI-powered career assistant that helps job seekers analyze resumes, evaluate job descriptions, identify skill gaps, optimize ATS scores, prepare for interviews, and manage job applications—all in one platform.

---

## Project Overview

CareerPilot AI is an Agentic AI platform developed for the **Gappy AI Hackathon 2026**.

The platform automates the job application workflow by combining Resume Analysis, Job Description Analysis, ATS Optimization, Skill Gap Detection, Interview Preparation, Market Intelligence, and Application Tracking into one interactive application.

Unlike traditional resume checkers, CareerPilot AI performs intelligent matching between a candidate's resume and a specific job description while providing actionable recommendations to improve employability.

---

# Problem Statement

Finding the right job is becoming increasingly difficult because candidates must:

- Tailor resumes for every application
- Understand ATS requirements
- Identify missing skills
- Prepare for interviews
- Track hundreds of applications
- Analyze market demand

CareerPilot AI automates these repetitive tasks using AI-powered agents.

---

# 💡 Solution

CareerPilot AI provides an end-to-end career assistance platform capable of:

✅ Resume Parsing

✅ Job Description Analysis

✅ ATS Resume Evaluation

✅ Skill Gap Analysis

✅ Resume Optimization

✅ Interview Preparation

✅ Career Market Intelligence

✅ Application Tracking

---

# Features

## Resume Analysis

- Upload PDF Resume
- Resume Skill Extraction
- Experience Detection
- Education Extraction
- Resume Score

---

## Job Description Analyzer

- Company Detection
- Role Detection
- Seniority Detection
- Required Skills
- ATS Keywords
- Key Responsibilities

---

## Resume Matching

- Resume Fit Score
- ATS Compatibility Score
- Matched Skills
- Missing Skills
- Skill Gap Analysis
- Resume Improvement Suggestions

---

## Market Intelligence

Analyze multiple job descriptions to discover:

- Most demanded skills
- Emerging technologies
- Learning roadmap
- Industry trends

---

## Interview Simulator

- AI-generated interview questions
- Interview evaluation
- Technical score
- Communication score
- Confidence score
- Personalized feedback

---

## Application Tracker

Track every application using:

- Application Status
- Interview Status
- Follow-up Date
- Notes
- Priority Level

---

# Tech Stack

| Category | Technology |
|----------|------------|
| Programming Language | Python |
| Frontend | Streamlit |
| Database | SQLite |
| AI Runtime | Lemma / Lemme / OpenAI |
| Data Processing | JSON |
| PDF Parsing | pdfplumber |

---

# 🏗️ Project Architecture

```text
                Resume PDF
                     │
                     ▼
            Resume Analysis Agent
                     │
                     ▼
             Candidate Profile
                     │
                     ▼
         Job Description Analyzer
                     │
                     ▼
          Resume Matching Agent
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
 ATS Optimization          Skill Gap Detection
        ▼                         ▼
 Interview Agent      Resume Optimizer Agent
        ▼                         ▼
      Database & Application Tracker
                     │
                     ▼
              Streamlit Dashboard
```

---

# 📂 Project Structure

```text
CareerPilot AI
│
├── app.py
├── agents.py
├── database.py
├── careerpilot.db
├── requirements.txt
├── README.md
│
├── logs/
│
├── pod/
│   ├── files/
│   ├── tables/
│   └── pod.md
│
└── screenshots/
```

---

# ⚙️ Installation

Clone the repository

```bash
git clone <repository-url>
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
streamlit run app.py
```
# Future Improvements

- Resume Version Management
- LinkedIn Profile Analysis
- AI Cover Letter Generator
- Salary Prediction
- Job Recommendation Engine
- Resume vs Multiple JDs Comparison
- Email Automation
- Calendar Integration
- Resume Ranking Dashboard
- Recruiter Analytics

---

# Learning Outcomes

This project demonstrates practical knowledge of:

- Agentic AI
- Resume Parsing
- ATS Optimization
- NLP Concepts
- Prompt Engineering
- Python Development
- Streamlit
- SQLite
- Workflow Automation
- Software Architecture

---

# 👨‍💻 Author

**Ankit Saini**

Data Scientist | Python | SQL | Power BI | Machine Learning
---

# ⭐ If you found this project useful

Please consider giving it a ⭐ on GitHub.
