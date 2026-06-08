#!/usr/bin/env python3
"""
Hybrid watermark removal:
1. GWT snap (reverse alpha blending) — handles the main diamond
2. Tight inpaint pass on any remaining bright residual pixels
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
    roi_x, roi_y = w-200, h-250
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

def cleanup_residual(img_before, img_after, x1, y1, x2, y2):
    """After GWT, inpaint pixels that are still brighter than expected background."""
    region_before = img_before[y1:y2, x1:x2]
    region_after  = img_after[y1:y2, x1:x2]

    # Sample expected background from a ring around the watermark
    pad = 25
    h, w = img_after.shape[:2]
    ring = img_after[max(0,y1-pad):min(h,y2+pad), max(0,x1-pad):min(w,x2+pad)]
    ring_mask = np.ones(ring.shape[:2], bool)
    ry = pad if y1>=pad else y1
    rx = pad if x1>=pad else x1
    ring_mask[ry:ry+(y2-y1), rx:rx+(x2-x1)] = False
    bg_median = np.median(ring[ring_mask].reshape(-1,3), axis=0)

    # Residual = processed pixels still brighter than expected background
    gray_after = cv2.cvtColor(region_after, cv2.COLOR_BGR2GRAY)
    bg_brightness = float(np.mean(bg_median))
    residual_mask = (gray_after > bg_brightness + 35).astype(np.uint8) * 255

    if residual_mask.sum() == 0:
        return img_after  # nothing to fix

    # Dilate slightly to catch edges
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    residual_mask = cv2.dilate(residual_mask, kernel, iterations=1)

    # Inpaint only the residual region with small radius
    full_mask = np.zeros(img_after.shape[:2], np.uint8)
    full_mask[y1:y2, x1:x2] = residual_mask

    rpad = 20
    ry1, ry2 = max(0,y1-rpad), min(h,y2+rpad)
    rx1, rx2 = max(0,x1-rpad), min(w,x2+rpad)
    sub = img_after[ry1:ry2, rx1:rx2].copy()
    sub_mask = full_mask[ry1:ry2, rx1:rx2]
    inpainted = cv2.inpaint(sub, sub_mask, 3, cv2.INPAINT_TELEA)

    result = img_after.copy()
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

        # Detect region from first frame
        first = os.path.join(frames_dir, frames[0])
        region = detect_region(first)
        if not region:
            print("ERROR: watermark region not found"); sys.exit(1)
        rx, ry, rw, rh = region
        region_str = f"{rx},{ry},{rw},{rh}"
        wm_x1, wm_y1, wm_x2, wm_y2 = rx+40, ry+40, rx+rw-40, ry+rh-40
        print(f"Watermark region: ({wm_x1},{wm_y1})-({wm_x2},{wm_y2}), search: {region_str}")

        print("Processing with GWT snap + residual cleanup...")
        for i, fname in enumerate(frames):
            path = os.path.join(frames_dir, fname)
            img_before = cv2.imread(path)

            # Step 1: GWT reverse alpha blending
            subprocess.run([GWT, "-i", path, "-o", path,
                "--snap", "--fallback-region", region_str,
                "--snap-threshold", "0.05",
                "--denoise", "ai"],
                capture_output=True)

            img_after = cv2.imread(path)

            # Step 2: clean up any residual
            result = cleanup_residual(img_before, img_after, wm_x1, wm_y1, wm_x2, wm_y2)
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
