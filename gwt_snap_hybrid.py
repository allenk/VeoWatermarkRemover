#!/usr/bin/env python3
"""
Watermark removal (v14) — patch-copy with feathered blend.

For each frame:
1. Detect the bright watermark pixels (threshold = background + 20, small dilation).
2. Build a non-watermark boundary mask (outer ring of the diamond, clean fabric).
3. Use cv2.matchTemplate (masked, fast) to find the best-matching fabric patch
   in the surrounding shirt region.
4. Copy that patch over the watermark area.
5. Feather the seam: inside the watermark mask → 100% patch; outside in a
   12 px ring → smooth patch→original blend (fabric-to-fabric, no bright pixels).

Falls back to TELEA inpaint if no good patch is found (SSD too high).
"""
import os, sys, subprocess, tempfile
import cv2, numpy as np

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
    roi_x, roi_y = w-220, h-250
    roi = img[roi_y:h, roi_x:w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    bright = (gray > 80).astype(np.uint8)
    coords = np.where(bright > 0)
    if not len(coords[0]): return None
    y_min, y_max = coords[0].min(), coords[0].max()
    x_min, x_max = coords[1].min(), coords[1].max()
    pad = 40
    return (max(0, roi_x+x_min-pad), max(0, roi_y+y_min-pad),
            min(w, roi_x+x_max+pad) - max(0, roi_x+x_min-pad),
            min(h, roi_y+y_max+pad) - max(0, roi_y+y_min-pad))

def remove_watermark(img, wm_x1, wm_y1, wm_x2, wm_y2):
    h, w = img.shape[:2]
    dh, dw = wm_y2-wm_y1, wm_x2-wm_x1

    # ── 1. Sample background brightness from ring around diamond ──────────────
    pad = 35
    ry1, ry2 = max(0, wm_y1-pad), min(h, wm_y2+pad)
    rx1, rx2 = max(0, wm_x1-pad), min(w, wm_x2+pad)
    ring_crop = img[ry1:ry2, rx1:rx2]
    ring_mask = np.ones(ring_crop.shape[:2], bool)
    iy = wm_y1-ry1; ix = wm_x1-rx1
    ring_mask[iy:iy+dh, ix:ix+dw] = False
    bg_pixels = ring_crop[ring_mask]
    if len(bg_pixels) == 0:
        bg = 50.0
    else:
        bg = float(np.median(cv2.cvtColor(bg_pixels.reshape(-1,1,3).astype(np.uint8),
                                          cv2.COLOR_BGR2GRAY).flatten()))

    # ── 2. Build watermark mask (bright pixels inside diamond area) ───────────
    region = img[wm_y1:wm_y2, wm_x1:wm_x2]
    gray   = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    # Lower threshold + larger dilation to catch semi-transparent edge pixels
    wm_mask = (gray > bg + 12).astype(np.uint8)
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    wm_mask = cv2.dilate(wm_mask, k5, iterations=2)
    if wm_mask.sum() == 0:
        return img  # nothing to remove

    # ── 3. Build non-watermark boundary for template matching ─────────────────
    k15 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15,15))
    outer_ring = cv2.dilate(wm_mask, k15) - wm_mask   # clean fabric ring outside diamond
    match_mask = outer_ring.astype(np.uint8) * 255     # only match on these known-good pixels

    templ = region.copy()                              # full dh×dw template
    templ_gray = cv2.cvtColor(templ, cv2.COLOR_BGR2GRAY)

    # ── 4. Search for best patch using matchTemplate (masked, fast) ───────────
    # Search ABOVE the watermark (same shirt, same vertical column) — avoids
    # the person's arm/hand that can enter from the left at later timestamps.
    # Keep vertical range tight (≤100 px) so we don't reach neck/beads/off-fabric.
    search_x_lo = max(0,   wm_x1 - 60)
    search_x_hi = min(w - dw, wm_x2 + 10)
    search_y_lo = max(0,   wm_y1 - 100)
    search_y_hi = wm_y1 - 15              # stop well before the watermark row

    # Sample background color (BGR) from the ring for color-consistency check
    bg_bgr = np.median(ring_crop[ring_mask].reshape(-1,3).astype(float), axis=0)  # [B,G,R]

    def _find_patch(sx1, sx2, sy1, sy2):
        if sx2 - sx1 < dw or sy2 - sy1 < dh:
            return None
        sr = cv2.cvtColor(img[sy1:sy2+dh, sx1:sx2+dw], cv2.COLOR_BGR2GRAY).astype(np.float32)
        try:
            res = cv2.matchTemplate(sr, templ_gray.astype(np.float32),
                                    cv2.TM_SQDIFF, mask=match_mask.astype(np.float32))
            _, _, mloc, _ = cv2.minMaxLoc(res)
            return (sx1 + mloc[0], sy1 + mloc[1])
        except Exception:
            return None

    best_loc = _find_patch(search_x_lo, search_x_hi, search_y_lo, search_y_hi)
    # Fallback: also try left of watermark if above search fails validation
    best_loc_left = _find_patch(max(dw, wm_x1-320), wm_x1-dw-10,
                                max(0, wm_y1-150), min(h-dh, wm_y2+150))

    def _patch_valid(bx, by):
        """Return patch if its brightness AND color match the background."""
        if bx is None or by is None: return None
        if by+dh > h or bx+dw > w: return None
        if bx == wm_x1 and by == wm_y1: return None
        p = img[by:by+dh, bx:bx+dw].copy()
        pg = cv2.cvtColor(p, cv2.COLOR_BGR2GRAY).astype(float)
        if abs(pg.mean() - bg) > 20: return None          # brightness check
        p_bgr = np.median(p.reshape(-1,3).astype(float), axis=0)
        if np.max(np.abs(p_bgr - bg_bgr)) > 15: return None  # per-channel color check
        return p

    best_patch = (_patch_valid(*best_loc) if best_loc else None or
                  _patch_valid(*best_loc_left) if best_loc_left else None)

    # ── 5. Copy best patch with feathered blend ───────────────────────────────
    if best_patch is not None:
        # Feather: 1.0 inside mask, smooth 1→0 in 12px ring outside mask
        dist_out  = cv2.distanceTransform(1-wm_mask, cv2.DIST_L2, 3)
        feather   = np.where(wm_mask > 0, 1.0, np.clip(1.0 - dist_out/12.0, 0.0, 1.0))
        feather_3 = np.stack([feather]*3, axis=2)
        blended   = (best_patch.astype(float) * feather_3 +
                     region.astype(float) * (1.0 - feather_3))
        result_img = img.copy()
        result_img[wm_y1:wm_y2, wm_x1:wm_x2] = np.clip(blended, 0, 255).astype(np.uint8)
        return result_img

    # ── 6. Fallback: TELEA inpaint ────────────────────────────────────────────
    full_mask = np.zeros((h, w), np.uint8)
    full_mask[wm_y1:wm_y2, wm_x1:wm_x2] = wm_mask * 255
    sub  = img[ry1:ry2, rx1:rx2].copy()
    inp  = cv2.inpaint(sub, full_mask[ry1:ry2, rx1:rx2], 7, cv2.INPAINT_TELEA)
    res  = img.copy()
    res[ry1:ry2, rx1:rx2] = inp
    return res

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
        wm_x1, wm_y1, wm_x2, wm_y2 = rx+40, ry+40, rx+rw-40, ry+rh-40
        print(f"Watermark region: ({wm_x1},{wm_y1})-({wm_x2},{wm_y2})")

        print("Processing: patch-copy + feather blend ...")
        for i, fname in enumerate(frames):
            path = os.path.join(frames_dir, fname)
            img  = cv2.imread(path)
            result = remove_watermark(img, wm_x1, wm_y1, wm_x2, wm_y2)
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
