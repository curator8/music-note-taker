// import { useEffect } from "react";

interface VideoProps {
  propTitle: string;
  propFilePath: string;
  propDescription?: string | null;
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
  propTitle,
  propFilePath,
  propDescription,
}: VideoProps) => {
  const videoUrl = getVideoUrl(propFilePath);
  const description = propDescription?.trim();

  return (
    <article>
      <h1>{propTitle}</h1>
      <video width="320" height="240" controls>
        <source src={videoUrl} type="video/mp4" />
      </video>
      <section>
        <h2>Video Description</h2>
        <p>{description || "No description has been added for this video."}</p>
      </section>
    </article>
  );
};
