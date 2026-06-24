# Music Lesson Practice Notes

Music Lesson Practice Notes is a local web app for uploading practice videos,
extracting performance signals from the video/audio, and turning those signals
into useful music-teacher notes.

The project is built around a simple workflow:

1. A student uploads a practice video.
2. FastAPI stores the video in a local backend folder.
3. The student clicks **Generate notes** in the React app.
4. The backend runs the practice-video extraction logic.
5. The extracted JSON is sent to an LLM to create consistent teacher-style notes.
6. The notes are saved in PostgreSQL and displayed beside the video.

## Current Features

- Upload practice videos from the React frontend.
- Store uploaded videos locally in `backend-fastapi/video/`.
- Save video metadata in PostgreSQL with SQLModel.
- Serve uploaded videos through FastAPI static files.
- Generate practice notes from video/audio analysis.
- Store generated notes in a separate PostgreSQL table.
- Show note generation status in the frontend.
- Render generated notes under each video.
- Seek the video to a note timestamp when a timestamp is available.

## Tech Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** FastAPI, SQLModel
- **Database:** PostgreSQL
- **Video/audio processing:** ffmpeg, librosa, OpenCV, MediaPipe
- **AI note generation:** OpenAI API

## Project Structure

```text
backend-fastapi/
  main.py
    FastAPI app, upload endpoint, video endpoints, note-generation endpoints.

  config.py
    Loads local database settings from backend-fastapi/.env.

  datamodel/SQLModels.py
    SQLModel table definitions and database helper functions.

  practice-video-extraction-logic/
    util.py
      Converts videos into analysis JSON, builds rule-based notes,
      and sends extracted JSON to the LLM for teacher-style notes.

    audio_analysis.ipynb
    video_analysis.ipynb
    speech_transcript.ipynb
    video_descrption.ipynb
      Notebook experiments that informed the extraction functions.

  SQL/
    auth/DDL.sql
      Initial schema for users and videos.

    migrations/
      001_add_video_description.sql
      002_add_video_notes.sql
        Adds note-generation job tracking and generated video notes.

  video/
    Local uploaded video storage, served by FastAPI at /video/{file_name}.

front-end-react/music-app/
  src/App.tsx
    Loads videos and provides the upload form.

  src/Video.tsx
    Displays each video, triggers note generation, polls for notes,
    and renders generated notes.

  src/index.css
    App styling for upload, video cards, and notes.
```

## Important Backend Endpoints

### Videos

```http
POST /videos
```

Uploads a video file, stores it locally, and creates a video row in PostgreSQL.
The frontend sends multipart form data with:

- `file`
- `user_id`
- `title`
- `description` optional

```http
GET /users/{user_id}/videos
```

Returns videos for a user.

```http
GET /videos
```

Returns all videos.

```http
GET /video/{file_name}
```

Serves a locally stored video file.

### Notes

```http
POST /videos/{video_id}/generate-notes
```

Starts a background note-generation job for the selected video.

The job:

1. Extracts audio from the video with ffmpeg.
2. Runs practice analysis in `util.py`.
3. Produces structured JSON metrics.
4. Sends the JSON to the LLM with a music-teacher prompt.
5. Saves generated notes in `auth.video_notes`.

```http
GET /videos/{video_id}/notes
```

Returns the latest note-generation job and all saved notes for the video:

```json
{
  "job": {
    "job_id": 1,
    "video_id": 1,
    "status": "complete",
    "error_message": null
  },
  "notes": [
    {
      "note_id": 1,
      "video_id": 1,
      "note_type": "tempo",
      "start_seconds": null,
      "end_seconds": null,
      "title": "Tempo consistency",
      "message": "Your tempo was mostly steady. Practice this: repeat the middle section slowly with a metronome.",
      "data": {
        "source": "openai",
        "model": "gpt-5.4-mini",
        "priority": "medium"
      }
    }
  ]
}
```

## Database Tables

The app uses the `auth` schema.

### `auth.users`

Stores app users.

### `auth.videos`

Stores uploaded video metadata:

- `video_id`
- `user_id`
- `title`
- `file_path`
- `description`
- `create_dt`

### `auth.video_extraction_jobs`

Tracks note generation:

- `job_id`
- `video_id`
- `status`: `pending`, `processing`, `complete`, or `failed`
- `error_message`
- `create_dt`
- `updated_at`

### `auth.video_notes`

Stores generated notes:

- `note_id`
- `video_id`
- `note_type`
- `start_seconds`
- `end_seconds`
- `title`
- `message`
- `data` JSONB
- `create_dt`

## Practice Video Extraction

The main extraction code lives in:

```text
backend-fastapi/practice-video-extraction-logic/util.py
```

Important functions:

- `extract_audio_from_video(...)`
- `analyze_practice_video(...)`
- `analyze_audio_file(...)`
- `analyze_tempo(...)`
- `detect_pauses(...)`
- `analyze_dynamics(...)`
- `analyze_pitch(...)`
- `analyze_tone(...)`
- `analyze_attacks(...)`
- `analyze_difficult_sections(...)`
- `build_video_notes(...)`
- `generate_llm_video_notes(...)`

`analyze_practice_video(...)` returns JSON-ready analysis data. The LLM note
generator then turns that analysis JSON into consistent teacher-style notes.

## LLM Note Prompt

The backend asks the model to behave like a music teacher and return structured
JSON. The prompt is designed to keep notes:

- specific
- encouraging
- actionable
- grounded in the extracted JSON
- consistent in shape for the frontend and database

Each generated note includes a short observation and a concrete practice action.

## Local Setup

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd music_lesson_app
```

### 2. Backend environment

Create `backend-fastapi/.env`:

```env
DB_NAME=music_app_db
DB_PORT=5432
DB_USER=your_database_user
DB_HOST=localhost
DB_PASSWORD=your_database_password
OPENAI_API_KEY=your_openai_api_key
```

Do not commit real API keys or database passwords.

### 3. Install backend dependencies

```bash
cd backend-fastapi
pip install -r requirements.txt
```

The backend also requires `ffmpeg`.

Ubuntu/Debian:

```bash
sudo apt install ffmpeg
```

### 4. Apply database migrations

Run the initial schema and migrations against your PostgreSQL database.

```bash
psql \
  -h localhost \
  -p 5432 \
  -U your_database_user \
  -d music_app_db \
  -f SQL/auth/DDL.sql
```

```bash
psql \
  -h localhost \
  -p 5432 \
  -U your_database_user \
  -d music_app_db \
  -f SQL/migrations/001_add_video_description.sql
```

```bash
psql \
  -h localhost \
  -p 5432 \
  -U your_database_user \
  -d music_app_db \
  -f SQL/migrations/002_add_video_notes.sql
```

### 5. Start the backend

From `backend-fastapi/`:

```bash
uvicorn main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

### 6. Install frontend dependencies

In a second terminal:

```bash
cd front-end-react/music-app
npm install
```

### 7. Start the frontend

```bash
npm run dev
```

The frontend runs at:

```text
http://127.0.0.1:5173
```

The frontend expects the backend at `http://127.0.0.1:8000` by default. You can
override it with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Development Workflow

1. Start PostgreSQL.
2. Start FastAPI from `backend-fastapi/`.
3. Start Vite from `front-end-react/music-app/`.
4. Upload a video in the frontend.
5. Click **Generate notes**.
6. Watch the job status change from `pending` to `processing` to `complete`.
7. Review generated notes below the video.

## Notes for Visitors

This project is still in active development. The current focus is proving the
end-to-end product loop:

```text
upload video -> extract JSON metrics -> generate LLM notes -> store notes -> show notes
```

The notebooks in `practice-video-extraction-logic/` are experiments. The
production-facing extraction functions are being consolidated in `util.py`.

## Future Improvements

- Add authentication instead of using a hard-coded local test user.
- Move note generation to a durable worker queue.
- Add progress events instead of polling.
- Add model configuration in the database or admin UI.
- Improve frontend note filtering by note type and priority.
- Add tests for extraction output and database helpers.
- Rename `practice-video-extraction-logic` to a Python-friendly package name.
