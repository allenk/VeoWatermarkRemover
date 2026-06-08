#!/usr/bin/env python3
"""
Hybrid watermark removal:
1. Build a fixed diamond mask from the best reference frame (dark background).
2. Run GWT snap on each frame for reverse alpha blending.
3. Check if GWT created a dark shadow artifact (over-subtracted the background).
   - If dark shadow detected: revert to original + fixed-mask inpaint (radius 15)
   - Otherwise: keep GWT result + fix any bright residual with fixed-mask inpaint
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
    roi_x, roi_y = w-220, h-250  # wider to avoid clipping diamond left edge
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
    """Find darkest-background frame, build Otsu mask there — reuse for all frames."""
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

def sample_background(img, wm_x1, wm_y1, wm_x2, wm_y2):
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

def gwt_dark_shadow(img_before, img_after, x1, y1, x2, y2, fixed_mask):
    """
    Detect if GWT over-subtracted and left a dark shadow patch.
    We look at pixels inside the fixed mask that got significantly darkened
    beyond what watermark removal should cause.
    """
    rb = img_before[y1:y2, x1:x2]
    ra = img_after[y1:y2, x1:x2]
    gb = cv2.cvtColor(rb, cv2.COLOR_BGR2GRAY).astype(int)
    ga = cv2.cvtColor(ra, cv2.COLOR_BGR2GRAY).astype(int)
    diff = ga - gb  # negative = darkened
    # Count mask pixels that got significantly darkened
    mask_bool = fixed_mask > 0
    darkened_in_mask = ((diff < -20) & mask_bool).sum()
    total_mask = mask_bool.sum()
    # If >30% of the mask pixels are over-darkened, GWT created a dark shadow
    return (darkened_in_mask / max(1, total_mask)) > 0.30

def inpaint_fixed_mask(img, fixed_mask, wm_x1, wm_y1, wm_x2, wm_y2, radius=15):
    """Inpaint the fixed diamond mask with given radius for texture reconstruction."""
    h, w = img.shape[:2]
    full_mask = np.zeros((h, w), np.uint8)
    full_mask[wm_y1:wm_y2, wm_x1:wm_x2] = fixed_mask
    pad = 30
    ry1, ry2 = max(0,wm_y1-pad), min(h,wm_y2+pad)
    rx1, rx2 = max(0,wm_x1-pad), min(w,wm_x2+pad)
    sub = img[ry1:ry2, rx1:rx2].copy()
    sub_mask = full_mask[ry1:ry2, rx1:rx2]
    inpainted = cv2.inpaint(sub, sub_mask, radius, cv2.INPAINT_TELEA)
    result = img.copy()
    result[ry1:ry2, rx1:rx2] = inpainted
    return result

def fix_residual(img_after, fixed_mask, wm_x1, wm_y1, wm_x2, wm_y2, bg_brightness):
    """Fix any bright residual after GWT (small inpaint radius, just residual pixels)."""
    region = img_after[wm_y1:wm_y2, wm_x1:wm_x2]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    residual = ((gray > bg_brightness + 15) & (fixed_mask > 0)).astype(np.uint8) * 255
    if residual.sum() == 0:
        return img_after
    h, w = img_after.shape[:2]
    full_mask = np.zeros((h, w), np.uint8)
    full_mask[wm_y1:wm_y2, wm_x1:wm_x2] = residual
    pad = 20
    ry1, ry2 = max(0,wm_y1-pad), min(h,wm_y2+pad)
    rx1, rx2 = max(0,wm_x1-pad), min(w,wm_x2+pad)
    sub = img_after[ry1:ry2, rx1:rx2].copy()
    sub_mask = full_mask[ry1:ry2, rx1:rx2]
    inpainted = cv2.inpaint(sub, sub_mask, 5, cv2.INPAINT_TELEA)
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

        gwt_ok = 0
        shadow_fixed = 0

        print("Processing: GWT snap, dark-shadow detection, fallback inpaint...")
        for i, fname in enumerate(frames):
            path = os.path.join(frames_dir, fname)
            img_before = cv2.imread(path)

            # GWT reverse alpha blending
            subprocess.run([GWT, "-i", path, "-o", path,
                "--snap", "--fallback-region", region_str,
                "--snap-threshold", "0.05",
                "--denoise", "ai"],
                capture_output=True)

            img_after = cv2.imread(path)

            # Check if GWT left a dark shadow in the mask area
            if gwt_dark_shadow(img_before, img_after, wm_x1, wm_y1, wm_x2, wm_y2, fixed_mask):
                # GWT over-subtracted — inpaint the original with large radius
                result = inpaint_fixed_mask(img_before, fixed_mask,
                                            wm_x1, wm_y1, wm_x2, wm_y2, radius=15)
                shadow_fixed += 1
            else:
                # GWT worked — fix any leftover bright residual
                bg = sample_background(img_after, wm_x1, wm_y1, wm_x2, wm_y2)
                result = fix_residual(img_after, fixed_mask,
                                      wm_x1, wm_y1, wm_x2, wm_y2, bg)
                gwt_ok += 1

            cv2.imwrite(path, result)

            if (i+1) % 20 == 0 or (i+1) == len(frames):
                print(f"  {i+1}/{len(frames)}  (gwt_ok={gwt_ok}, shadow_fixed={shadow_fixed})")

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
    print(f"Summary: {gwt_ok} frames GWT clean, {shadow_fixed} frames inpainted from original")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("input"); p.add_argument("output", nargs="?")
    args = p.parse_args()
    out = args.output or args.input.replace(".mp4","_clean.mp4")
    process(args.input, out)
