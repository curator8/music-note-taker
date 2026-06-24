from datetime import datetime
from typing import Any, Dict, Optional

from config import DATABASE_URL
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel, create_engine, select


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    user_id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    password_hash: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = True
    email_verified: Optional[bool] = False
    failed_login_attempts: Optional[int] = 0
    last_login_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    create_dt: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


# table = True makes it a table model 
class Video(SQLModel, table=True):

    __tablename__ = "videos"
    __table_args__ = {"schema": "auth"}


    video_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="auth.users.user_id")
    title: str
    file_path: str
    description: Optional[str] = None
    create_dt: Optional[datetime] = None




class VideoExtractionJob(SQLModel, table=True):
    __tablename__ = "video_extraction_jobs"
    __table_args__ = {"schema": "auth"}

    job_id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="auth.videos.video_id", index=True)
    status: str = Field(default="pending")
    error_message: Optional[str] = None
    create_dt: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class VideoNote(SQLModel, table=True):
    __tablename__ = "video_notes"
    __table_args__ = {"schema": "auth"}

    note_id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="auth.videos.video_id", index=True)
    note_type: str = Field(index=True)
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    title: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    create_dt: Optional[datetime] = Field(default_factory=datetime.utcnow)


def connect_music_db():
    return create_engine(DATABASE_URL)


def get_users():
    engine = connect_music_db()
    with Session(engine) as session:
        return session.exec(select(User)).all()

def get_videos():
    engine = connect_music_db()
    with Session(engine) as session: 
        return session.exec(select(Video)).all()    


def get_video_by_id(video_id: int):
    engine = connect_music_db()
    with Session(engine) as session:
        return session.get(Video, video_id)


def create_video(user_id: int, title: str, file_path: str, description: Optional[str] = None):
    engine = connect_music_db()
    with Session(engine) as session:
        video = Video(
            user_id=user_id,
            title=title,
            file_path=file_path,
            description=description,
            create_dt=datetime.utcnow(),
        )
        session.add(video)
        session.commit()
        session.refresh(video)
        return video
    

def get_videos_by_user(user_id: int):
    engine = connect_music_db() 

    with Session(engine) as session: 
        statement = (
            select(Video).
            where(Video.user_id == user_id)
            .order_by(Video.create_dt.desc())
        )

        return session.exec(statement).all()


def update_video_description(video_id: int, description: str):
    engine = connect_music_db()

    with Session(engine) as session:
        video = session.get(Video, video_id)

        if video is None:
            return None

        video.description = description
        session.add(video)
        session.commit()
        session.refresh(video)

        return video


def create_video_extraction_job(video_id: int):
    engine = connect_music_db()
    with Session(engine) as session:
        job = VideoExtractionJob(
            video_id=video_id,
            status="pending",
            create_dt=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


def get_latest_video_extraction_job(video_id: int):
    engine = connect_music_db()
    with Session(engine) as session:
        statement = (
            select(VideoExtractionJob)
            .where(VideoExtractionJob.video_id == video_id)
            .order_by(VideoExtractionJob.create_dt.desc())
        )
        return session.exec(statement).first()


def update_video_extraction_job(
    job_id: int,
    status: str,
    error_message: Optional[str] = None,
):
    engine = connect_music_db()
    with Session(engine) as session:
        job = session.get(VideoExtractionJob, job_id)

        if job is None:
            return None

        job.status = status
        job.error_message = error_message
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


def get_video_notes(video_id: int):
    engine = connect_music_db()
    with Session(engine) as session:
        statement = (
            select(VideoNote)
            .where(VideoNote.video_id == video_id)
            .order_by(VideoNote.start_seconds.nullsfirst(), VideoNote.note_id)
        )
        return session.exec(statement).all()


def replace_video_notes(video_id: int, notes: list[dict[str, Any]]):
    engine = connect_music_db()
    with Session(engine) as session:
        existing_notes = session.exec(
            select(VideoNote).where(VideoNote.video_id == video_id)
        ).all()

        for note in existing_notes:
            session.delete(note)

        saved_notes = []
        for note in notes:
            saved_note = VideoNote(**note)
            session.add(saved_note)
            saved_notes.append(saved_note)

        session.commit()

        for note in saved_notes:
            session.refresh(note)

        return saved_notes
