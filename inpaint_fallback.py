#!/usr/bin/env python3
"""
inpaint_fallback.py — OpenCV-based Gemini watermark removal for videos
where GeminiWatermarkTool auto-detection fails.

Usage:
    python inpaint_fallback.py input.mp4 [output.mp4]

The script:
1. Detects the watermark region automatically by scanning the bottom-right
   corner for pixels brighter than the local background.
2. Extracts all frames, inpaints the watermark region on each frame using
   OpenCV's TELEA inpainting, and re-encodes the video.

Requirements:
    pip install opencv-python
    ffmpeg must be on PATH
"""

import argparse
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np


def detect_watermark(frame: np.ndarray, search_w: int = 200, search_h: int = 250):
    """
    Scan the bottom-right corner for the watermark.
    Returns (x1, y1, x2, y2) in full-frame coordinates, or None.
    """
    h, w = frame.shape[:2]
    roi_x, roi_y = w - search_w, h - search_h
    roi = frame[roi_y:h, roi_x:w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Threshold: pixels clearly brighter than the dark background
    threshold = 80
    bright = (gray > threshold).astype(np.uint8) * 255
    coords = np.where(bright > 0)
    if len(coords[0]) == 0:
        return None

    y_min, y_max = coords[0].min(), coords[0].max()
    x_min, x_max = coords[1].min(), coords[1].max()

    # Sanity check: must be reasonably small (a logo, not the whole frame)
    if (x_max - x_min) > search_w * 0.9 or (y_max - y_min) > search_h * 0.9:
        return None

    # Add padding (extra on left/top where diamond tip tends to be clipped)
    pad_left, pad_top, pad_right, pad_bottom = 18, 15, 10, 10
    return (
        max(0, roi_x + x_min - pad_left),
        max(0, roi_y + y_min - pad_top),
        min(w, roi_x + x_max + pad_right),
        min(h, roi_y + y_max + pad_bottom),
    )


def build_mask(frame: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
    """Build an inpaint mask (white = watermark pixels) for the given region."""
    region = frame[y1:y2, x1:x2]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.dilate(mask, kernel, iterations=2)
    full_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    full_mask[y1:y2, x1:x2] = mask
    return full_mask


def inpaint_frame(frame: np.ndarray, full_mask: np.ndarray,
                  x1: int, y1: int, x2: int, y2: int,
                  pad: int = 20, radius: int = 3) -> np.ndarray:
    """Inpaint the watermark region using surrounding context."""
    h, w = frame.shape[:2]
    ry1, ry2 = max(0, y1 - pad), min(h, y2 + pad)
    rx1, rx2 = max(0, x1 - pad), min(w, x2 + pad)
    region = frame[ry1:ry2, rx1:rx2].copy()
    region_mask = full_mask[ry1:ry2, rx1:rx2]
    inpainted = cv2.inpaint(region, region_mask, radius, cv2.INPAINT_TELEA)
    result = frame.copy()
    result[ry1:ry2, rx1:rx2] = inpainted
    return result


def get_fps(input_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", input_path],
        capture_output=True, text=True
    )
    num, den = result.stdout.strip().split("/")
    return float(num) / float(den)


def process(input_path: str, output_path: str):
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    with tempfile.TemporaryDirectory() as frames_dir:
        # 1. Extract frames
        print("Extracting frames...")
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             os.path.join(frames_dir, "frame_%04d.png")],
            check=True, capture_output=True
        )

        frames = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
        if not frames:
            print("ERROR: no frames extracted", file=sys.stderr)
            sys.exit(1)

        print(f"Detecting watermark on first frame...")
        first = cv2.imread(os.path.join(frames_dir, frames[0]))
        bounds = detect_watermark(first)
        if bounds is None:
            print("ERROR: could not detect watermark in bottom-right corner.", file=sys.stderr)
            print("The video may not have a detectable Gemini watermark.", file=sys.stderr)
            sys.exit(1)

        x1, y1, x2, y2 = bounds
        print(f"Watermark detected at ({x1},{y1})-({x2},{y2}), size={x2-x1}x{y2-y1}")

        # 2. Inpaint each frame
        print(f"Processing {len(frames)} frames...")
        for i, fname in enumerate(frames):
            path = os.path.join(frames_dir, fname)
            img = cv2.imread(path)
            mask = build_mask(img, x1, y1, x2, y2)
            result = inpaint_frame(img, mask, x1, y1, x2, y2)
            cv2.imwrite(path, result)
            if (i + 1) % 10 == 0 or (i + 1) == len(frames):
                print(f"  {i+1}/{len(frames)}")

        # 3. Re-encode with original audio
        fps = get_fps(input_path)
        print(f"Re-encoding at {fps:.3f} fps...")
        subprocess.run(
            ["ffmpeg", "-y",
             "-framerate", str(fps),
             "-i", os.path.join(frames_dir, "frame_%04d.png"),
             "-i", input_path,
             "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-crf", "18", "-preset", "fast",
             "-movflags", "+faststart", "-pix_fmt", "yuv420p",
             "-c:a", "copy",
             output_path],
            check=True
        )

    print(f"Done -> {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="OpenCV inpaint fallback for Gemini watermark removal in videos."
    )
    parser.add_argument("input", help="Input video file (.mp4/.mkv/.mov)")
    parser.add_argument("output", nargs="?", help="Output file (default: input_inpainted.mp4)")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output = args.output
    else:
        base, ext = os.path.splitext(args.input)
        output = f"{base}_inpainted{ext}"

    process(args.input, output)


if __name__ == "__main__":
    main()
