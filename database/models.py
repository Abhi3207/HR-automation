"""
SQLAlchemy models for the HR Multi-Agent System.
Defines all database entities for the recruitment pipeline.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class JobPosting(Base):
    """A job posting created by the Job Posting Agent."""
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    department = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False)
    preferred_qualifications = Column(Text, nullable=True)
    salary_range = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    employment_type = Column(String(50), default="Full-time")
    status = Column(String(20), default="open")  # open, closed, filled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    applications = relationship("Application", back_populates="job_posting")
    offers = relationship("Offer", back_populates="job_posting")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "department": self.department,
            "description": self.description,
            "requirements": self.requirements,
            "preferred_qualifications": self.preferred_qualifications,
            "salary_range": self.salary_range,
            "location": self.location,
            "employment_type": self.employment_type,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Candidate(Base):
    """A candidate in the recruitment pipeline."""
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)
    resume_text = Column(Text, nullable=False)
    skills = Column(Text, nullable=True)  # Comma-separated skills
    experience_years = Column(Integer, nullable=True)
    education = Column(String(200), nullable=True)
    status = Column(String(30), default="applied")  # applied, shortlisted, interviewing, ranked, selected, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    applications = relationship("Application", back_populates="candidate")
    interviews = relationship("Interview", back_populates="candidate")
    offers = relationship("Offer", back_populates="candidate")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "resume_text": (self.resume_text[:200] + "...") if self.resume_text and len(self.resume_text) > 200 else (self.resume_text or ""),
            "skills": self.skills,
            "experience_years": self.experience_years,
            "education": self.education,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Application(Base):
    """Links a candidate to a job posting with screening results."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    screening_score = Column(Float, nullable=True)  # 0-100
    screening_notes = Column(Text, nullable=True)
    is_shortlisted = Column(Boolean, default=False)
    applied_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    candidate = relationship("Candidate", back_populates="applications")
    job_posting = relationship("JobPosting", back_populates="applications")
    rankings = relationship("Ranking", back_populates="application")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate.name if self.candidate else None,
            "job_posting_id": self.job_posting_id,
            "job_title": self.job_posting.title if self.job_posting else None,
            "screening_score": self.screening_score,
            "screening_notes": self.screening_notes,
            "is_shortlisted": self.is_shortlisted,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }


class Interview(Base):
    """An interview scheduled for a candidate."""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    interviewer_name = Column(String(200), nullable=False)
    interviewer_email = Column(String(200), nullable=True)
    interview_type = Column(String(50), default="technical")  # technical, behavioral, culture_fit
    scheduled_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    meeting_link = Column(String(500), nullable=True)
    status = Column(String(20), default="scheduled")  # scheduled, completed, cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")
    feedback = relationship("Feedback", back_populates="interview", uselist=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate.name if self.candidate else None,
            "interviewer_name": self.interviewer_name,
            "interview_type": self.interview_type,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "duration_minutes": self.duration_minutes,
            "status": self.status,
        }


class Feedback(Base):
    """Interviewer feedback for a completed interview."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, unique=True)
    interviewer_name = Column(String(200), nullable=False)
    technical_rating = Column(Integer, nullable=True)  # 1-10
    communication_rating = Column(Integer, nullable=True)  # 1-10
    culture_fit_rating = Column(Integer, nullable=True)  # 1-10
    overall_rating = Column(Float, nullable=False)  # 1-10
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    recommendation = Column(String(20), nullable=False)  # strong_hire, hire, maybe, no_hire
    detailed_notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    interview = relationship("Interview", back_populates="feedback")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "interview_id": self.interview_id,
            "interviewer_name": self.interviewer_name,
            "technical_rating": self.technical_rating,
            "communication_rating": self.communication_rating,
            "culture_fit_rating": self.culture_fit_rating,
            "overall_rating": self.overall_rating,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendation": self.recommendation,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }


class Ranking(Base):
    """Candidate ranking with composite scoring."""
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    resume_score = Column(Float, nullable=True)  # From screening
    interview_score = Column(Float, nullable=True)  # Average of feedback
    overall_score = Column(Float, nullable=False)  # Weighted composite
    rank = Column(Integer, nullable=True)
    score_breakdown = Column(JSON, nullable=True)  # Detailed scoring breakdown
    analysis = Column(Text, nullable=True)  # LLM-generated analysis
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application = relationship("Application", back_populates="rankings")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "resume_score": self.resume_score,
            "interview_score": self.interview_score,
            "overall_score": self.overall_score,
            "rank": self.rank,
            "score_breakdown": self.score_breakdown,
            "analysis": self.analysis,
        }


class Offer(Base):
    """Final hiring decision for a candidate."""
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    decision = Column(String(20), nullable=False)  # offer, reject, waitlist
    salary_offered = Column(String(100), nullable=True)
    start_date = Column(DateTime, nullable=True)
    justification = Column(Text, nullable=True)  # LLM-generated justification
    offer_letter_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    candidate = relationship("Candidate", back_populates="offers")
    job_posting = relationship("JobPosting", back_populates="offers")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate.name if self.candidate else None,
            "job_posting_id": self.job_posting_id,
            "job_title": self.job_posting.title if self.job_posting else None,
            "decision": self.decision,
            "salary_offered": self.salary_offered,
            "justification": self.justification,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
