#!/usr/bin/env python3
"""
Use GeminiWatermarkTool image mode with --snap --fallback-region on each frame.
This achieves the same reverse alpha blending quality as auto-detection mode,
for videos where the video-mode NCC gate fails.
"""
import argparse
import os
import subprocess
import sys
import tempfile

GWT = r"C:\Users\Murat\Projects\VeoWatermarkRemover\GeminiWatermarkTool-Video.exe"

def get_fps(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    num, den = r.stdout.strip().split("/")
    return float(num) / float(den)

def detect_region(frame_path):
    """Detect watermark bounding box by brightness scan in bottom-right."""
    import cv2, numpy as np
    img = cv2.imread(frame_path)
    h, w = img.shape[:2]
    roi_x, roi_y = w - 200, h - 250
    roi = img[roi_y:h, roi_x:w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    bright = (gray > 80).astype(np.uint8)
    coords = np.where(bright > 0)
    if not len(coords[0]):
        return None
    y_min, y_max = coords[0].min(), coords[0].max()
    x_min, x_max = coords[1].min(), coords[1].max()
    # Return a generous search region with padding
    pad = 40
    return (
        max(0, roi_x + x_min - pad),
        max(0, roi_y + y_min - pad),
        min(w, roi_x + x_max + pad) - max(0, roi_x + x_min - pad),
        min(h, roi_y + y_max + pad) - max(0, roi_y + y_min - pad),
    )

def process(input_path, output_path):
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    with tempfile.TemporaryDirectory() as frames_dir:
        # 1. Extract frames
        print("Extracting frames...")
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             os.path.join(frames_dir, "frame_%04d.png")],
            check=True, capture_output=True)

        frames = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
        if not frames:
            print("ERROR: no frames extracted", file=sys.stderr)
            sys.exit(1)

        # 2. Detect watermark region from first frame
        first_path = os.path.join(frames_dir, frames[0])
        region = detect_region(first_path)
        if not region:
            print("ERROR: could not detect watermark region", file=sys.stderr)
            sys.exit(1)
        rx, ry, rw, rh = region
        region_str = f"{rx},{ry},{rw},{rh}"
        print(f"Search region: {region_str}")

        # 3. Process each frame with GWT snap search
        print(f"Processing {len(frames)} frames with GWT reverse alpha blending...")
        for i, fname in enumerate(frames):
            path = os.path.join(frames_dir, fname)
            subprocess.run(
                [GWT, "-i", path, "-o", path,
                 "--snap", "--fallback-region", region_str,
                 "--snap-threshold", "0.1",
                 "--denoise", "ai"],
                capture_output=True)
            if (i + 1) % 20 == 0 or (i + 1) == len(frames):
                print(f"  {i+1}/{len(frames)}")

        # 4. Re-encode
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
             "-c:a", "copy", output_path],
            check=True)

    print(f"Done -> {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output", nargs="?")
    args = parser.parse_args()
    if not os.path.isfile(args.input):
        print(f"ERROR: {args.input} not found", file=sys.stderr)
        sys.exit(1)
    output = args.output or args.input.replace(".mp4", "_gwt.mp4")
    process(args.input, output)

if __name__ == "__main__":
    main()
