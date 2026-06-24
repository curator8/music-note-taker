import { useEffect, useRef, useState } from "react";

interface VideoProps {
  videoId: number;
  propTitle: string;
  propFilePath: string;
  propDescription?: string | null;
}

interface VideoNote {
  note_id: number;
  note_type: string;
  start_seconds?: number | null;
  end_seconds?: number | null;
  title: string;
  message: string;
  data: Record<string, unknown>;
}

interface ExtractionJob {
  job_id: number;
  video_id: number;
  status: "pending" | "processing" | "complete" | "failed";
  error_message?: string | null;
}

interface NotesResponse {
  job?: ExtractionJob | null;
  notes: VideoNote[];
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const getVideoUrl = (filePath: string) => {
  if (filePath.startsWith("http://") || filePath.startsWith("https://")) {
    return filePath;
  }

  if (filePath.startsWith("/")) {
    return `${API_BASE_URL}${filePath}`;
  }

  return `${API_BASE_URL}/video/${filePath}`;
};

export const Video = ({
  videoId,
  propTitle,
  propFilePath,
  propDescription,
}: VideoProps) => {
  const videoUrl = getVideoUrl(propFilePath);
  const description = propDescription?.trim();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [notes, setNotes] = useState<VideoNote[]>([]);
  const [job, setJob] = useState<ExtractionJob | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadNotes = async () => {
    const response = await fetch(`${API_BASE_URL}/videos/${videoId}/notes`);

    if (!response.ok) {
      throw new Error("Could not load notes.");
    }

    const data: NotesResponse = await response.json();
    setNotes(data.notes ?? []);
    setJob(data.job ?? null);

    return data.job ?? null;
  };

  useEffect(() => {
    loadNotes().catch(() => {
      setNotes([]);
      setJob(null);
    });
  }, [videoId]);

  useEffect(() => {
    if (job?.status !== "pending" && job?.status !== "processing") {
      return;
    }

    const intervalId = window.setInterval(() => {
      loadNotes().catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Could not load notes.");
      });
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, [job?.status, videoId]);

  const generateNotes = async () => {
    setIsGenerating(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/videos/${videoId}/generate-notes`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Could not start note generation.");
      }

      const nextJob: ExtractionJob = await response.json();
      setJob(nextJob);
      await loadNotes();
    } catch (generateError) {
      setError(
        generateError instanceof Error
          ? generateError.message
          : "Could not start note generation.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const seekToNote = (note: VideoNote) => {
    if (note.start_seconds == null || !videoRef.current) {
      return;
    }

    videoRef.current.currentTime = note.start_seconds;
    videoRef.current.play();
  };

  return (
    <article className="video-card">
      <h1>{propTitle}</h1>
      <video ref={videoRef} className="practice-video" controls>
        <source src={videoUrl} type="video/mp4" />
      </video>

      <section className="description-block">
        <h2>Video Description</h2>
        <p>{description || "No description has been added for this video."}</p>
      </section>

      <section className="notes-block">
        <div className="notes-header">
          <div>
            <h2>Practice Notes</h2>
            {job && <p className={`job-status status-${job.status}`}>{job.status}</p>}
          </div>

          <button
            type="button"
            onClick={generateNotes}
            disabled={isGenerating || job?.status === "pending" || job?.status === "processing"}
          >
            {isGenerating || job?.status === "pending" || job?.status === "processing"
              ? "Generating..."
              : "Generate notes"}
          </button>
        </div>

        {job?.status === "failed" && (
          <p className="error-text">{job.error_message || "Note generation failed."}</p>
        )}
        {error && <p className="error-text">{error}</p>}

        {notes.length === 0 ? (
          <p className="empty-text">No notes have been generated for this video.</p>
        ) : (
          <ul className="notes-list">
            {notes.map((note) => (
              <li key={note.note_id}>
                <button type="button" onClick={() => seekToNote(note)}>
                  <span className="note-type">{note.note_type}</span>
                  <strong>{note.title}</strong>
                  <span>{note.message}</span>
                  {note.start_seconds != null && (
                    <small>{Math.floor(note.start_seconds / 60)}:{String(Math.floor(note.start_seconds % 60)).padStart(2, "0")}</small>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
};
