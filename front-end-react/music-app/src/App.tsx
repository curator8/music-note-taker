import { useEffect, useState } from "react";
import { Video } from "./Video.tsx";

// import "./App.css";

function App() {
  const [videos, setVideos] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/users/1/videos")
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
      
      <Video />
    </>
  );
}

export default App;
