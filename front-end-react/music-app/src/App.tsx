import { useEffect, useState } from "react";
import { Video } from "./Video.tsx";

// import "./App.css";

interface LessonVideo {
  video_id: number;
  title: string;
  file_path: string;
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

function App() {
  const [videos, setVideos] = useState<LessonVideo[]>([]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/users/1/videos`)
      .then((response) => {
        return response.json();
      })
      .then((data) => {
        setVideos(data);
      });
  }, []);

  // console.log(videos);

  return (
    <>
      {videos.map((video) => (
        <Video
          key={video.video_id}
          propTitle={video.title}
          propFilePath={video.file_path}
        />
      ))}
    </>
  );
}

export default App;
