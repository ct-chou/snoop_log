"""
processor.py — Extract frames and audio from a training session video.
"""

import os
import tempfile
import base64
from pathlib import Path

import ffmpeg
from PIL import Image


def extract_frames(video_path: str, num_frames: int = 8) -> list[str]:
    """
    Extract `num_frames` evenly-spaced frames from a video.
    Returns a list of base64-encoded JPEG strings (for Claude vision API).
    """
    video_path = str(video_path)

    # Get video duration
    probe = ffmpeg.probe(video_path)
    duration = float(probe["format"]["duration"])

    frame_dir = tempfile.mkdtemp()
    frames_b64 = []

    for i in range(num_frames):
        t = duration * i / num_frames
        frame_path = os.path.join(frame_dir, f"frame_{i:03d}.jpg")

        (
            ffmpeg
            .input(video_path, ss=t)
            .output(frame_path, vframes=1, format="image2", vcodec="mjpeg")
            .overwrite_output()
            .run(quiet=True)
        )

        if os.path.exists(frame_path):
            with open(frame_path, "rb") as f:
                frames_b64.append(base64.standard_b64encode(f.read()).decode("utf-8"))
            os.unlink(frame_path)

    os.rmdir(frame_dir)
    return frames_b64


def extract_audio(video_path: str) -> str:
    """
    Extract audio from a video file as mp3.
    Returns path to the temp mp3 file.
    """
    video_path = str(video_path)
    audio_fd, audio_path = tempfile.mkstemp(suffix=".mp3")
    os.close(audio_fd)

    (
        ffmpeg
        .input(video_path)
        .output(audio_path, acodec="libmp3lame", audio_bitrate="128k", vn=None)
        .overwrite_output()
        .run(quiet=True)
    )

    return audio_path


def process_video(video_path: str, num_frames: int = 8) -> dict:
    """
    Full processing pipeline for a session video.
    Returns {"frames_b64": [...], "audio_path": str, "duration": float}
    """
    probe = ffmpeg.probe(str(video_path))
    duration = float(probe["format"]["duration"])

    frames = extract_frames(video_path, num_frames)
    audio_path = extract_audio(video_path)

    return {
        "frames_b64": frames,
        "audio_path": audio_path,
        "duration": duration,
    }
