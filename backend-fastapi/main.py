import importlib.util
import re
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from datamodel import SQLModels
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
VIDEO_DIR = BASE_DIR / "video"
EXTRACTION_UTIL_PATH = BASE_DIR / "practice-video-extraction-logic" / "util.py"


def load_extraction_util():
    spec = importlib.util.spec_from_file_location(
        "practice_video_extraction_util",
        EXTRACTION_UTIL_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanitize_filename(filename: str) -> str:
    path = Path(filename)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", path.stem).strip("-").lower()
    suffix = path.suffix.lower() or ".mp4"
    return f"{stem or 'practice-video'}-{uuid.uuid4().hex[:8]}{suffix}"


def resolve_video_path(file_path: str) -> Path:
    if file_path.startswith("/video/"):
        file_path = file_path.replace("/video/", "", 1)

    path = Path(file_path)
    if path.is_absolute():
        return path

    return VIDEO_DIR / path


class VideoDescriptionUpdate(BaseModel):
    description: str


# instantiates app
app = FastAPI()

VIDEO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/video", StaticFiles(directory=VIDEO_DIR), name="video")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# handles get request to root...root being the "/"
@app.get("/users")
def get_users():
    pass 
    results  =  SQLModels.get_users() 
    return results 


# get single user 
@app.get("/users/:id") 
def get_user():
    pass 



@app.post("/videos")
async def upload_video(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    title: str = Form(...),
    description: str | None = Form(default=None),
):
    filename = sanitize_filename(file.filename or title)
    destination = VIDEO_DIR / filename

    with destination.open("wb") as output_file:
        while chunk := await file.read(1024 * 1024):
            output_file.write(chunk)

    return SQLModels.create_video(
        user_id=user_id,
        title=title,
        file_path=filename,
        description=description,
    )


# get all the videos 
@app.get("/videos") 
def get_videos():
    return SQLModels.get_videos()


# get videos for a user
@app.get("/users/{user_id}/videos")
def get_videos_by_user(user_id: int): 
    return SQLModels.get_videos_by_user(user_id)


@app.patch("/videos/{video_id}/description")
def update_video_description(video_id: int, payload: VideoDescriptionUpdate):
    video = SQLModels.update_video_description(
        video_id=video_id,
        description=payload.description,
    )

    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    return video


def run_note_generation_job(job_id: int, video_id: int, file_path: str):
    extraction_util = load_extraction_util()

    try:
        SQLModels.update_video_extraction_job(job_id, "processing")
        analysis = extraction_util.analyze_practice_video(
            resolve_video_path(file_path),
            include_posture=False,
            include_transcript=False,
            include_frame_descriptions=False,
        )
        try:
            notes = extraction_util.generate_llm_video_notes(video_id, analysis)
        except Exception as llm_exc:
            notes = extraction_util.build_video_notes(video_id, analysis)
            notes.insert(
                0,
                {
                    "video_id": video_id,
                    "note_type": "llm_status",
                    "start_seconds": None,
                    "end_seconds": None,
                    "title": "Generated without LLM",
                    "message": "OpenAI note generation failed, so the app saved structured analysis notes instead.",
                    "data": {"source": "fallback", "error": str(llm_exc)},
                },
            )

        SQLModels.replace_video_notes(video_id, notes)
        SQLModels.update_video_extraction_job(job_id, "complete")
    except Exception as exc:
        SQLModels.update_video_extraction_job(job_id, "failed", str(exc))


@app.post("/videos/{video_id}/generate-notes")
def generate_video_notes(video_id: int, background_tasks: BackgroundTasks):
    video = SQLModels.get_video_by_id(video_id)

    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    job = SQLModels.create_video_extraction_job(video_id)
    background_tasks.add_task(
        run_note_generation_job,
        job.job_id,
        video_id,
        video.file_path,
    )

    return job


@app.get("/videos/{video_id}/notes")
def get_video_notes(video_id: int):
    video = SQLModels.get_video_by_id(video_id)

    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "job": SQLModels.get_latest_video_extraction_job(video_id),
        "notes": SQLModels.get_video_notes(video_id),
    }
