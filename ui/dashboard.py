"""
Streamlit Dashboard for the HR Multi-Agent Recruitment System.

Provides a visual interface to:
- View pipeline progress with stage-level status
- Manage job postings and candidates
- Review interviews, feedback, rankings, and decisions
- Compare top candidates side-by-side
- Export data as CSV
- Start new pipelines
"""

import io

import pandas as pd
import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db import init_db, get_session
from database.models import (
    JobPosting, Candidate, Application, Interview,
    Feedback, Ranking, Offer
)

# --- Page Config ---
st.set_page_config(
    page_title="HR Multi-Agent System",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom Styling ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .stage-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-green { background: #d4edda; color: #155724; }
    .badge-blue { background: #cce5ff; color: #004085; }
    .badge-yellow { background: #fff3cd; color: #856404; }
    .badge-red { background: #f8d7da; color: #721c24; }
    .badge-grey { background: #e2e3e5; color: #383d41; }

    /* Stage progress bar */
    .stage-progress {
        display: flex;
        gap: 8px;
        margin: 1rem 0;
    }
    .stage-pill {
        flex: 1;
        text-align: center;
        padding: 10px 8px;
        border-radius: 10px;
        font-size: 0.8rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stage-done { background: #28a745; color: white; }
    .stage-pending { background: #e9ecef; color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# Initialize database
init_db()


# --- Helper: detect completed stages from DB ---
def _get_completed_stages() -> set[str]:
    """Inspect the database to determine which pipeline stages have data."""
    completed = set()
    with get_session() as session:
        if session.query(JobPosting).count() > 0:
            completed.add("job_posting")
        if session.query(Application).filter(Application.screening_score.isnot(None)).count() > 0:
            completed.add("resume_selection")
        if session.query(Interview).count() > 0:
            completed.add("interview_scheduling")
        if session.query(Feedback).count() > 0:
            completed.add("feedback_collection")
        if session.query(Ranking).count() > 0:
            completed.add("candidate_ranking")
        if session.query(Offer).count() > 0:
            completed.add("final_selection")
    return completed


def _render_pipeline_progress():
    """Render a coloured stage-progress bar based on DB state."""
    completed = _get_completed_stages()
    stages = [
        ("📋 Job Posting", "job_posting"),
        ("📄 Resume Screening", "resume_selection"),
        ("📅 Interviews", "interview_scheduling"),
        ("💬 Feedback", "feedback_collection"),
        ("🏆 Ranking", "candidate_ranking"),
        ("✅ Selection", "final_selection"),
    ]
    pills_html = ""
    for label, key in stages:
        css_class = "stage-done" if key in completed else "stage-pending"
        pills_html += f'<div class="stage-pill {css_class}">{label}</div>'

    st.markdown(f'<div class="stage-progress">{pills_html}</div>', unsafe_allow_html=True)


# --- Helper: dataframe → CSV download button ---
def _csv_download(df: pd.DataFrame, filename: str, label: str = "📥 Download CSV"):
    """Render a download button for a DataFrame."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(label=label, data=csv_bytes, file_name=filename, mime="text/csv")


# --- Sidebar ---
st.sidebar.markdown("## 🏢 HR Agent System")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📋 Job Postings", "👥 Candidates",
     "📅 Interviews", "💬 Feedback", "🏆 Rankings",
     "✅ Decisions", "📈 Compare Candidates", "🚀 Run Pipeline"],
    index=0,
)


# ======================================================================
# DASHBOARD
# ======================================================================
if page == "📊 Dashboard":
    st.markdown('<div class="main-header">HR Recruitment Dashboard</div>', unsafe_allow_html=True)
    st.markdown("Multi-agent pipeline powered by LangGraph")

    with get_session() as session:
        jobs_count = session.query(JobPosting).count()
        candidates_count = session.query(Candidate).count()
        interviews_count = session.query(Interview).count()
        offers_count = session.query(Offer).filter(Offer.decision == "offer").count()
        rejections_count = session.query(Offer).filter(Offer.decision == "reject").count()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📋 Job Postings", jobs_count)
    col2.metric("👥 Candidates", candidates_count)
    col3.metric("📅 Interviews", interviews_count)
    col4.metric("✅ Offers Made", offers_count)
    col5.metric("❌ Rejections", rejections_count)

    st.divider()

    # Pipeline stages visualization
    st.subheader("🔄 Pipeline Progress")
    _render_pipeline_progress()

    st.divider()

    # Recent activity
    st.subheader("📝 Recent Activity")
    with get_session() as session:
        recent_offers = session.query(Offer).order_by(Offer.created_at.desc()).limit(5).all()
        if recent_offers:
            for offer in recent_offers:
                decision_emoji = "✅" if offer.decision == "offer" else "❌" if offer.decision == "reject" else "⏳"
                st.markdown(
                    f"{decision_emoji} **{offer.candidate.name if offer.candidate else 'Unknown'}** — "
                    f"{offer.decision.upper()} for {offer.job_posting.title if offer.job_posting else 'Unknown'}"
                )
        else:
            st.info("No pipeline results yet. Run a pipeline to see activity here!")


# ======================================================================
# JOB POSTINGS
# ======================================================================
elif page == "📋 Job Postings":
    st.header("📋 Job Postings")

    with get_session() as session:
        postings = session.query(JobPosting).order_by(JobPosting.created_at.desc()).all()

        if postings:
            for posting in postings:
                with st.expander(f"**{posting.title}** — {posting.department} ({posting.status})", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Location:** {posting.location}")
                        st.markdown(f"**Type:** {posting.employment_type}")
                        st.markdown(f"**Salary:** {posting.salary_range}")
                    with col2:
                        st.markdown(f"**Status:** {posting.status}")
                        st.markdown(f"**Created:** {posting.created_at}")

                    st.markdown("---")
                    st.markdown("**Description:**")
                    st.markdown(posting.description)
                    st.markdown("**Requirements:**")
                    st.markdown(posting.requirements)
                    if posting.preferred_qualifications:
                        st.markdown("**Preferred Qualifications:**")
                        st.markdown(posting.preferred_qualifications)
        else:
            st.info("No job postings yet. Run the pipeline to create one!")


# ======================================================================
# CANDIDATES
# ======================================================================
elif page == "👥 Candidates":
    st.header("👥 Candidates")

    with get_session() as session:
        candidates = session.query(Candidate).order_by(Candidate.created_at.desc()).all()

        if candidates:
            # Summary table
            data = []
            for c in candidates:
                status_emoji = {
                    "applied": "📝", "shortlisted": "⭐", "interviewing": "🎤",
                    "ranked": "📊", "selected": "✅", "rejected": "❌"
                }.get(c.status, "❓")
                data.append({
                    "Name": c.name,
                    "Email": c.email,
                    "Skills": c.skills or "N/A",
                    "Experience": f"{c.experience_years} yrs" if c.experience_years else "N/A",
                    "Status": f"{status_emoji} {c.status}",
                })

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            _csv_download(df, "candidates.csv")

            # Detailed view
            st.subheader("Candidate Details")
            for c in candidates:
                with st.expander(f"**{c.name}** ({c.email}) — {c.status}"):
                    st.markdown(f"**Skills:** {c.skills or 'Not specified'}")
                    st.markdown(f"**Experience:** {c.experience_years or 'N/A'} years")
                    st.markdown(f"**Education:** {c.education or 'N/A'}")
                    st.markdown("**Resume:**")
                    st.text(c.resume_text[:500] + ("..." if len(c.resume_text) > 500 else ""))
        else:
            st.info("No candidates yet.")


# ======================================================================
# INTERVIEWS
# ======================================================================
elif page == "📅 Interviews":
    st.header("📅 Scheduled Interviews")

    with get_session() as session:
        interviews = session.query(Interview).order_by(Interview.scheduled_time).all()

        if interviews:
            data = []
            for i in interviews:
                status_color = {"scheduled": "🟡", "completed": "🟢", "cancelled": "🔴"}.get(i.status, "⚪")
                data.append({
                    "Candidate": i.candidate.name if i.candidate else "Unknown",
                    "Interviewer": i.interviewer_name,
                    "Type": i.interview_type,
                    "Time": str(i.scheduled_time),
                    "Duration": f"{i.duration_minutes} min",
                    "Status": f"{status_color} {i.status}",
                })

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            _csv_download(df, "interviews.csv")
        else:
            st.info("No interviews scheduled yet.")


# ======================================================================
# FEEDBACK
# ======================================================================
elif page == "💬 Feedback":
    st.header("💬 Interview Feedback")

    with get_session() as session:
        all_feedback = session.query(Feedback).order_by(Feedback.submitted_at.desc()).all()

        if all_feedback:
            for fb in all_feedback:
                interview = fb.interview
                candidate_name = interview.candidate.name if interview and interview.candidate else "Unknown"

                rec_color = {
                    "strong_hire": "🟢", "hire": "🟡",
                    "maybe": "🟠", "no_hire": "🔴"
                }.get(fb.recommendation, "⚪")

                with st.expander(
                    f"{rec_color} **{candidate_name}** — {fb.recommendation} "
                    f"(Rating: {fb.overall_rating}/10) by {fb.interviewer_name}"
                ):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Technical", f"{fb.technical_rating}/10" if fb.technical_rating else "N/A")
                    col2.metric("Communication", f"{fb.communication_rating}/10" if fb.communication_rating else "N/A")
                    col3.metric("Culture Fit", f"{fb.culture_fit_rating}/10" if fb.culture_fit_rating else "N/A")

                    if fb.strengths:
                        st.markdown(f"**Strengths:** {fb.strengths}")
                    if fb.weaknesses:
                        st.markdown(f"**Weaknesses:** {fb.weaknesses}")
                    if fb.detailed_notes:
                        st.markdown(f"**Notes:** {fb.detailed_notes}")
        else:
            st.info("No feedback submitted yet.")


# ======================================================================
# RANKINGS
# ======================================================================
elif page == "🏆 Rankings":
    st.header("🏆 Candidate Rankings")

    with get_session() as session:
        rankings = session.query(Ranking).order_by(Ranking.rank).all()

        if rankings:
            data = []
            for r in rankings:
                candidate_name = "Unknown"
                if r.application and r.application.candidate:
                    candidate_name = r.application.candidate.name

                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(r.rank, f"#{r.rank}")

                data.append({
                    "Rank": medal,
                    "Candidate": candidate_name,
                    "Resume Score": f"{r.resume_score:.1f}/10" if r.resume_score else "N/A",
                    "Interview Score": f"{r.interview_score:.1f}/10" if r.interview_score else "N/A",
                    "Overall Score": f"{r.overall_score:.1f}/10" if r.overall_score else "N/A",
                })

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            _csv_download(df, "rankings.csv")

            # Detailed analysis
            st.subheader("Detailed Analysis")
            for r in rankings:
                candidate_name = r.application.candidate.name if r.application and r.application.candidate else "Unknown"
                with st.expander(f"Rank #{r.rank} — {candidate_name} (Score: {r.overall_score:.1f})"):
                    if r.analysis:
                        st.markdown(r.analysis)
                    if r.score_breakdown:
                        st.json(r.score_breakdown)
        else:
            st.info("No rankings computed yet.")


# ======================================================================
# DECISIONS
# ======================================================================
elif page == "✅ Decisions":
    st.header("✅ Final Decisions")

    with get_session() as session:
        decisions = session.query(Offer).order_by(Offer.created_at.desc()).all()

        if decisions:
            # Summary metrics
            offers = [d for d in decisions if d.decision == "offer"]
            rejects = [d for d in decisions if d.decision == "reject"]
            waitlist = [d for d in decisions if d.decision == "waitlist"]

            col1, col2, col3 = st.columns(3)
            col1.metric("✅ Offers", len(offers))
            col2.metric("❌ Rejections", len(rejects))
            col3.metric("⏳ Waitlisted", len(waitlist))

            st.divider()

            # Export
            dec_data = []
            for d in decisions:
                dec_data.append({
                    "Candidate": d.candidate.name if d.candidate else "Unknown",
                    "Job": d.job_posting.title if d.job_posting else "Unknown",
                    "Decision": d.decision.upper(),
                    "Salary Offered": d.salary_offered or "—",
                    "Justification": (d.justification or "")[:120],
                })
            dec_df = pd.DataFrame(dec_data)
            _csv_download(dec_df, "decisions.csv")

            for d in decisions:
                emoji = {"offer": "✅", "reject": "❌", "waitlist": "⏳"}.get(d.decision, "❓")
                candidate_name = d.candidate.name if d.candidate else "Unknown"
                job_title = d.job_posting.title if d.job_posting else "Unknown"

                with st.expander(f"{emoji} **{candidate_name}** — {d.decision.upper()} for {job_title}"):
                    if d.salary_offered:
                        st.markdown(f"**Salary Offered:** {d.salary_offered}")
                    if d.justification:
                        st.markdown(f"**Justification:** {d.justification}")
                    if d.offer_letter_summary:
                        st.markdown(f"**Offer Summary:** {d.offer_letter_summary}")
        else:
            st.info("No decisions made yet.")


# ======================================================================
# COMPARE CANDIDATES  (NEW)
# ======================================================================
elif page == "📈 Compare Candidates":
    st.header("📈 Candidate Comparison")
    st.markdown("Side-by-side comparison of ranked candidates.")

    with get_session() as session:
        rankings = session.query(Ranking).order_by(Ranking.rank).all()

        if rankings:
            # Build comparison data
            names = []
            resume_scores = []
            interview_scores = []
            overall_scores = []

            for r in rankings:
                name = r.application.candidate.name if r.application and r.application.candidate else "Unknown"
                names.append(name)
                resume_scores.append(r.resume_score or 0)
                interview_scores.append(r.interview_score or 0)
                overall_scores.append(r.overall_score or 0)

            # Bar chart comparison
            chart_df = pd.DataFrame({
                "Resume Score": resume_scores,
                "Interview Score": interview_scores,
                "Overall Score": overall_scores,
            }, index=names)

            st.bar_chart(chart_df, height=400)

            st.divider()

            # Side-by-side detail cards (top 3)
            top_n = min(3, len(rankings))
            st.subheader(f"Top {top_n} Candidates — Detail Comparison")
            cols = st.columns(top_n)
            for idx, r in enumerate(rankings[:top_n]):
                with cols[idx]:
                    name = r.application.candidate.name if r.application and r.application.candidate else "Unknown"
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(r.rank, f"#{r.rank}")
                    st.markdown(f"### {medal} {name}")
                    st.metric("Overall", f"{r.overall_score:.1f}/10")
                    st.metric("Resume", f"{r.resume_score:.1f}/10" if r.resume_score else "N/A")
                    st.metric("Interview", f"{r.interview_score:.1f}/10" if r.interview_score else "N/A")
                    if r.analysis:
                        st.markdown("**Analysis:**")
                        st.caption(r.analysis[:300] + ("..." if len(r.analysis) > 300 else ""))
        else:
            st.info("No rankings available yet. Run the pipeline first.")


# ======================================================================
# RUN PIPELINE
# ======================================================================
elif page == "🚀 Run Pipeline":
    st.header("🚀 Run HR Pipeline")
    st.markdown("Start a new automated hiring pipeline.")

    with st.form("pipeline_form"):
        job_title = st.text_input("Job Title", value="Senior Software Engineer")
        department = st.text_input("Department", value="Engineering")
        requirements = st.text_area(
            "Requirements",
            value="5+ years Python experience, REST APIs, cloud services (AWS/GCP), "
                  "SQL databases, team leadership, strong communication skills",
            height=100,
        )

        st.subheader("📝 Candidates")
        st.markdown("Add candidate resumes (one per section):")

        num_candidates = st.number_input("Number of candidates", min_value=1, max_value=10, value=3)

        candidates = []
        for i in range(int(num_candidates)):
            st.markdown(f"---\n**Candidate {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(f"Name", key=f"name_{i}", value=f"Candidate {i+1}")
                email = st.text_input(f"Email", key=f"email_{i}", value=f"candidate{i+1}@email.com")
            with col2:
                skills = st.text_input(f"Skills", key=f"skills_{i}", value="Python, AWS, SQL")
                exp = st.number_input(f"Years Experience", key=f"exp_{i}", value=5, min_value=0)

            resume = st.text_area(
                f"Resume Text",
                key=f"resume_{i}",
                value=f"Experienced software engineer with {5+i} years in Python development...",
                height=80,
            )

            candidates.append({
                "name": name,
                "email": email,
                "resume_text": resume,
                "skills": skills,
                "experience_years": exp,
            })

        submitted = st.form_submit_button("🚀 Start Pipeline", use_container_width=True)

        if submitted:
            if not job_title or not requirements:
                st.error("Please fill in the job title and requirements.")
            else:
                st.info("🔄 Starting pipeline... This may take a few minutes.")

                try:
                    from config.settings import settings
                    settings.validate()

                    from langchain_core.messages import HumanMessage
                    from graph.pipeline import build_pipeline

                    # Add candidates to DB
                    with get_session() as session:
                        for c_data in candidates:
                            existing = session.query(Candidate).filter(
                                Candidate.email == c_data["email"]
                            ).first()
                            if not existing:
                                c = Candidate(
                                    name=c_data["name"],
                                    email=c_data["email"],
                                    resume_text=c_data["resume_text"],
                                    skills=c_data.get("skills", ""),
                                    experience_years=c_data.get("experience_years", 0),
                                )
                                session.add(c)

                    # Build candidate info string
                    candidate_info = "\n\nCandidates to evaluate:\n"
                    for c in candidates:
                        candidate_info += (
                            f"- {c['name']} ({c['email']}): "
                            f"Skills: {c.get('skills', 'N/A')}, "
                            f"Experience: {c.get('experience_years', 'N/A')} years. "
                            f"Resume: {c['resume_text'][:300]}\n"
                        )

                    pipeline = build_pipeline()

                    initial_state = {
                        "messages": [
                            HumanMessage(content=f"""
Start the HR recruitment pipeline:

Job Title: {job_title}
Department: {department}
Requirements: {requirements}
{candidate_info}

Proceed through all 6 stages of the pipeline.
""")
                        ],
                        "current_stage": "start",
                        "next_agent": "",
                        "pipeline_status": "running",
                        "error_message": None,
                        "retry_count": 0,
                        "max_retries": settings.AGENT_MAX_RETRIES,
                        "failed_stages": [],
                        "job_posting_id": None,
                        "job_posting": None,
                        "candidates": candidates,
                        "shortlisted_candidates": [],
                        "scheduled_interviews": [],
                        "interview_feedback": [],
                        "candidate_rankings": [],
                        "final_decisions": [],
                        "stage_metrics": [],
                    }

                    with st.spinner("Running pipeline through all 6 agents..."):
                        result = pipeline.invoke(initial_state)

                    st.success("✅ Pipeline completed successfully!")
                    st.balloons()

                    # Show stage metrics
                    metrics = result.get("stage_metrics", [])
                    if metrics:
                        st.subheader("⏱️ Stage Performance")
                        metrics_df = pd.DataFrame(metrics)
                        st.dataframe(metrics_df, use_container_width=True)

                    failed = result.get("failed_stages", [])
                    if failed:
                        st.warning(f"⚠️ Some stages failed: {', '.join(failed)}")

                    st.markdown("Navigate to other tabs to see the results.")

                except ValueError as e:
                    st.error(f"Configuration Error: {str(e)}")
                except Exception as e:
                    st.error(f"Pipeline Error: {str(e)}")
                    st.exception(e)


# --- Footer ---
st.sidebar.divider()
st.sidebar.caption("Built with LangGraph + Streamlit")
st.sidebar.caption("Multi-Agent HR Recruitment System v2.0")
