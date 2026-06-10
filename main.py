"""
HR Multi-Agent Recruitment System — Main Entry Point

Usage:
    python main.py run     — Run a full pipeline demo with sample data
    python main.py api     — Start the FastAPI server
    python main.py ui      — Launch Streamlit dashboard
    python main.py init    — Initialize the database only
"""

import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_demo():
    """Run a complete pipeline demo with sample data."""
    from config.settings import settings
    settings.validate()

    from database.db import init_db
    from langchain_core.messages import HumanMessage
    from graph.pipeline import build_pipeline

    print("=" * 70)
    print("HR Multi-Agent Recruitment System - Demo Pipeline")
    print("=" * 70)

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
                print(f"  [+] Added candidate: {c_data['name']}")

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
        "job_posting_id": None,
        "job_posting": None,
        "candidates": sample_candidates,
        "shortlisted_candidates": [],
        "scheduled_interviews": [],
        "interview_feedback": [],
        "candidate_rankings": [],
        "final_decisions": [],
    }

    print("\n>> Starting pipeline execution...\n")

    # Run the pipeline
    try:
        result = pipeline.invoke(initial_state)

        print("\n" + "=" * 70)
        print("[OK] PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nFinal status: {result.get('pipeline_status', 'unknown')}")
        print(f"Total messages exchanged: {len(result.get('messages', []))}")

        # Print summary from database
        from database.models import JobPosting, Application, Offer, Ranking

        with get_session() as session:
            jobs = session.query(JobPosting).all()
            print(f"\n[JOBS] Job Postings: {len(jobs)}")
            for j in jobs:
                print(f"   - {j.title} ({j.status})")

            apps = session.query(Application).all()
            shortlisted = [a for a in apps if a.is_shortlisted]
            print(f"\n[APPS] Applications: {len(apps)} total, {len(shortlisted)} shortlisted")

            from database.models import Interview as InterviewModel
            interviews = session.query(InterviewModel).all()
            print(f"\n[INTERVIEWS] Interviews: {len(interviews)}")

            from database.models import Feedback as FeedbackModel
            feedback = session.query(FeedbackModel).all()
            print(f"\n[FEEDBACK] Feedback: {len(feedback)} submissions")

            rankings = session.query(Ranking).order_by(Ranking.rank).all()
            print(f"\n[RANKINGS] Rankings:")
            for r in rankings:
                name = r.application.candidate.name if r.application and r.application.candidate else "Unknown"
                print(f"   #{r.rank}: {name} - Score: {r.overall_score:.1f}/10")

            offers = session.query(Offer).all()
            print(f"\n[DECISIONS] Decisions:")
            for o in offers:
                name = o.candidate.name if o.candidate else "Unknown"
                marker = "[OFFER]" if o.decision == "offer" else "[REJECT]" if o.decision == "reject" else "[WAIT]"
                print(f"   {marker} {name}: {o.decision.upper()}")
                if o.justification:
                    print(f"      Reason: {o.justification[:100]}...")

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
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
    print("Database initialized. Tables created.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable commands: run, api, ui, init")
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "run":
        run_demo()
    elif command == "api":
        run_api()
    elif command == "ui":
        run_ui()
    elif command == "init":
        init_database()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: run, api, ui, init")
        sys.exit(1)


if __name__ == "__main__":
    main()
