from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable


DEFAULT_AUDIO_SAMPLE_RATE = 16000
DEFAULT_PAUSE_SECONDS = 0.3


def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def _round(value: Any, digits: int = 2) -> float:
    return round(float(value), digits)


def _safe_mean(values: Iterable[float], default: float = 0.0) -> float:
    values = list(values)
    if not values:
        return default

    np = _import_numpy()
    return float(np.mean(values))


def _safe_max(values: Iterable[float], default: float = 0.0) -> float:
    values = list(values)
    return float(max(values)) if values else default


def _to_jsonable(value: Any) -> Any:
    try:
        import numpy as np
    except ImportError:
        np = None

    if np is not None:
        if isinstance(value, np.ndarray):
            return [_to_jsonable(item) for item in value.tolist()]
        if isinstance(value, np.generic):
            return value.item()

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]

    return value


def _import_numpy():
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("numpy is required for practice video analysis") from exc

    return np


def _import_librosa():
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("librosa is required for audio practice analysis") from exc

    return librosa


def extract_audio_from_video(
    video_path: str | Path,
    audio_path: str | Path | None = None,
    sample_rate: int = DEFAULT_AUDIO_SAMPLE_RATE,
) -> str:
    """Extract mono WAV audio from a video file using ffmpeg."""
    video_path = Path(video_path)
    if audio_path is None:
        audio_path = video_path.with_suffix(".wav")
    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
    )

    return str(audio_path)


def load_audio(audio_path: str | Path, sample_rate: int | None = None) -> tuple[Any, int]:
    librosa = _import_librosa()
    music_array, loaded_sample_rate = librosa.load(str(audio_path), sr=sample_rate)
    return music_array, int(loaded_sample_rate)


def analyze_tempo(music_array: Any, sample_rate: int) -> dict[str, Any]:
    librosa = _import_librosa()
    np = _import_numpy()

    tempo, beats = librosa.beat.beat_track(y=music_array, sr=sample_rate)
    tempo_value = float(np.asarray(tempo).reshape(-1)[0]) if np.size(tempo) else 0.0
    beat_times = librosa.frames_to_time(beats, sr=sample_rate)
    beat_intervals = np.diff(beat_times)
    instant_bpms = 60 / beat_intervals if len(beat_intervals) else np.array([])

    return {
        "estimated_bpm": _round(tempo_value),
        "average_bpm": _round(np.mean(instant_bpms)) if len(instant_bpms) else _round(tempo_value),
        "bpm_variance": _round(np.var(instant_bpms)) if len(instant_bpms) else 0,
        "bpm_standard_deviation": _round(np.std(instant_bpms)) if len(instant_bpms) else 0,
        "beat_count": int(len(beats)),
        "beat_times_seconds": [_round(time) for time in beat_times],
        "instant_bpms": [_round(bpm) for bpm in instant_bpms],
    }


def detect_pauses(
    music_array: Any,
    sample_rate: int,
    top_db: int = 40,
    minimum_pause_seconds: float = DEFAULT_PAUSE_SECONDS,
) -> dict[str, Any]:
    librosa = _import_librosa()
    np = _import_numpy()

    intervals = librosa.effects.split(music_array, top_db=top_db)
    interval_times = librosa.samples_to_time(intervals, sr=sample_rate)
    pauses = []

    for index in range(len(interval_times) - 1):
        pause_start = float(interval_times[index][1])
        pause_end = float(interval_times[index + 1][0])
        pause_duration = pause_end - pause_start

        if pause_duration >= minimum_pause_seconds:
            pauses.append(
                {
                    "start_seconds": _round(pause_start),
                    "end_seconds": _round(pause_end),
                    "duration_seconds": _round(pause_duration),
                    "start_label": format_time(pause_start),
                    "end_label": format_time(pause_end),
                }
            )

    durations = [pause["duration_seconds"] for pause in pauses]
    return {
        "pause_count": len(pauses),
        "longest_pause_seconds": _round(_safe_max(durations)),
        "total_pause_seconds": _round(float(np.sum(durations)) if durations else 0),
        "events": pauses,
    }


def analyze_dynamics(music_array: Any, sample_rate: int) -> dict[str, Any]:
    librosa = _import_librosa()
    np = _import_numpy()

    intervals = librosa.effects.split(music_array, top_db=40)
    non_silent_audio = (
        np.concatenate([music_array[start:end] for start, end in intervals])
        if len(intervals)
        else music_array
    )

    rms = librosa.feature.rms(y=non_silent_audio)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max) if len(rms) else np.array([])

    full_rms = librosa.feature.rms(y=music_array)[0]
    full_rms_db = librosa.amplitude_to_db(full_rms, ref=np.max) if len(full_rms) else np.array([])
    rms_times = librosa.frames_to_time(np.arange(len(full_rms_db)), sr=sample_rate)

    section_size = max(1, len(full_rms_db) // 4) if len(full_rms_db) else 1
    start_volume = float(np.mean(full_rms_db[:section_size])) if len(full_rms_db) else 0
    end_volume = float(np.mean(full_rms_db[-section_size:])) if len(full_rms_db) else 0
    volume_change = end_volume - start_volume

    smoothed_rms = np.array([])
    smoothed_times = np.array([])
    window_size = 10
    if len(full_rms_db) >= window_size:
        smoothed_rms = np.convolve(full_rms_db, np.ones(window_size) / window_size, mode="valid")
        smoothed_times = rms_times[window_size - 1 :]

    crescendos = []
    for index in range(max(0, len(smoothed_rms) - window_size)):
        start = smoothed_rms[index]
        end = smoothed_rms[index + window_size]

        if end - start > 4:
            crescendos.append(
                {
                    "start_seconds": _round(smoothed_times[index]),
                    "end_seconds": _round(smoothed_times[index + window_size]),
                    "change_db": _round(end - start),
                }
            )

    if volume_change > 3:
        feedback = "Volume increased gradually through the performance."
    elif volume_change < -3:
        feedback = "Volume faded toward the end."
    elif crescendos:
        feedback = "Crescendos were present."
    else:
        feedback = "Volume stayed mostly consistent."

    return {
        "average_volume_db": _round(np.mean(rms_db)) if len(rms_db) else 0,
        "max_volume_db": _round(np.max(rms_db)) if len(rms_db) else 0,
        "min_volume_db": _round(np.min(rms_db)) if len(rms_db) else 0,
        "dynamic_range_db": _round(np.max(rms_db) - np.min(rms_db)) if len(rms_db) else 0,
        "start_volume_db": _round(start_volume),
        "end_volume_db": _round(end_volume),
        "volume_change_db": _round(volume_change),
        "crescendos": crescendos,
        "feedback": feedback,
    }


def analyze_pitch(music_array: Any, sample_rate: int) -> dict[str, Any]:
    librosa = _import_librosa()
    np = _import_numpy()

    f0, _, _ = librosa.pyin(
        music_array,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sample_rate,
    )
    times = librosa.times_like(f0, sr=sample_rate)
    voiced_f0 = f0[~np.isnan(f0)]
    voiced_times = times[~np.isnan(f0)]

    if len(voiced_f0) == 0:
        return {
            "average_pitch_hz": 0,
            "average_pitch_note": None,
            "pitch_standard_deviation_hz": 0,
            "pitch_standard_deviation_cents": 0,
            "pitch_jump_count": 0,
            "pitch_jump_times_seconds": [],
            "vibrato_frequency_hz": 0,
            "feedback": "No clear pitch detected.",
        }

    average_pitch_hz = float(np.mean(voiced_f0))
    pitch_cents = 1200 * np.log2(voiced_f0 / average_pitch_hz)
    pitch_cents_series = 1200 * np.log2(voiced_f0 / voiced_f0[0])
    pitch_jumps_cents = np.abs(np.diff(pitch_cents_series))
    jump_times = voiced_times[1:][pitch_jumps_cents > 200]

    try:
        from scipy.signal import find_peaks

        peaks, _ = find_peaks(pitch_cents, distance=3)
    except ImportError:
        peaks = []

    if len(peaks) > 1:
        peak_times = voiced_times[peaks]
        vibrato_periods = np.diff(peak_times)
        vibrato_frequency = float(1 / np.mean(vibrato_periods))
    else:
        vibrato_frequency = 0.0

    pitch_std_cents = float(np.std(pitch_cents))
    if pitch_std_cents < 25:
        feedback = "Sustained notes showed stable pitch."
    elif pitch_std_cents < 60:
        feedback = "Some pitch variation detected."
    else:
        feedback = "Several large pitch deviations detected."

    return {
        "average_pitch_hz": _round(average_pitch_hz),
        "average_pitch_note": librosa.hz_to_note(average_pitch_hz),
        "pitch_variance_hz": _round(np.var(voiced_f0)),
        "pitch_standard_deviation_hz": _round(np.std(voiced_f0)),
        "pitch_variance_cents": _round(np.var(pitch_cents)),
        "pitch_standard_deviation_cents": _round(pitch_std_cents),
        "pitch_jump_count": int(len(jump_times)),
        "pitch_jump_times_seconds": [_round(time) for time in jump_times],
        "vibrato_frequency_hz": _round(vibrato_frequency),
        "feedback": feedback,
    }


def analyze_tone(music_array: Any, sample_rate: int) -> dict[str, Any]:
    librosa = _import_librosa()
    np = _import_numpy()

    centroid = librosa.feature.spectral_centroid(y=music_array, sr=sample_rate)[0]
    flatness = librosa.feature.spectral_flatness(y=music_array)[0]
    rms = librosa.feature.rms(y=music_array)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    playing_frames = rms_db > -40

    centroid_playing = centroid[playing_frames]
    flatness_playing = flatness[playing_frames]

    avg_centroid = float(np.mean(centroid_playing)) if len(centroid_playing) else 0
    centroid_std = float(np.std(centroid_playing)) if len(centroid_playing) else 0
    avg_flatness = float(np.mean(flatness_playing)) if len(flatness_playing) else 0
    avg_rms = float(np.mean(rms[playing_frames])) if len(rms[playing_frames]) else 0

    if avg_centroid < 1000:
        color_feedback = "Tone remained consistently warm."
    elif avg_centroid < 1800:
        color_feedback = "Tone had a balanced warmth and brightness."
    else:
        color_feedback = "Tone was bright or aggressive."

    if avg_centroid > 1800 and avg_flatness > 0.02:
        scratch_feedback = "Scratchy bowing detected."
    else:
        scratch_feedback = "Bowing tone sounded mostly clean."

    if avg_rms > 0.03 and avg_flatness < 0.015:
        resonance_feedback = "Rich resonance detected."
    else:
        resonance_feedback = "Resonance could be stronger."

    if centroid_std < 300:
        consistency_feedback = "Tone remained consistent."
    elif centroid_std < 600:
        consistency_feedback = "Tone had some variation."
    else:
        consistency_feedback = "Tone consistency varied noticeably."

    return {
        "average_centroid_hz": _round(avg_centroid),
        "centroid_variation_hz": _round(centroid_std),
        "average_flatness": round(avg_flatness, 4),
        "average_rms": round(avg_rms, 4),
        "color_feedback": color_feedback,
        "scratch_feedback": scratch_feedback,
        "resonance_feedback": resonance_feedback,
        "consistency_feedback": consistency_feedback,
    }


def analyze_attacks(music_array: Any, sample_rate: int, window_seconds: int = 10) -> dict[str, Any]:
    librosa = _import_librosa()
    np = _import_numpy()

    onset_frames = librosa.onset.onset_detect(y=music_array, sr=sample_rate, units="frames")
    onset_times = librosa.frames_to_time(onset_frames, sr=sample_rate)
    duration_seconds = librosa.get_duration(y=music_array, sr=sample_rate)
    duration_minutes = duration_seconds / 60 if duration_seconds else 0
    attack_intervals = np.diff(onset_times)

    bins = np.arange(0, duration_seconds + window_seconds, window_seconds)
    attack_counts, _ = np.histogram(onset_times, bins=bins) if len(bins) > 1 else ([], [])
    attack_density = attack_counts / window_seconds if len(attack_counts) else []

    if len(attack_intervals) == 0:
        feedback = "Not enough attacks detected to measure consistency."
    elif np.std(attack_intervals) < 0.1:
        feedback = "Attacks were rhythmically consistent."
    elif np.std(attack_intervals) < 0.25:
        feedback = "Some irregular attacks detected."
    else:
        feedback = "Irregular attacks detected."

    density_by_window = []
    for index, density in enumerate(attack_density):
        density_by_window.append(
            {
                "start_seconds": _round(bins[index]),
                "end_seconds": _round(min(bins[index + 1], duration_seconds)),
                "attacks_per_second": _round(density),
            }
        )

    return {
        "attack_count": int(len(onset_times)),
        "notes_per_minute": _round(len(onset_times) / duration_minutes) if duration_minutes else 0,
        "average_attack_spacing_seconds": _round(np.mean(attack_intervals)) if len(attack_intervals) else 0,
        "attack_irregularity_seconds": _round(np.std(attack_intervals)) if len(attack_intervals) else 0,
        "attack_times_seconds": [_round(time) for time in onset_times],
        "density_by_window": density_by_window,
        "feedback": feedback,
    }


def analyze_difficult_sections(
    music_array: Any,
    sample_rate: int,
    window_seconds: int = 35,
) -> dict[str, Any]:
    librosa = _import_librosa()
    np = _import_numpy()

    pause_result = detect_pauses(music_array, sample_rate)
    pauses = pause_result["events"]
    rms = librosa.feature.rms(y=music_array)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    rms_times = librosa.frames_to_time(np.arange(len(rms_db)), sr=sample_rate)
    session_length_seconds = librosa.get_duration(y=music_array, sr=sample_rate)
    bins = np.arange(0, session_length_seconds + window_seconds, window_seconds)
    sections = []

    for index in range(len(bins) - 1):
        start = float(bins[index])
        end = float(min(bins[index + 1], session_length_seconds))
        window_pauses = [pause for pause in pauses if start <= pause["start_seconds"] < end]
        pause_count = len(window_pauses)
        total_pause_time = sum(pause["duration_seconds"] for pause in window_pauses)
        rms_in_window = rms_db[(rms_times >= start) & (rms_times < end)]
        avg_rms = float(np.mean(rms_in_window)) if len(rms_in_window) else -80
        rms_variance = float(np.var(rms_in_window)) if len(rms_in_window) else 0
        difficulty_score = pause_count * 2.0 + total_pause_time * 1.5 + rms_variance * 0.05

        sections.append(
            {
                "start_seconds": _round(start),
                "end_seconds": _round(end),
                "start_label": format_time(start),
                "end_label": format_time(end),
                "pause_count": pause_count,
                "total_pause_seconds": _round(total_pause_time),
                "average_rms_db": _round(avg_rms),
                "rms_variance": _round(rms_variance),
                "difficulty_score": _round(difficulty_score),
            }
        )

    ranked_sections = sorted(sections, key=lambda section: section["difficulty_score"], reverse=True)
    hardest_section = ranked_sections[0] if ranked_sections else None

    if not hardest_section or hardest_section["pause_count"] == 0:
        feedback = "No major difficult section detected from pauses."
    else:
        feedback = (
            f"Most interruptions occurred between {hardest_section['start_label']}-"
            f"{hardest_section['end_label']}. This section may need focused practice."
        )

    return {
        "hardest_section": hardest_section,
        "top_sections": ranked_sections[:3],
        "sections": sections,
        "feedback": feedback,
    }


def analyze_audio_file(audio_path: str | Path, sample_rate: int | None = None) -> dict[str, Any]:
    librosa = _import_librosa()
    music_array, loaded_sample_rate = load_audio(audio_path, sample_rate=sample_rate)
    duration_seconds = librosa.get_duration(y=music_array, sr=loaded_sample_rate)

    result = {
        "source": {"audio_path": str(audio_path), "sample_rate": loaded_sample_rate},
        "duration": {
            "seconds": _round(duration_seconds),
            "label": format_time(duration_seconds),
        },
        "tempo": analyze_tempo(music_array, loaded_sample_rate),
        "pauses": detect_pauses(music_array, loaded_sample_rate),
        "dynamics": analyze_dynamics(music_array, loaded_sample_rate),
        "pitch": analyze_pitch(music_array, loaded_sample_rate),
        "tone": analyze_tone(music_array, loaded_sample_rate),
        "attacks": analyze_attacks(music_array, loaded_sample_rate),
        "difficult_sections": analyze_difficult_sections(music_array, loaded_sample_rate),
    }

    result["feedback"] = [
        result["dynamics"]["feedback"],
        result["pitch"]["feedback"],
        result["tone"]["scratch_feedback"],
        result["tone"]["resonance_feedback"],
        result["tone"]["consistency_feedback"],
        result["attacks"]["feedback"],
        result["difficult_sections"]["feedback"],
    ]

    return _to_jsonable(result)


def transcribe_audio(
    audio_path: str | Path,
    model_name: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    beam_size: int = 5,
) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is required for audio transcription") from exc

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, info = model.transcribe(str(audio_path), beam_size=beam_size)

    transcript_segments = [
        {
            "start_seconds": _round(segment.start),
            "end_seconds": _round(segment.end),
            "text": segment.text.strip(),
        }
        for segment in segments
    ]
    full_transcript = " ".join(segment["text"] for segment in transcript_segments)

    return {
        "description": full_transcript,
        "language": info.language,
        "language_probability": _round(info.language_probability, 4),
        "segments": transcript_segments,
    }


def describe_video_frames(
    video_path: str | Path,
    sample_every_seconds: int = 5,
    model_name: str = "Salesforce/blip-image-captioning-base",
) -> dict[str, Any]:
    try:
        import cv2
        import torch
        from PIL import Image
        from transformers import BlipForConditionalGeneration, BlipProcessor
    except ImportError as exc:
        raise RuntimeError(
            "opencv-python, torch, pillow, and transformers are required for video captions"
        ) from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = BlipProcessor.from_pretrained(model_name)
    model = BlipForConditionalGeneration.from_pretrained(model_name).to(device)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise ValueError("Could not read video FPS")

    frame_interval = max(1, int(fps * sample_every_seconds))
    frame_count = 0
    captions = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            timestamp = frame_count / fps
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)
            inputs = processor(images=image, return_tensors="pt").to(device)

            with torch.no_grad():
                output_ids = model.generate(**inputs, max_new_tokens=30)

            captions.append(
                {
                    "timestamp_seconds": _round(timestamp),
                    "timestamp_label": format_time(timestamp),
                    "description": processor.decode(output_ids[0], skip_special_tokens=True),
                }
            )

        frame_count += 1

    cap.release()

    return {
        "video_path": str(video_path),
        "sample_every_seconds": sample_every_seconds,
        "frame_descriptions": captions,
    }


def get_head_down_score(landmarks: list[Any]) -> float:
    nose = landmarks[0]
    left_eye = landmarks[2]
    right_eye = landmarks[5]
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]
    left_hip = landmarks[23]
    right_hip = landmarks[24]

    eye_y = (left_eye.y + right_eye.y) / 2
    shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
    hip_y = (left_hip.y + right_hip.y) / 2
    torso_height = hip_y - shoulder_y

    if torso_height <= 0:
        return 0.0

    face_y = (nose.y * 0.7) + (eye_y * 0.3)
    head_clearance = (shoulder_y - face_y) / torso_height
    return float(1 - head_clearance)


def _torso_center(landmarks: list[Any]) -> tuple[Any, Any]:
    np = _import_numpy()
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]
    left_hip = landmarks[23]
    right_hip = landmarks[24]

    shoulder_center = np.array(
        [
            (left_shoulder.x + right_shoulder.x) / 2,
            (left_shoulder.y + right_shoulder.y) / 2,
        ]
    )
    hip_center = np.array(
        [
            (left_hip.x + right_hip.x) / 2,
            (left_hip.y + right_hip.y) / 2,
        ]
    )

    return shoulder_center, hip_center


def _calculate_posture_frame_metrics(
    landmarks: list[Any],
    head_down_threshold: float,
) -> tuple[bool, float, float, Any]:
    np = _import_numpy()
    shoulder_center, hip_center = _torso_center(landmarks)
    head_down_score = get_head_down_score(landmarks)
    head_down = head_down_score > head_down_threshold
    torso_vector = shoulder_center - hip_center
    torso_lean = abs(float(torso_vector[0]))
    posture_value = np.array(
        [
            shoulder_center[0],
            shoulder_center[1],
            hip_center[0],
            hip_center[1],
            torso_lean,
        ]
    )

    return head_down, head_down_score, torso_lean, posture_value


def analyze_video_posture(
    video_path: str | Path,
    pose_model_path: str | Path | None = None,
    head_down_threshold: float = 0.35,
    posture_change_threshold: float = 0.08,
) -> dict[str, Any]:
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        raise RuntimeError("opencv-python and mediapipe are required for posture analysis") from exc

    np = _import_numpy()
    if pose_model_path is None:
        pose_model_path = Path(__file__).with_name("pose_landmarker.task")

    BaseOptions = mp.tasks.BaseOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions

    pose_options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(pose_model_path)),
        running_mode=VisionRunningMode.VIDEO,
        num_poses=1,
    )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise ValueError("Could not read video FPS")

    total_pose_frames = 0
    looking_down_frames = 0
    torso_lean_values = []
    posture_values = []
    head_down_scores = []
    head_down_events = []

    with PoseLandmarker.create_from_options(pose_options) as pose_landmarker:
        frame_index = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int((frame_index / fps) * 1000)
            result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)
            time_seconds = frame_index / fps

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                head_down, head_down_score, torso_lean, posture_value = _calculate_posture_frame_metrics(
                    landmarks,
                    head_down_threshold,
                )

                total_pose_frames += 1
                if head_down:
                    looking_down_frames += 1
                    head_down_events.append(
                        {
                            "time_seconds": _round(time_seconds),
                            "time_label": format_time(time_seconds),
                            "score": _round(head_down_score, 3),
                        }
                    )

                torso_lean_values.append(torso_lean)
                posture_values.append(posture_value)
                head_down_scores.append(head_down_score)

            frame_index += 1

    cap.release()

    posture_change_count = 0
    for index in range(1, len(posture_values)):
        change = np.linalg.norm(posture_values[index] - posture_values[index - 1])
        if change > posture_change_threshold:
            posture_change_count += 1

    head_down_segments = []
    if head_down_events:
        start = head_down_events[0]["time_seconds"]
        previous = start

        for event in head_down_events[1:]:
            current = event["time_seconds"]
            if current - previous > 0.5:
                duration = previous - start
                if duration >= 1.0:
                    head_down_segments.append(
                        {
                            "start_seconds": _round(start),
                            "end_seconds": _round(previous),
                            "start_label": format_time(start),
                            "end_label": format_time(previous),
                            "duration_seconds": _round(duration),
                        }
                    )
                start = current
            previous = current

        duration = previous - start
        if duration >= 1.0:
            head_down_segments.append(
                {
                    "start_seconds": _round(start),
                    "end_seconds": _round(previous),
                    "start_label": format_time(start),
                    "end_label": format_time(previous),
                    "duration_seconds": _round(duration),
                }
            )

    looking_down_percent = (
        float(np.mean(np.array(head_down_scores) > head_down_threshold) * 100)
        if head_down_scores
        else 0
    )

    return {
        "looking_down_percent": _round(looking_down_percent),
        "posture_change_count": posture_change_count,
        "average_torso_lean": _round(_safe_mean(torso_lean_values), 3),
        "total_pose_frames": total_pose_frames,
        "looking_down_frames": looking_down_frames,
        "head_down_score_summary": {
            "min": _round(np.min(head_down_scores), 3) if head_down_scores else 0,
            "average": _round(np.mean(head_down_scores), 3) if head_down_scores else 0,
            "max": _round(np.max(head_down_scores), 3) if head_down_scores else 0,
        },
        "head_down_segments": head_down_segments,
        "head_down_events": head_down_events,
    }


def analyze_practice_video(
    video_path: str | Path,
    *,
    audio_path: str | Path | None = None,
    include_posture: bool = False,
    include_transcript: bool = False,
    include_frame_descriptions: bool = False,
) -> dict[str, Any]:
    """Return one JSON-ready payload for the frontend from a practice video."""
    video_path = Path(video_path)
    cleanup_audio = False

    if audio_path is None:
        temp_dir = tempfile.TemporaryDirectory()
        audio_path = Path(temp_dir.name) / f"{video_path.stem}.wav"
        cleanup_audio = True
    else:
        temp_dir = None
        audio_path = Path(audio_path)

    try:
        extracted_audio_path = extract_audio_from_video(video_path, audio_path)
        payload = {
            "video_path": str(video_path),
            "audio": analyze_audio_file(extracted_audio_path, sample_rate=DEFAULT_AUDIO_SAMPLE_RATE),
        }
        if cleanup_audio:
            payload["audio"]["source"]["audio_path"] = None
            payload["audio"]["source"]["temporary_audio"] = True

        if include_posture:
            payload["posture"] = analyze_video_posture(video_path)
        if include_transcript:
            payload["transcript"] = transcribe_audio(extracted_audio_path)
        if include_frame_descriptions:
            payload["frame_descriptions"] = describe_video_frames(video_path)

        return _to_jsonable(payload)
    finally:
        if cleanup_audio and temp_dir is not None:
            temp_dir.cleanup()


def build_video_notes(video_id: int, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert raw analysis output into note rows that are useful in the UI."""
    audio = analysis.get("audio", {})
    notes = []

    tempo = audio.get("tempo")
    if tempo:
        notes.append(
            {
                "video_id": video_id,
                "note_type": "tempo",
                "start_seconds": None,
                "end_seconds": None,
                "title": "Tempo summary",
                "message": (
                    f"Average tempo was {tempo.get('average_bpm', 0)} BPM "
                    f"with {tempo.get('bpm_standard_deviation', 0)} BPM variation."
                ),
                "data": tempo,
            }
        )

    pauses = audio.get("pauses", {}).get("events", [])
    for pause in pauses:
        notes.append(
            {
                "video_id": video_id,
                "note_type": "pause",
                "start_seconds": pause.get("start_seconds"),
                "end_seconds": pause.get("end_seconds"),
                "title": "Pause detected",
                "message": f"Pause lasted {pause.get('duration_seconds', 0)} seconds.",
                "data": pause,
            }
        )

    dynamics = audio.get("dynamics")
    if dynamics:
        notes.append(
            {
                "video_id": video_id,
                "note_type": "dynamics",
                "start_seconds": None,
                "end_seconds": None,
                "title": "Dynamics",
                "message": dynamics.get("feedback", "Dynamics analysis complete."),
                "data": dynamics,
            }
        )

    tone = audio.get("tone")
    if tone:
        for key, title in [
            ("scratch_feedback", "Bowing tone"),
            ("resonance_feedback", "Resonance"),
            ("consistency_feedback", "Tone consistency"),
        ]:
            message = tone.get(key)
            if message:
                notes.append(
                    {
                        "video_id": video_id,
                        "note_type": "tone",
                        "start_seconds": None,
                        "end_seconds": None,
                        "title": title,
                        "message": message,
                        "data": tone,
                    }
                )

    attacks = audio.get("attacks")
    if attacks:
        notes.append(
            {
                "video_id": video_id,
                "note_type": "attacks",
                "start_seconds": None,
                "end_seconds": None,
                "title": "Attack consistency",
                "message": attacks.get("feedback", "Attack analysis complete."),
                "data": attacks,
            }
        )

    difficult = audio.get("difficult_sections", {})
    hardest_section = difficult.get("hardest_section")
    if hardest_section:
        notes.append(
            {
                "video_id": video_id,
                "note_type": "difficult_section",
                "start_seconds": hardest_section.get("start_seconds"),
                "end_seconds": hardest_section.get("end_seconds"),
                "title": "Focused practice section",
                "message": difficult.get("feedback", "This section may need focused practice."),
                "data": hardest_section,
            }
        )

    transcript = analysis.get("transcript")
    if transcript and transcript.get("description"):
        notes.append(
            {
                "video_id": video_id,
                "note_type": "transcript",
                "start_seconds": None,
                "end_seconds": None,
                "title": "Transcript",
                "message": transcript["description"],
                "data": transcript,
            }
        )

    posture = analysis.get("posture")
    if posture:
        notes.append(
            {
                "video_id": video_id,
                "note_type": "posture",
                "start_seconds": None,
                "end_seconds": None,
                "title": "Posture summary",
                "message": f"Looking down for {posture.get('looking_down_percent', 0)}% of detected pose frames.",
                "data": posture,
            }
        )

    return notes


def _extract_openai_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    chunks = []
    for output_item in getattr(response, "output", []) or []:
        for content_item in getattr(output_item, "content", []) or []:
            text = getattr(content_item, "text", None)
            if text:
                chunks.append(text)

    return "".join(chunks)


def generate_llm_video_notes(
    video_id: int,
    analysis: dict[str, Any],
    model: str = "gpt-5.4-mini",
) -> list[dict[str, Any]]:
    """Ask an LLM to turn extraction metrics into teacher-style note rows."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai is required for LLM note generation") from exc

    client = OpenAI()
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "note_type": {"type": "string"},
                        "start_seconds": {"type": ["number", "null"]},
                        "end_seconds": {"type": ["number", "null"]},
                        "title": {"type": "string"},
                        "message": {"type": "string"},
                        "action": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                    },
                    "required": [
                        "note_type",
                        "start_seconds",
                        "end_seconds",
                        "title",
                        "message",
                        "action",
                        "priority",
                    ],
                },
            }
        },
        "required": ["notes"],
    }

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Pretend to be a music teacher writing practice notes for a "
                    "student. Use the JSON extracted from the generated practice "
                    "video to create consistent, helpful notes. Return only JSON "
                    "that matches the requested schema. Create 4 to 8 notes. Each "
                    "note must be specific, encouraging, and actionable. Do not "
                    "invent details that are not supported by the JSON. Use a "
                    "timestamp only when the JSON includes a useful start_seconds "
                    "or end_seconds value. Prefer note_type values like tempo, "
                    "pause, tone, dynamics, rhythm, posture, difficult_section, "
                    "or practice_plan. The message should explain what you noticed "
                    "in one or two sentences. The action should tell the student "
                    "exactly what to practice next."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(analysis),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "practice_video_notes",
                "schema": schema,
                "strict": True,
            }
        },
    )

    payload = json.loads(_extract_openai_text(response))
    notes = []

    for note in payload.get("notes", []):
        notes.append(
            {
                "video_id": video_id,
                "note_type": note["note_type"],
                "start_seconds": note["start_seconds"],
                "end_seconds": note["end_seconds"],
                "title": note["title"],
                "message": f"{note['message']} Practice this: {note['action']}",
                "data": {
                    "source": "openai",
                    "model": model,
                    "priority": note["priority"],
                    "action": note["action"],
                    "raw_note": note,
                },
            }
        )

    return notes
