#!/usr/bin/env python3
"""
Hybrid watermark removal (v12):
1. Run GWT snap WITHOUT --denoise ai (reverse alpha blending removes bright diamond).
2. Build a fixed diamond mask once from the darkest-background reference frame.
3. Inpaint the full fixed mask with TELEA radius=12 — this cleanly replaces
   the semi-transparent edge/outline ring that GWT leaves behind, without
   the blurry-square artifact that --denoise ai caused.
"""
import os, sys, subprocess, tempfile
import cv2, numpy as np

GWT = r"C:\Users\Murat\Projects\VeoWatermarkRemover\GeminiWatermarkTool-Video.exe"

def get_fps(path):
    r = subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=r_frame_rate",
        "-of","default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    n, d = r.stdout.strip().split("/")
    return float(n)/float(d)

def detect_region(frame_path):
    img = cv2.imread(frame_path)
    h, w = img.shape[:2]
    roi_x, roi_y = w-220, h-250  # wide enough to capture diamond left edge
    roi = img[roi_y:h, roi_x:w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    bright = (gray > 80).astype(np.uint8)
    coords = np.where(bright > 0)
    if not len(coords[0]): return None
    y_min, y_max = coords[0].min(), coords[0].max()
    x_min, x_max = coords[1].min(), coords[1].max()
    pad = 40
    return (max(0,roi_x+x_min-pad), max(0,roi_y+y_min-pad),
            min(w,roi_x+x_max+pad)-max(0,roi_x+x_min-pad),
            min(h,roi_y+y_max+pad)-max(0,roi_y+y_min-pad))

def build_fixed_mask(frames_dir, frames, wm_x1, wm_y1, wm_x2, wm_y2):
    """Find darkest-background frame, Otsu+dilation to build diamond mask."""
    best_frame = None
    lowest_bg = 999
    step = max(1, len(frames) // 30)
    for fname in frames[::step]:
        img = cv2.imread(os.path.join(frames_dir, fname))
        region = img[wm_y1:wm_y2, wm_x1:wm_x2]
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        bg = float(np.percentile(gray, 25))
        if bg < lowest_bg:
            lowest_bg = bg
            best_frame = fname
    print(f"  Reference frame for mask: {best_frame} (bg Q25={lowest_bg:.1f})")
    img = cv2.imread(os.path.join(frames_dir, best_frame))
    region = img[wm_y1:wm_y2, wm_x1:wm_x2]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    mask = cv2.dilate(mask, kernel, iterations=2)
    return mask

def inpaint_diamond(img, fixed_mask, wm_x1, wm_y1, wm_x2, wm_y2,
                    radius=12):
    """Inpaint the full diamond mask area to erase outline residual."""
    h, w = img.shape[:2]
    full_mask = np.zeros((h, w), np.uint8)
    full_mask[wm_y1:wm_y2, wm_x1:wm_x2] = fixed_mask
    pad = 30
    ry1, ry2 = max(0, wm_y1-pad), min(h, wm_y2+pad)
    rx1, rx2 = max(0, wm_x1-pad), min(w, wm_x2+pad)
    sub = img[ry1:ry2, rx1:rx2].copy()
    sub_mask = full_mask[ry1:ry2, rx1:rx2]
    inpainted = cv2.inpaint(sub, sub_mask, radius, cv2.INPAINT_TELEA)
    result = img.copy()
    result[ry1:ry2, rx1:rx2] = inpainted
    return result

def process(input_path, output_path):
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    with tempfile.TemporaryDirectory() as frames_dir:
        print("Extracting frames...")
        subprocess.run(["ffmpeg","-y","-i",input_path,
            os.path.join(frames_dir,"frame_%04d.png")],
            check=True, capture_output=True)

        frames = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
        print(f"{len(frames)} frames")

        first = os.path.join(frames_dir, frames[0])
        region = detect_region(first)
        if not region:
            print("ERROR: watermark region not found"); sys.exit(1)
        rx, ry, rw, rh = region
        region_str = f"{rx},{ry},{rw},{rh}"
        wm_x1, wm_y1, wm_x2, wm_y2 = rx+40, ry+40, rx+rw-40, ry+rh-40
        print(f"Watermark: ({wm_x1},{wm_y1})-({wm_x2},{wm_y2}), GWT search: {region_str}")

        print("Building fixed diamond mask...")
        fixed_mask = build_fixed_mask(frames_dir, frames, wm_x1, wm_y1, wm_x2, wm_y2)

        print("Processing: GWT snap (no denoise) + TELEA inpaint r=12 ...")
        for i, fname in enumerate(frames):
            path = os.path.join(frames_dir, fname)

            # Step 1: GWT snap without denoising
            subprocess.run([GWT, "-i", path, "-o", path,
                "--snap", "--fallback-region", region_str,
                "--snap-threshold", "0.05"],
                capture_output=True)

            # Step 2: inpaint full diamond mask to remove outline residual
            img = cv2.imread(path)
            result = inpaint_diamond(img, fixed_mask, wm_x1, wm_y1, wm_x2, wm_y2)
            cv2.imwrite(path, result)

            if (i+1) % 20 == 0 or (i+1) == len(frames):
                print(f"  {i+1}/{len(frames)}")

        fps = get_fps(input_path)
        print(f"Re-encoding at {fps:.3f} fps...")
        subprocess.run(["ffmpeg","-y",
            "-framerate", str(fps),
            "-i", os.path.join(frames_dir,"frame_%04d.png"),
            "-i", input_path,
            "-map","0:v","-map","1:a",
            "-c:v","libx264","-crf","18","-preset","fast",
            "-movflags","+faststart","-pix_fmt","yuv420p",
            "-c:a","copy", output_path], check=True)

    print(f"Done -> {output_path}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("input"); p.add_argument("output", nargs="?")
    args = p.parse_args()
    out = args.output or args.input.replace(".mp4","_clean.mp4")
    process(args.input, out)
