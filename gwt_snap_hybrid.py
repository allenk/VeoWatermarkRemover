#!/usr/bin/env python3
"""
Hybrid watermark removal:
1. Build a fixed diamond mask from the best reference frame (dark background).
2. Run GWT snap on each frame for reverse alpha blending.
3. Within the fixed mask area, check if significant residual remains.
   If yes: inpaint only those residual pixels using the fixed mask.
   This avoids per-frame Otsu which mistakenly picks up skin/fabric.
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

def build_fixed_mask(frames_dir, frames, wm_x1, wm_y1, wm_x2, wm_y2):
    """
    Find the frame with the darkest background in the watermark region,
    run Otsu there, return the mask. This mask defines exactly where the
    diamond pixels are — reuse for all frames.
    """
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
    return mask  # (wm_h, wm_w)

def sample_background(img, wm_x1, wm_y1, wm_x2, wm_y2):
    """Sample background brightness from a ring around the watermark region."""
    h, w = img.shape[:2]
    pad = 30
    ring = img[max(0,wm_y1-pad):min(h,wm_y2+pad), max(0,wm_x1-pad):min(w,wm_x2+pad)]
    ring_mask = np.ones(ring.shape[:2], bool)
    ry = pad if wm_y1>=pad else wm_y1
    rx = pad if wm_x1>=pad else wm_x1
    ring_mask[ry:ry+(wm_y2-wm_y1), rx:rx+(wm_x2-wm_x1)] = False
    bg_pixels = ring[ring_mask]
    if len(bg_pixels) == 0:
        return 50.0
    bg_gray = cv2.cvtColor(bg_pixels.reshape(-1,1,3).astype(np.uint8),
                            cv2.COLOR_BGR2GRAY).flatten()
    return float(np.median(bg_gray))

def inpaint_residual(img, fixed_mask, wm_x1, wm_y1, wm_x2, wm_y2, bg_brightness):
    """
    Within fixed_mask area, find pixels still significantly above background
    and inpaint them using the fixed mask (not re-thresholded per frame).
    """
    region = img[wm_y1:wm_y2, wm_x1:wm_x2]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)

    # Residual = pixels inside the diamond mask that are still too bright
    threshold = bg_brightness + 25
    residual = ((gray > threshold) & (fixed_mask > 0)).astype(np.uint8) * 255

    if residual.sum() == 0:
        return img, False  # nothing to fix

    # Use the full fixed mask for inpainting (cleaner edges than just residual pixels)
    h, w = img.shape[:2]
    full_mask = np.zeros((h, w), np.uint8)
    full_mask[wm_y1:wm_y2, wm_x1:wm_x2] = fixed_mask

    pad = 20
    ry1, ry2 = max(0,wm_y1-pad), min(h,wm_y2+pad)
    rx1, rx2 = max(0,wm_x1-pad), min(w,wm_x2+pad)
    sub = img[ry1:ry2, rx1:rx2].copy()
    sub_mask = full_mask[ry1:ry2, rx1:rx2]
    inpainted = cv2.inpaint(sub, sub_mask, 3, cv2.INPAINT_TELEA)
    result = img.copy()
    result[ry1:ry2, rx1:rx2] = inpainted
    return result, True

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

        print("Building fixed diamond mask from reference frame...")
        fixed_mask = build_fixed_mask(frames_dir, frames, wm_x1, wm_y1, wm_x2, wm_y2)

        residual_count = 0
        print("Processing: GWT snap on every frame, fixed-mask residual cleanup...")
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

            # Step 2: Measure background, then check/fix residual using fixed mask
            bg = sample_background(img_after, wm_x1, wm_y1, wm_x2, wm_y2)
            result, had_residual = inpaint_residual(img_after, fixed_mask,
                                                     wm_x1, wm_y1, wm_x2, wm_y2, bg)
            if had_residual:
                residual_count += 1

            cv2.imwrite(path, result)

            if (i+1) % 20 == 0 or (i+1) == len(frames):
                print(f"  {i+1}/{len(frames)}  (residual cleanups: {residual_count})")

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
    print(f"{residual_count}/{len(frames)} frames needed residual cleanup")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("input"); p.add_argument("output", nargs="?")
    args = p.parse_args()
    out = args.output or args.input.replace(".mp4","_clean.mp4")
    process(args.input, out)
