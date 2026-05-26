for file in video/*.MOV video/*.mov; do
  [ -e "$file" ] || continue

  ffmpeg -y -i "$file" \
    -c:v libx264 \
    -c:a aac \
    -movflags +faststart \
    "${file%.*}.mp4"
done