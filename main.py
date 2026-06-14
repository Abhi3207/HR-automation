"""
HR Multi-Agent Recruitment System — Main Entry Point

Usage:
    python main.py run       — Run a full pipeline demo with sample data
    python main.py api       — Start the FastAPI server
    python main.py ui        — Launch Streamlit dashboard
    python main.py init      — Initialize the database only
    python main.py reset     — Drop and re-create all database tables
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def run_demo():
    """Run a complete pipeline demo with sample data."""
    from config.settings import settings
    settings.validate()

    from database.db import init_db
    from langchain_core.messages import HumanMessage
    from graph.pipeline import build_pipeline

    logger.info("=" * 70)
    logger.info("HR Multi-Agent Recruitment System - Demo Pipeline")
    logger.info("=" * 70)

    # Initialize database
    init_db()

    # Pre-seed candidates in the database
    from database.db import get_session
    from database.models import Candidate

    sample_candidates = [
        {
            "name": "Alice Chen",
            "email": "alice.chen@email.com",
            "resume_text": (
                "Senior Software Engineer with 7 years of experience in Python and cloud technologies. "
                "Led a team of 5 at TechCorp, building microservices on AWS. Expert in FastAPI, Django, "
                "PostgreSQL, Redis, and Docker. Published 3 papers on distributed systems. "
                "MSc Computer Science from Stanford University. Strong communicator who mentored "
                "5 junior engineers. Built a real-time analytics platform processing 10M events/day."
            ),
            "skills": "Python, AWS, FastAPI, Django, PostgreSQL, Docker, Kubernetes, Redis",
            "experience_years": 7,
            "education": "MSc Computer Science, Stanford University",
        },
        {
            "name": "Bob Martinez",
            "email": "bob.martinez@email.com",
            "resume_text": (
                "Full-stack developer with 4 years of experience. Proficient in Python and JavaScript. "
                "Worked at StartupXYZ building REST APIs with Flask. Experience with MySQL and MongoDB. "
                "BSc in Information Technology from State University. Basic knowledge of AWS services. "
                "Completed several online courses in machine learning. Good team player with "
                "experience in Agile/Scrum methodologies."
            ),
            "skills": "Python, JavaScript, Flask, MySQL, MongoDB, React",
            "experience_years": 4,
            "education": "BSc Information Technology, State University",
        },
        {
            "name": "Carol Davis",
            "email": "carol.davis@email.com",
            "resume_text": (
                "Software Engineer with 6 years specializing in backend systems and cloud architecture. "
                "Currently at MegaCorp as a Senior Backend Engineer. Deep expertise in Python, Go, "
                "and cloud-native development on GCP. Architected a payment processing system handling "
                "$50M annually. Strong background in system design and API development. "
                "MSc Software Engineering from MIT. Active open-source contributor with 2k+ GitHub stars. "
                "Speaker at PyCon 2024. Experience leading cross-functional teams."
            ),
            "skills": "Python, Go, GCP, Kubernetes, gRPC, PostgreSQL, System Design, CI/CD",
            "experience_years": 6,
            "education": "MSc Software Engineering, MIT",
        },
        {
            "name": "David Kim",
            "email": "david.kim@email.com",
            "resume_text": (
                "Junior developer with 2 years of experience. Learning Python and web development. "
                "Worked on a small internal tool at a local company using Django. "
                "BSc Computer Science from Community College. Completed a coding bootcamp. "
                "Familiar with HTML, CSS, JavaScript. Starting to learn about cloud services. "
                "Enthusiastic and eager to learn new technologies."
            ),
            "skills": "Python, Django, HTML, CSS, JavaScript, Git",
            "experience_years": 2,
            "education": "BSc Computer Science, Community College",
        },
    ]

    with get_session() as session:
        for c_data in sample_candidates:
            existing = session.query(Candidate).filter(
                Candidate.email == c_data["email"]
            ).first()
            if not existing:
                candidate = Candidate(
                    name=c_data["name"],
                    email=c_data["email"],
                    resume_text=c_data["resume_text"],
                    skills=c_data["skills"],
                    experience_years=c_data["experience_years"],
                    education=c_data["education"],
                )
                session.add(candidate)
                logger.info("  [+] Added candidate: %s", c_data["name"])

    # Build candidate info for the prompt
    candidate_info = "\n\nCandidates who have applied:\n"
    for c in sample_candidates:
        candidate_info += (
            f"\n- **{c['name']}** ({c['email']})\n"
            f"  Skills: {c['skills']}\n"
            f"  Experience: {c['experience_years']} years\n"
            f"  Education: {c['education']}\n"
            f"  Resume: {c['resume_text']}\n"
        )

    # Build the pipeline
    pipeline = build_pipeline()

    # Create initial state
    initial_state = {
        "messages": [
            HumanMessage(content=f"""
Start the HR recruitment pipeline for the following position:

Job Title: Senior Software Engineer
Department: Engineering
Requirements: 5+ years of Python experience, REST API development, cloud services
(AWS or GCP), SQL databases, containerization (Docker/Kubernetes), team leadership
experience, strong communication skills, CS degree preferred.
Salary Range: $130,000 - $180,000
Location: Remote (US)
{candidate_info}

Please proceed through all stages:
1. Create the job posting with a professional description
2. Screen all 4 candidates' resumes against the requirements and score them
3. Schedule interviews for shortlisted candidates
4. Collect interviewer feedback for each interview
5. Rank all evaluated candidates
6. Make final hiring decisions
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
        "candidates": sample_candidates,
        "shortlisted_candidates": [],
        "scheduled_interviews": [],
        "interview_feedback": [],
        "candidate_rankings": [],
        "final_decisions": [],
        "stage_metrics": [],
    }

    logger.info(">> Starting pipeline execution...")

    # Run the pipeline
    try:
        result = pipeline.invoke(initial_state)

        logger.info("=" * 70)
        logger.info("[OK] PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("=" * 70)
        logger.info("Final status: %s", result.get("pipeline_status", "unknown"))
        logger.info("Total messages exchanged: %d", len(result.get("messages", [])))

        # Log stage metrics
        stage_metrics = result.get("stage_metrics", [])
        if stage_metrics:
            logger.info("[METRICS] Per-stage performance:")
            for m in stage_metrics:
                logger.info(
                    "   %s — %.1fs | %s | %d tool calls",
                    m.get("stage", "?"), m.get("elapsed_seconds", 0),
                    m.get("status", "?"), m.get("tool_calls", 0),
                )

        failed = result.get("failed_stages", [])
        if failed:
            logger.warning("[WARNING] Failed stages: %s", ", ".join(failed))

        # Print summary from database
        from database.models import JobPosting, Application, Offer, Ranking

        with get_session() as session:
            jobs = session.query(JobPosting).all()
            logger.info("[JOBS] Job Postings: %d", len(jobs))
            for j in jobs:
                logger.info("   - %s (%s)", j.title, j.status)

            apps = session.query(Application).all()
            shortlisted = [a for a in apps if a.is_shortlisted]
            logger.info("[APPS] Applications: %d total, %d shortlisted", len(apps), len(shortlisted))

            from database.models import Interview as InterviewModel
            interviews = session.query(InterviewModel).all()
            logger.info("[INTERVIEWS] Interviews: %d", len(interviews))

            from database.models import Feedback as FeedbackModel
            feedback = session.query(FeedbackModel).all()
            logger.info("[FEEDBACK] Feedback: %d submissions", len(feedback))

            rankings = session.query(Ranking).order_by(Ranking.rank).all()
            logger.info("[RANKINGS] Rankings:")
            for r in rankings:
                name = r.application.candidate.name if r.application and r.application.candidate else "Unknown"
                logger.info("   #%d: %s - Score: %.1f/10", r.rank, name, r.overall_score)

            offers = session.query(Offer).all()
            logger.info("[DECISIONS] Decisions:")
            for o in offers:
                name = o.candidate.name if o.candidate else "Unknown"
                marker = "[OFFER]" if o.decision == "offer" else "[REJECT]" if o.decision == "reject" else "[WAIT]"
                logger.info("   %s %s: %s", marker, name, o.decision.upper())
                if o.justification:
                    logger.info("      Reason: %s...", o.justification[:100])

    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        sys.exit(1)


def run_api():
    """Start the FastAPI server."""
    from api.server import run_server
    run_server()


def run_ui():
    """Launch the Streamlit dashboard."""
    import subprocess
    dashboard_path = PROJECT_ROOT / "ui" / "dashboard.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.headless", "true",
    ])


def init_database():
    """Initialize the database tables."""
    from database.db import init_db
    init_db()
    logger.info("Database initialized. Tables created.")


def reset_database():
    """Drop all tables and re-create them."""
    from database.db import drop_db, init_db
    drop_db()
    init_db()
    logger.info("Database reset complete.")


def main():
    parser = argparse.ArgumentParser(
        prog="hr-multi-agent",
        description="HR Multi-Agent Recruitment System — powered by LangGraph",
    )
    parser.add_argument(
        "command",
        choices=["run", "api", "ui", "init", "reset"],
        help="Command to execute",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    # Apply verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    commands = {
        "run": run_demo,
        "api": run_api,
        "ui": run_ui,
        "init": init_database,
        "reset": reset_database,
    }

    commands[args.command]()


if __name__ == "__main__":
    main()
