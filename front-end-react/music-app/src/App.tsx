import { type FormEvent, useEffect, useState } from "react";
import { Video } from "./Video.tsx";
import "./index.css";

interface LessonVideo {
  video_id: number;
  title: string;
  file_path: string;
  description?: string | null;
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

function App() {
  const [videos, setVideos] = useState<LessonVideo[]>([]);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadVideos = () => {
    fetch(`${API_BASE_URL}/users/1/videos`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Could not load videos.");
        }

        return response.json();
      })
      .then((data) => {
        setVideos(data);
      })
      .catch((error) => {
        setUploadError(error instanceof Error ? error.message : "Could not load videos.");
      });
  };

  useEffect(() => {
    loadVideos();
  }, []);

  const uploadVideo = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!file || !title.trim()) {
      setUploadError("Choose a video file and enter a title.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("user_id", "1");
    formData.append("title", title.trim());

    setIsUploading(true);
    setUploadError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/videos`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed.");
      }

      setTitle("");
      setFile(null);
      event.currentTarget.reset();
      loadVideos();
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="app-shell">
      <section className="upload-panel">
        <div>
          <h1>Practice Videos</h1>
          <p>Upload a practice video, then generate timestamped notes from the analysis.</p>
        </div>

        <form className="upload-form" onSubmit={uploadVideo}>
          <label>
            Title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Waltz No. 2 practice"
            />
          </label>

          <label>
            Video file
            <input
              type="file"
              accept="video/*"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>

          <button type="submit" disabled={isUploading}>
            {isUploading ? "Uploading..." : "Upload video"}
          </button>
        </form>

        {uploadError && <p className="error-text">{uploadError}</p>}
      </section>

      <section className="video-list">
      {videos.map((video) => (
        <Video
          key={video.video_id}
          videoId={video.video_id}
          propTitle={video.title}
          propFilePath={video.file_path}
          propDescription={video.description}
        />
      ))}
      </section>
    </main>
  );
}

export default App;
