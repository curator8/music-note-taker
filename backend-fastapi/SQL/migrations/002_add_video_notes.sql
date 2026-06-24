CREATE TABLE IF NOT EXISTS auth.video_extraction_jobs (
    job_id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES auth.videos(video_id) ON DELETE CASCADE,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    create_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_video_extraction_jobs_video_id
    ON auth.video_extraction_jobs(video_id);

CREATE TABLE IF NOT EXISTS auth.video_notes (
    note_id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES auth.videos(video_id) ON DELETE CASCADE,
    note_type VARCHAR(80) NOT NULL,
    start_seconds DOUBLE PRECISION,
    end_seconds DOUBLE PRECISION,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    create_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_video_notes_video_id
    ON auth.video_notes(video_id);

CREATE INDEX IF NOT EXISTS idx_video_notes_note_type
    ON auth.video_notes(note_type);

CREATE INDEX IF NOT EXISTS idx_video_notes_data
    ON auth.video_notes USING GIN (data);
