
import re
import csv
import sqlite3
from io import StringIO
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document
from datetime import datetime
import time
DB_NAME = "job_applications.db"

def get_gemini_client():
    """Create a Gemini client without retrying quota-exhaustion (HTTP 429) errors."""
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to .streamlit/secrets.toml."
        )

    
    return genai.Client(
        api_key=api_key,
        http_options=genai.types.HttpOptions(
            timeout=30000,
            retry_options=genai.types.HttpRetryOptions(
                attempts=1,
                initial_delay=1.0,
                max_delay=3.0,
                exp_base=2.0,
                jitter=0.3,
                http_status_codes=[408, 500, 502, 503, 504],
            ),
        ),
    )



def show_gemini_error(error, feature_name):
    """Display a readable message without dumping a traceback into the page."""
    message = str(error)
    lowered = message.lower()

    if (
        "429" in message
        or "resource_exhausted" in lowered
        or "quota" in lowered
    ):
        st.warning(
            f"{feature_name}: Gemini API quota is exhausted or rate-limited. "
            "Wait for the quota to reset, or check your limits at "
            "https://ai.google.dev/gemini-api/docs/rate-limits."
        )
    elif "gemini_api_key" in lowered or "api key" in lowered:
        st.error(
            f"{feature_name}: Gemini API key is missing or invalid. "
            "Check .streamlit/secrets.toml without sharing the key."
        )
    else:
        st.error(f"{feature_name}: {type(error).__name__}: {error}")


def init_database():
    """Create the application tracker table if it does not already exist."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                job_title TEXT NOT NULL,
                location TEXT,
                job_url TEXT,
                application_date TEXT,
                status TEXT,
                follow_up_date TEXT,
                notes TEXT
            )
            """
        )


def load_applications():
    """Load saved applications from SQLite in display-friendly form."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT company, job_title, location, job_url,
                   application_date, status, follow_up_date, notes
            FROM job_applications
            ORDER BY id DESC
            """
        ).fetchall()

    return [
        {
            "Company": row["company"] or "",
            "Job Title": row["job_title"] or "",
            "Location": row["location"] or "",
            "Job URL": row["job_url"] or "",
            "Application Date": row["application_date"] or "",
            "Status": row["status"] or "",
            "Follow-up Date": row["follow_up_date"] or "",
            "Notes": row["notes"] or "",
        }
        for row in rows
    ]


init_database()


st.set_page_config(
    page_title="AI Job Search Assistant",
    page_icon="🎯",
    layout="wide",
)

SKILLS = [
    "Python", "Java", "SQL", "Django", "FastAPI",
    "Flask", "REST API", "PostgreSQL", "MySQL",
    "Machine Learning", "Deep Learning",
    "Generative AI", "LLM", "RAG", "LangChain",
    "Agentic AI", "NLP", "Pandas", "NumPy",
    "Scikit-learn", "AWS", "Docker", "Kubernetes",
    "Git", "React", "JavaScript", "HTML", "CSS",
    "Data Analysis", "Power BI", "Excel",
]


def extract_resume_text(uploaded_file):
    """Extract readable text from a PDF or Word resume."""
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    if filename.endswith(".docx"):
        document = Document(uploaded_file)
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    return ""


def extract_skills(text):
    """Find supported skills mentioned in text."""
    found = set()
    text_lower = text.lower()

    for skill in SKILLS:
        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(skill.lower())
            + r"(?![a-z0-9])"
        )

        if re.search(pattern, text_lower):
            found.add(skill)

    return found


st.title("🎯 AI Job Search Assistant")

st.write(
    "Upload your resume and paste a job description "
    "to discover matching skills, potential gaps, "
    "and AI-powered career recommendations."
)

st.caption(
    "Resume parsing, keyword analysis, and Gemini AI advice"
)

uploaded_file = st.file_uploader(
    "Upload your resume (PDF or DOCX)",
    type=["pdf", "docx"],
)

job_description = st.text_area(
    "Paste the job description",
    height=250,
    placeholder="Paste the complete job description here...",
)

if st.button("Analyze My Resume", type="primary"):

    if uploaded_file is None:
        st.warning("Please upload your resume.")

    elif not job_description.strip():
        st.warning("Please paste a job description.")

    else:
        try:
            resume_text = extract_resume_text(uploaded_file)

            if not resume_text.strip():
                st.error(
                    "No readable text was found. "
                    "Try a text-based PDF or DOCX file."
                )
                st.session_state.analysis = None

            else:
                st.session_state.analysis = {
                    "resume_text": resume_text,
                    "job_description": job_description,
                }

        except Exception as error:
            st.error(
                "Unable to read this file. Check that "
                "your PDF or DOCX resume is valid."
            )
            st.caption(str(error))
            st.session_state.analysis = None


analysis = st.session_state.get("analysis")

if analysis:
    resume_text = analysis["resume_text"]
    job_description = analysis["job_description"]

    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_description)

    matched_skills = resume_skills & job_skills
    missing_skills = job_skills - resume_skills

    score = (
        len(matched_skills) / len(job_skills) * 100
        if job_skills else 0
    )

    st.divider()
    st.header("📊 Analysis Results")

    col1, col2, col3 = st.columns(3)

    col1.metric("Skill Coverage", f"{score:.1f}%")
    col2.metric("Matched Skills", len(matched_skills))
    col3.metric("Potential Skill Gaps", len(missing_skills))

    st.progress(int(score))

    left, right = st.columns(2)

    with left:
        st.subheader("✅ Matched Skills")

        if matched_skills:
            for skill in sorted(matched_skills):
                st.write(f"• {skill}")
        else:
            st.write("No matching skills detected.")

    with right:
        st.subheader("📚 Skills to Review")

        if missing_skills:
            for skill in sorted(missing_skills):
                st.write(f"• {skill}")
        else:
            st.write(
                "No gaps detected in the supported skill list."
            )

    st.divider()
    st.subheader("💡 Recommendations")

    if missing_skills:
        st.write(
            "Review the job requirements for these skills. "
            "Learn them or demonstrate relevant experience "
            "where appropriate."
        )
    else:
        st.write(
            "Review the full job description to ensure your "
            "experience and achievements match the role."
        )

    st.info(
        "This is keyword-based skill coverage, not an ATS score "
        "or a hiring probability. A missing skill may be described "
        "differently in your resume."
    )

    st.divider()
    st.header("🤖 AI-Powered Career Advice")

    st.write(
        "Use Gemini to get job-specific feedback, practical "
        "improvement suggestions, and interview preparation."
    )

    if st.button("Generate AI Recommendations"):
        try:
            client = get_gemini_client()


            prompt = f"""
You are a practical career assistant.

Analyze the resume against the job description.

RESUME:
{resume_text[:12000]}

JOB DESCRIPTION:
{job_description[:8000]}

Provide:
1. Three strongest relevant qualifications supported by
   evidence in the resume.
2. Important job requirements that the resume does not
   clearly demonstrate.
3. Three practical improvements to tailor the resume.
4. Five relevant interview questions with concise example
   answer guidance based only on the candidate's evidence.
5. A short, realistic preparation plan.

Do not invent experience, qualifications, achievements,
or projects. Distinguish between missing evidence and
confirmed lack of a skill. Never recommend falsely adding
skills to a resume. Keep the answer clear and actionable.
"""

            with st.spinner(
                "Gemini is analyzing your resume and job description..."
            ):
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                )

            if response.text:
                st.session_state["ai_recommendations"] = response.text
                st.markdown(response.text)
            else:
                st.warning(
                    "Gemini returned an empty response. "
                    "Please try again."
                )

              
        except Exception as error:
            show_gemini_error(error, "AI career advice")

            
# FEATURE 1: Advanced Job Description Analyzer

st.divider()
st.header("🔎 Advanced Job Description Analyzer")

st.write(
    "Understand which requirements are essential, which are preferred, "
    "and how to prepare for the role."
)

if st.button("Analyze Job Requirements"):
    analysis = st.session_state.get("analysis")

    if not analysis:
        st.warning(
            "Please analyze your resume first using the "
            "'Analyze My Resume' button."
        )
    else:
        try:
            client = get_gemini_client()


            prompt = f"""
You are a careful technical recruiter and career coach.

Analyze this job description and the candidate's resume.

JOB DESCRIPTION:
{analysis["job_description"][:8000]}

RESUME:
{analysis["resume_text"][:12000]}

Return these sections:

1. REQUIRED SKILLS:
List skills and qualifications explicitly required by the job.
For each, explain whether the resume clearly demonstrates it.

2. PREFERRED SKILLS:
List preferred or nice-to-have skills separately.
Do not label a preferred skill as mandatory.

3. EXPERIENCE AND RESPONSIBILITIES:
Summarize the main responsibilities and identify relevant
evidence in the resume.

4. EVIDENCE GAPS:
Explain which requirements are not clearly demonstrated.
A missing mention is not proof that the candidate lacks the skill.

5. PRIORITY PLAN:
Suggest the five most useful next actions for preparing
for this role. Be specific and realistic.

Do not invent qualifications, projects, or work experience.
Use only evidence in the supplied resume.
"""

            with st.spinner(
                "Analyzing required and preferred job skills..."
            ):
                start_time = time.perf_counter()
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                )
                elapsed = time.perf_counter() - start_time
                st.caption(f"Gemini request time: {elapsed:.2f} seconds")

            if response.text:
                st.session_state["job_requirements_analysis"] = response.text
                st.markdown(response.text)
            else:
                st.warning(
                    "No analysis was returned. Please try again."
                )

        
        except Exception as error:
            show_gemini_error(error, "Job requirements analysis")

            
# FEATURE 2: Downloadable Analysis Report

st.divider()
st.header("📄 Download Your Analysis Report")

report_analysis = st.session_state.get("analysis")

if not report_analysis:
    st.info(
        "Analyze your resume and job description first "
        "to create a downloadable report."
    )
else:
    report_resume = report_analysis["resume_text"]
    report_jd = report_analysis["job_description"]

    report_resume_skills = extract_skills(report_resume)
    report_job_skills = extract_skills(report_jd)

    report_matched = report_resume_skills & report_job_skills
    report_missing = report_job_skills - report_resume_skills

    report_score = (
        len(report_matched) / len(report_job_skills) * 100
        if report_job_skills else 0
    )

    generated_at = datetime.now().strftime(
        "%d %B %Y, %I:%M %p"
    )

    matched_text = (
        "\n".join(f"- {skill}" for skill in sorted(report_matched))
        if report_matched else "- No matching skills detected."
    )

    missing_text = (
        "\n".join(f"- {skill}" for skill in sorted(report_missing))
        if report_missing else "- No gaps detected in the supported skill list."
    )

    ai_advice = st.session_state.get(
        "ai_recommendations",
        "AI career recommendations have not been generated yet."
    )

    jd_analysis = st.session_state.get(
        "job_requirements_analysis",
        "Advanced job-description analysis has not been generated yet."
    )

    report_content = f"""AI JOB SEARCH ASSISTANT
RESUME AND JOB DESCRIPTION ANALYSIS

Report generated: {generated_at}

1. SKILL COVERAGE
Keyword skill coverage: {report_score:.1f}%
Matched skills: {len(report_matched)}
Potential skill gaps: {len(report_missing)}

2. MATCHED SKILLS
{matched_text}

3. POTENTIAL SKILL GAPS
{missing_text}

4. AI-POWERED CAREER ADVICE
{ai_advice}

5. ADVANCED JOB DESCRIPTION ANALYSIS
{jd_analysis}

DISCLAIMER
This report provides keyword-based skill coverage and AI-generated
career guidance. It is not an official ATS score or a guarantee of
employment. A missing keyword does not prove that a candidate lacks
the corresponding skill. Review AI suggestions for accuracy.
"""

    st.write(
        "Download your skill analysis and any AI feedback "
        "generated during this session."
    )

    st.download_button(
        label="⬇️ Download Analysis Report",
        data=report_content,
        file_name="ai_job_search_analysis.txt",
        mime="text/plain",
    )
    
# FEATURE 3: Resume Improvement Assistant

st.divider()
st.header("✍️ Resume Improvement Assistant")

st.write(
    "Improve your resume for a specific job while keeping "
    "your skills, experience, and achievements truthful."
)

resume_data = st.session_state.get("analysis")

if not resume_data:
    st.info(
        "Please upload your resume and click Analyze My Resume "
        "before using this feature."
    )
else:
    original_resume = resume_data["resume_text"]
    target_jd = resume_data["job_description"]

    st.subheader("1. Review your current details")

    with st.expander("View extracted resume text"):
        st.text(original_resume[:10000])

    st.subheader("2. Choose what to improve")

    improvement_type = st.selectbox(
        "Select an improvement",
        [
            "Improve resume bullet points",
            "Rewrite my professional summary",
            "Identify weak points and suggest improvements",
            "Tailor my resume to the job description",
        ],
    )

    additional_context = st.text_area(
        "Optional: Add genuine achievements or project details",
        placeholder=(
            "Example: Built a Django application with user "
            "authentication and PostgreSQL integration."
        ),
    )

    if st.button(
        "✨ Improve My Resume",
        key="improve_resume_button",
    ):
        if not target_jd.strip():
            st.warning(
                "Please enter a job description in the "
                "Resume Analysis section first."
            )
        else:
            prompt = f"""
You are an experienced technical resume reviewer.

TASK:
{improvement_type}

JOB DESCRIPTION:
{target_jd[:12000]}

CURRENT RESUME:
{original_resume[:12000]}

ADDITIONAL INFORMATION PROVIDED BY THE CANDIDATE:
{additional_context[:3000]}

INSTRUCTIONS:
1. Tailor recommendations to the target job.
2. Use clear, concise, professional language.
3. Highlight relevant skills and projects already supported
   by the resume or additional information.
4. Never invent employers, job titles, years of experience,
   certifications, skills, project results, or metrics.
5. Do not claim the candidate has a skill unless the supplied
   information supports it.
6. If information is missing, identify what the candidate
   should verify or provide instead of making it up.
7. Preserve the candidate's actual education and experience.
8. Explain the most important changes and why they help.
9. Provide suggested resume wording that the candidate can
   review and edit before using.
10. Do not claim to calculate an official ATS score.

Return your response with these headings:
- Recommended Changes
- Improved Resume Wording
- Important Keywords to Consider
- Details the Candidate Should Verify
"""

            try:
                with st.spinner(
                    "Gemini is reviewing your resume..."
                ):
                    client = get_gemini_client()
                    response = client.models.generate_content(
                        model="gemini-3.5-flash",
                        contents=prompt,
                    )

                if response.text:
                    st.session_state[
                        "resume_improvement_result"
                    ] = response.text

                else:
                    st.warning(
                        "The AI returned an empty response. "
                        "Please try again."
                    )

            except Exception as e:
                show_gemini_error(e, "Resume improvement")

    improvement_result = st.session_state.get(
        "resume_improvement_result"
    )

    if improvement_result:
        st.subheader("3. Your Resume Improvements")
        st.markdown(improvement_result)

        st.download_button(
            label="⬇️ Download Resume Improvement Suggestions",
            data=improvement_result,
            file_name="resume_improvement_suggestions.txt",
            mime="text/plain",
            key="download_resume_improvements",
        )
        


# FEATURE: Interview Preparation Assistant

st.divider()
st.header("🎯 Interview Preparation Assistant")

st.write(
    "Generate interview questions and sample answers "
    "based on your resume and the job description."
)

interview_type = st.selectbox(
    "Choose interview type",
    [
        "Technical Interview",
        "HR Interview",
        "Project Discussion",
        "Mixed Mock Interview",
    ],
)

question_count = st.selectbox(
    "Number of questions",
    [5, 10, 15],
    index=0,
)

if st.button("Generate Interview Questions"):
    interview_data = st.session_state.get("analysis")

    if not interview_data:
        st.warning(
            "Please upload your resume, enter a job description, "
            "and click Analyze My Resume first."
        )
    else:
        try:
            client = get_gemini_client()

            interview_prompt = f"""
You are an experienced technical interviewer and career coach.

Prepare {question_count} interview questions for this candidate.

Interview type: {interview_type}

CANDIDATE RESUME:
{interview_data["resume_text"][:10000]}

JOB DESCRIPTION:
{interview_data["job_description"][:8000]}

Instructions:
1. Tailor questions to the resume and job description.
2. For each question, provide a clear sample answer.
3. For technical questions, explain the concepts accurately.
4. For project questions, use only projects mentioned in the resume.
5. For HR questions, keep answers natural and professional.
6. Never invent qualifications, achievements, or work experience.
7. Include useful tips for answering difficult questions.
"""

            with st.spinner(
                "Preparing your personalized interview..."
            ):
                interview_response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=interview_prompt,
                )

            if interview_response.text:
                st.session_state["interview_result"] = (
                    interview_response.text
                )
                st.markdown(interview_response.text)
            else:
                st.warning(
                    "No interview questions were returned. Please try again."
                )

        except Exception as error:
            show_gemini_error(error, "Interview preparation")

if st.session_state.get("interview_result"):
    st.download_button(
        label="⬇️ Download Interview Preparation",
        data=st.session_state["interview_result"],
        file_name="interview_preparation.txt",
        mime="text/plain",
    )

# JOB APPLICATION TRACKER

st.divider()
st.header("📋 Job Application Tracker")
st.write("Record applications and track your job-search progress.")

if "job_applications" not in st.session_state:
    st.session_state.job_applications = load_applications()

with st.form("job_application_form", clear_on_submit=True):
    st.subheader("Add a job application")

    company = st.text_input("Company name")
    job_title = st.text_input("Job title")

    job_location = st.selectbox(
        "Location",
        ["Bengaluru", "Hyderabad", "Remote", "Other"]
    )

    job_link = st.text_input("Job posting URL (optional)")

    application_date = st.date_input("Application date")

    status = st.selectbox(
        "Application status",
        [
            "Interested",
            "Applied",
            "Assessment",
            "Interview",
            "Offer",
            "Rejected",
            "Withdrawn"
        ]
    )

    follow_up_date = st.date_input("Follow-up date")

    notes = st.text_area("Notes (optional)")

    submitted = st.form_submit_button("➕ Add Application")

    
if submitted:
    if company.strip() and job_title.strip():
        application = {
            "Company": company.strip(),
            "Job Title": job_title.strip(),
            "Location": job_location,
            "Job URL": job_link.strip(),
            "Application Date": str(application_date),
            "Status": status,
            "Follow-up Date": str(follow_up_date),
            "Notes": notes.strip()
        }

        st.session_state.job_applications.append(application)
       
        
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                """
                INSERT INTO job_applications
                (company, job_title, location, job_url,
                 application_date, status, follow_up_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    application["Company"],
                    application["Job Title"],
                    application["Location"],
                    application["Job URL"],
                    application["Application Date"],
                    application["Status"],
                    application["Follow-up Date"],
                    application["Notes"]
                )
            )

        st.session_state.job_applications = load_applications()
        st.success("Application added and saved to database!")
    else:
        st.error("Please enter both company name and job title.")


st.subheader("Your applications")

applications = st.session_state.job_applications

if applications:
    st.metric("Total applications", len(applications))

    st.dataframe(applications, use_container_width=True)

    csv_buffer = StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=applications[0].keys()
    )
    writer.writeheader()
    writer.writerows(applications)

    st.download_button(
        "⬇️ Export applications to CSV",
        data=csv_buffer.getvalue(),
        file_name="job_applications.csv",
        mime="text/csv"
    )

    if st.button("🗑️ Clear all applications"):
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM job_applications")
        st.session_state.job_applications = []
        st.success("All applications were deleted.")
        st.rerun()
else:
    st.info("No applications yet. Add your first application above.")
