# Veo Watermark Remover

[![Download](https://img.shields.io/github/v/release/allenk/VeoWatermarkRemover?label=Download&color=brightgreen)](https://github.com/allenk/VeoWatermarkRemover/releases/latest)
[![Demo](https://img.shields.io/badge/Status-Demo%20Build-orange.svg)](#demo-build-notice)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-blue.svg)](#download)
[![Based on GWT](https://img.shields.io/badge/Based%20on-GeminiWatermarkTool-green.svg)](https://github.com/allenk/GeminiWatermarkTool)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/allenk/GeminiWatermarkTool/blob/main/LICENSE)
[![Support on Ko-fi](https://img.shields.io/badge/Support-Ko--fi-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/allenkoss)
[![Support via PayPal](https://img.shields.io/badge/Support-PayPal-00457C?logo=paypal&logoColor=white)](https://paypal.me/allenkoss)

> **NEW: Watch the demo video on YouTube — [Veo Watermark Remover in Action](https://www.youtube.com/watch?v=bPDhD67C_rI)**

> [!WARNING]
> **This is a DEMO/PREVIEW build** — CLI only, unsigned executable, early testing phase.
> See [Demo Build Notice](#demo-build-notice) for details and known limitations.
> **Windows/macOS may block the executable on first run — see [First Run — OS Security Prompts](#first-run--os-security-prompts) below.**

This is a **demo/preview build** of the upcoming Veo watermark removal feature for [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool). Once stabilized, this functionality will be merged into the main GWT release with full GUI support.

Remove the "Veo" text watermark from Google Veo-generated videos using **mathematically precise reverse alpha blending** — the same proven technique behind [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool).

No cloud services. No generative fill, no hallucinated pixels, no quality loss — the removal is pure, reversible math. An optional on-device ML assist (`--ml`) can fine-tune the intensity on tricky clips.

## What's New (v0.6.5)

- **Half-scale "stamped" diamonds are now found and removed** ([#31](https://github.com/allenk/VeoWatermarkRemover/issues/31)). Some newer clips (free-tier / API-stamped outputs) carry a much smaller diamond — about half the usual size, at a nonstandard corner position. Previous versions could lock onto look-alike scene content nearby and report success while the real watermark stayed put. The smart search now scans down to these small sizes and holds candidates to a stricter, data-calibrated bar, so the real diamond wins.
- **`--region x,y,w,h` now works on video.** When a watermark sits somewhere auto-detect doesn't know yet, you can lock the exact spot yourself (find it with the GUI snap tool or by eye) and pair it with `--veo-alpha` for intensity — e.g. `--region "1221,656,22,22" --veo-alpha 0.98`. No `--region` = unchanged auto behavior.
- **Fewer missed frames on bright, busy backgrounds.** The "watermark is occluded, skip this frame" guard now accounts for how faint a watermark *physically can be* over a bright background (ocean foam, snow) instead of using a fixed bar — a fully visible diamond no longer slips through on a single frame.
- **Fix for "diamond turns black" on old Intel iGPUs** ([#28](https://github.com/allenk/VeoWatermarkRemover/issues/28)). On systems whose Vulkan driver is present but broken (Mesa warns "Haswell Vulkan support is incomplete"), the AI denoise step could output a black patch. Device selection now skips broken and software-emulated Vulkan devices (llvmpipe/lavapipe & friends) and falls back to the fast native CPU path automatically. You can also force CPU outright with the new `--cpu` flag (or `GWT_CPU_DENOISE=1` for scripts).

## Previous Release Highlights (v0.6.4)

- **More stable by default — the ML assist is now opt-in (`--ml`).** v0.6.3 turned the "Alpha Judge" ML intensity predictor on by default. Across the huge variety of real-world clips, though, it occasionally over-corrected and made a clip *worse* than the plain analytical estimate. So the default is back to the **proven, predictable analytical intensity** — reliable for the common case — and Alpha Judge is now a one-flag opt-in (`--ml`) for the minority of clips whose intensity genuinely varies a lot. By default the tool no longer spins up the GPU for ML either, so it starts clean on more systems.
- **New "Veo" text — more reliable detection + 1080p support.** Fixed a case where a clip with the small "Veo" text over a busy foreground (e.g. shot through grass) was misread as the Gemini diamond and left the text in place ([#18](https://github.com/allenk/VeoWatermarkRemover/issues/18)) — it's now identified correctly. Also added the **1080p** small "Veo" wordmark (v0.6.3 handled 720p only).

## Previous Release Highlights (v0.6.3)

- **Alpha Judge ML intensity assist (now opt-in via `--ml`).** A small neural network (DNN) that runs entirely on your own machine and predicts the removal intensity from the video, combined with the analytical estimator. Helps clips whose intensity varies a lot; 100% offline, nothing uploaded. (Off by default since v0.6.4 — see above.)
- **Small "Veo" text watermark removal.** Google's **Flow** generator stamps a small "Veo" wordmark in the bottom-right corner of its newest outputs. The tool auto-detects which watermark a clip carries (the Gemini diamond or the small Veo text) and removes the right one — no flags, landscape or portrait.

## Previous Release Highlights (v0.6.2)

- **Auto-detects the relocated watermark.** Newer Veo portrait outputs
  (1080×1920, 720×1280) moved the diamond further in from the corner,
  and v0.6.1 didn't recognise the new spot — it SKIPped those files
  ([#14](https://github.com/allenk/VeoWatermarkRemover/issues/14),
  [#16](https://github.com/allenk/VeoWatermarkRemover/issues/16)).
  v0.6.2 adds the new positions AND a **smart bottom-right search** that
  finds the diamond wherever it sits (matching its shape across several
  frames and requiring them to agree on the position). If the position
  shifts again, the tool locates it **without needing an update** — the
  fixed positions are just a fast path, the search is the safety net.
- **Fixes the "dark hole" over-removal on bright backgrounds.** When the
  watermark drifted across a lit hand, skin, or a bright sky, the
  per-frame estimator could over-shoot and over-subtract, leaving a dark
  crater for a run of frames. v0.6.2 anchors each frame's intensity to
  the stable per-shot value and rejects physically-implausible
  estimates, so removal stays clean across the whole clip even as the
  background changes.
- **Keeps partially-occluded frames** ([#5](https://github.com/allenk/VeoWatermarkRemover/issues/5)).
  When a foreground object partly covers the diamond, the watermark is
  still there underneath — but v0.6.1 could read the low match score as
  "no watermark" and skip those frames, leaving it visible. v0.6.2 adds
  a three-tier confidence gate: high-confidence frames are tuned per
  frame, low-confidence frames get the shot's consensus intensity
  applied instead of being skipped, and only genuinely watermark-free
  frames pass through untouched.
- **Smarter 1080p intensity** ([#2](https://github.com/allenk/VeoWatermarkRemover/issues/2)).
  1080p previously used a fixed intensity, but some clips need a
  noticeably stronger one. v0.6.2 measures the correct intensity per
  shot with a more accurate least-squares estimator (~20% closer to the
  ideal value), while staying flicker-free on 1080p by locking one value
  for the whole shot.

## Previous Release Highlights (v0.6.1)

- **Survives intro fade-ins.** Many community-supplied 720p clips
  start with a brief fade-in or splash where the watermark isn't yet
  composited, and v0.6.0 saw NCC = 0 on frame 0 and SKIPped the whole
  file. v0.6.1 probes 12 frames spread across the video's first 90%
  and picks the best (sample, tuple) pair, so fade-ins no longer
  cause a false SKIP. Five previously-skipped community samples now
  auto-detect cleanly.
- **Adaptive per-frame alpha refinement.** The new
  [bisection feedback loop](#how-it-handles-difficult-clips) doesn't
  just estimate the alpha intensity — it APPLIES the candidate value,
  evaluates whether the result looks like the surrounding background,
  and adjusts up (residue remained) or down (dark hole) for up to
  five rounds per frame. Visual-consistency goal rather than pure
  prediction, so clips with foreground motion or heterogeneous
  backgrounds get a per-frame scale that actually fits.
- **Per-shot seed + per-frame change cap.** A stable per-video
  baseline (median of 12 sample-frame estimates) anchors the
  bisection, and a small per-frame change cap (±0.05) prevents any
  single bad assessment from causing a visible flash. Output stays
  smooth even on content where the bisection metric is locally noisy.
- **`--variant 720p-1` / `--variant 720p-2` escape hatch in the
  SKIP hint.** When auto-detect can't lock on, the SKIP message
  now suggests the manual override flags directly. Useful for clips
  that auto fails on (rare with v0.6.1's multi-frame probe, but the
  escape hatch is documented).
- **Honest limit acknowledged.** Some clips with very strong
  per-frame content motion (medical illustrations with hair strands,
  rapid-cut animation, etc.) still produce a small residue on a few
  frames. See
  [Manual touch-up workflow](#manual-touch-up-workflow-for-difficult-clips)
  below for the recommended workflow when the automatic result isn't
  good enough.

## Previous Release Highlights (v0.6.0)

- **720p Gemini 3.5 diamond removal — now auto-detected.** Both
  geometries observed in real Veo 720p outputs are calibrated:
  720p-1 standard (48×48 at margin 72,72, ~1.5 Mbps tier) and
  720p-2 compact (44×44 at margin 29,40, ~7 Mbps tier). Auto-detect
  picks the right one via NCC scoring.
- **Dynamic per-frame alpha estimation.** First release with
  per-frame alpha intensity recovery instead of a static multiplier.
  v0.6.1 evolved this into the adaptive bisection above.
- **Position refinement at video startup.** A ±4 px local NCC
  search around the tuple anchor snaps to the actual diamond
  position, absorbing encoding-tier drift without recalibration.
- **Transcoder timing fidelity.** Output frame count, duration, and
  FPS metadata match input exactly — no more silently dropping tail
  frames or shifting duration. Three classic libavcodec API misuses
  (decoder flush, packet duration stamping, frame-rate metadata
  propagation) fixed in one go.
- **Quieter default output** — FFmpeg container parser warnings
  (e.g. the `Unknown cover type: 0x1` line emitted on C2PA-tagged
  Veo videos) suppressed at default verbosity.

### Help Wanted: Other Resolutions

If you have a Gemini 3.5 video at **4K**, **square 1:1**, **9:16
short-form**, or any resolution not in 1080p / 720p, please
[open an issue](https://github.com/allenk/VeoWatermarkRemover/issues)
with a sample so we can calibrate that size too. The diamond shape
is consistent across resolutions; we mainly need the position and
size for each new encoding profile.

## Previous Release Highlights (v0.5.0)

- **Gemini 3.5 diamond watermark removal (1080p)** — the first
  release to handle Gemini 3.5's new diamond watermark by default
  (no flag needed). 1920×1080 landscape and 1080×1920 portrait
  validated end-to-end against community samples
  ([issue #2](https://github.com/allenk/VeoWatermarkRemover/issues/2),
  [#3](https://github.com/allenk/VeoWatermarkRemover/issues/3)).
- **`--legacy` flag for older Veo videos** — videos generated before
  Gemini 3.5 (with the "Veo" text watermark) need `--legacy`;
  the diamond and the text are different shapes at different
  positions, so applying the wrong removal would damage the frame.
- **No fallback between profiles** — if a diamond-mode result still
  shows the old "Veo" text, the video is pre-Gemini-3.5 — re-run
  with `--legacy`.
- **Tighter encode** — CRF 14 / preset slow (was 18 / medium). PSNR
  improved by ~2-3 dB on encoding-only regions; visually identical
  to source on most content.

## Previous Release Highlights (v0.4.0)

- **macOS stability fix** — addresses the SIGBUS crash on Apple Silicon reported in upstream GeminiWatermarkTool [#30](https://github.com/allenk/GeminiWatermarkTool/issues/30) / [#31](https://github.com/allenk/GeminiWatermarkTool/issues/31). The Vulkan loader is probed before NCNN's GPU init; if it's absent (the default on macOS without MoltenVK), AI denoise transparently falls back to CPU instead of crashing
- **`--snap-min-size`** — finer snap-search control on the image-watermark side (default 16, range 8-64), mirroring the existing `--snap-max-size` flag
- **End-to-end CI smoke test** — every CI build now runs `--denoise ai` through a real inference pipeline (Windows / Linux / macOS) before publishing. The previous `--version`-only check never touched the AI denoise init path, which is how the macOS crash slipped past CI in v0.3.0

## Previous Release Highlights (v0.3.0)

- **Improved watermark masks** — remastered 720p and 1080p alpha maps using golden frame-differencing from multiple video sources (10+ transition pairs)
- **Better output quality** — upgraded video encoder (High profile, B-frames, multi-reference)
- **Enhanced AI cleanup** — tuned per-resolution denoise parameters with expanded inference context
- **Progress bar** — real-time ASCII progress indicator during video processing
- **Quieter output** — reduced log verbosity in normal mode; use `--verbose` for detailed diagnostics

## How It Works

![Drag & Drop Demo](artworks/veo-watermark-remover.gif)

**Just drag and drop.** Drop your Veo video onto the executable — it automatically removes the watermark and outputs `video_processed.mp4` with audio preserved.

### Before / After

![Side by Side Comparison](artworks/GWT_VEO_Watermark_Removal_Demo.gif)

## Quick Start

### Drag & Drop (Windows — Easiest)

1. Download `GeminiWatermarkTool-Video.exe` (see [Download](#download) below)
2. Drag your `.mp4` file onto the exe
3. Done — output appears as `yourfile_processed.mp4` in the same folder

### Command Line (All Platforms)

```bash
# Simplest — auto-detects the watermark (Gemini diamond OR the new "Veo" text)
./GeminiWatermarkTool-Video video.mp4

# Older, larger "Veo" text from pre-Gemini-3.5 videos
./GeminiWatermarkTool-Video --legacy old_veo_video.mp4

# Specify output path
./GeminiWatermarkTool-Video -i video.mp4 -o cleaned.mp4

# Enable the ML intensity assist (opt-in) for a clip whose intensity varies a lot
./GeminiWatermarkTool-Video --ml video.mp4

# Pre-3.5 with explicit input / output
./GeminiWatermarkTool-Video --legacy -i old_video.mp4 -o cleaned.mp4

# Force a specific 720p variant if auto-detect picks wrong (rare):
./GeminiWatermarkTool-Video --variant 720p-1 video.mp4   # 48x48 standard
./GeminiWatermarkTool-Video --variant 720p-2 video.mp4   # 44x44 compact
```

> **Which mode do I need?**
>
> - **Just run it — no flags.** The tool auto-detects what a clip carries — the **Gemini diamond** (Gemini 3.5 and later) or the **new small "Veo" text** (Google Flow's latest outputs) — and removes the right one, in landscape or portrait.
> - **`--legacy`** is only for the **older, larger "Veo" text** from pre-Gemini-3.5 videos. New outputs don't need it.

## How It Handles Difficult Clips

The v0.6.1 adaptive loop runs once per frame and behaves like a small
auto-tuner. For each frame:

1. Compute the per-frame NCC against the calibrated diamond template.
   If NCC is below the gate (heavy foreground occlusion), the frame
   is left untouched — leaving the diamond visible on those few
   frames is more honest than scribbling synthetic content over them.
2. Sample the local background ring around the watermark region.
3. Pick a candidate alpha intensity (starting from the per-shot
   seed value learned from the first 12 sample frames).
4. APPLY the candidate, measure whether the resulting region matches
   the surrounding background:
   - **Brighter than surroundings → residue still present →
     increase intensity.**
   - **Darker than surroundings → over-subtracted (dark hole) →
     decrease intensity.**
5. Up to 5 bisection rounds. The change between adjacent frames is
   capped at ±0.05 so any single bad assessment can't cause a
   visible flash.

The goal is **visual consistency with the local context**, not a
prediction of some "true" alpha value. Same content + same diamond →
same removal. Different scenes within a clip get different per-frame
intensities, but each is correct for its own surroundings.

## Manual Touch-Up Workflow for Difficult Clips

The automatic pipeline handles **most** Gemini 3.5 video samples
cleanly, but some content classes still resist a fully automatic
solution — heavy per-frame motion, foreground objects overlapping
the watermark region, medical-illustration backgrounds with
high-frequency detail next to the diamond, etc. If you run a video
through v0.6.1 and a small number of frames still show residue or
a faint outline, the practical workflow is:

```bash
# 1. Run the automatic pipeline first
GeminiWatermarkTool-Video video.mp4

# 2. Decompose the auto-processed output into individual frames
ffmpeg -i video_processed.mp4 frames/frame_%04d.png

# 3. Open GUI mode (image-side GeminiWatermarkTool) on the problem
#    frames only. Use Custom region mode and tune the Alpha intensity
#    slider until that frame looks clean. Save the touched-up PNG
#    back to the same path.
#    (See https://github.com/allenk/GeminiWatermarkTool for the GUI
#    build that ships the Alpha intensity slider in Custom mode.)

# 4. Re-encode the frames back into a video, copying audio from the
#    original
ffmpeg -framerate 24 -i frames/frame_%04d.png \
       -i video.mp4 -map 0:v -map 1:a \
       -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p \
       -c:a copy \
       video_touched_up.mp4
```

For most clips you'll only need to manually fix a handful of frames.
The GUI's Custom-mode Alpha intensity slider lets you dial in the
exact value visually; values around `0.55-0.70` (V1-relative) cover
most current Gemini 3.5 720p content.

### Sigma Tuning Tips

The default AI denoise sigma is tuned for photographic / video
content (sigma = 50 for 1080p, sigma = 20 for 720p Veo). If your
output looks too blurry or has slight unnatural artifacts on
illustration / animation content, try a **smaller sigma**:

```bash
# Anime / illustration content often looks best with sigma ~15
GeminiWatermarkTool-Video --sigma 15 video.mp4

# Photographic content where AI denoise is too aggressive
GeminiWatermarkTool-Video --sigma 25 video.mp4
```

Lower sigma = less smoothing = sharper output but residual H.264
ringing artifacts may stay visible near the WM edges. Higher sigma
= more smoothing = cleaner edges but slight loss of detail. The
defaults are a compromise; for content classes with distinct
aesthetics, manual tuning helps.

## Features

- **Single executable** — standalone, zero dependencies, zero installation
- **Cross-platform** — Windows, Linux, and macOS (Universal Binary)
- **Direct mp4-to-mp4** — no intermediate files, no external tools needed
- **Audio preserved** — original audio track is kept without re-encoding
- **AI denoise** — GPU-accelerated FDnCNN cleanup for residual artifacts (Vulkan)
- **Gemini 3.5 diamond removal** (default, v0.5.0+) — handles the new
  watermark layout out of the box; v0.6.0 adds 720p (both standard
  and compact variants) alongside 1080p
- **Relocated-watermark auto-detection** (v0.6.2+) — known positions
  plus a smart bottom-right search that finds the diamond wherever it
  moves, with cross-frame agreement to avoid false matches
- **Over-removal protection** (v0.6.2+) — per-frame intensity is
  anchored to the stable per-shot value, preventing the dark-hole
  artifact when the watermark crosses bright/low-contrast areas
- **Partial-occlusion handling** (v0.6.2+) — a three-tier confidence
  gate cleans frames where a foreground object partly covers the
  diamond instead of skipping them
- **Dynamic 1080p intensity** (v0.6.2+) — least-squares per-shot
  estimate replaces the old fixed multiplier, flicker-free
- **Adaptive per-frame alpha refinement** (v0.6.1+, 720p) — bisection
  feedback loop applies a candidate intensity, measures the result
  against the local background, and adjusts up/down per frame; the
  change between adjacent frames is capped to prevent visible
  flashes
- **Multi-frame detection probe** (v0.6.1+) — probes 12 frames
  across the video instead of just frame 0, so intro fade-ins no
  longer cause a false SKIP
- **Tick-exact transcoder timing** (v0.6.0+) — frame count,
  duration, and FPS metadata match input exactly; no drift in NLE /
  editor alignment
- **`--variant` escape hatch** — force a known 720p geometry if
  auto-detect can't lock on (very rare with v0.6.1)
- **`--sigma` for content-aware denoise** — lower for animation /
  illustration, higher for photographic content
- **Legacy "Veo" text removal** (`--legacy`) — for pre-Gemini-3.5
  videos; the previous default behaviour still available behind a
  single flag
- **Progress bar** — real-time processing progress in the terminal

## Technical Details

This tool uses the same **reverse alpha blending** algorithm as [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool):

```text
original = (watermarked - alpha * logo_value) / (1 - alpha)
```

The Veo watermark alpha maps were extracted using frame differencing from Veo-generated videos with watermark on/off transitions. Multiple golden pairs (Lightning flash, Light bulb, Sunrise scenes) were averaged for maximum accuracy. AI denoise (FDnCNN, NCNN + Vulkan GPU) handles residual edge artifacts from video compression.

For the full technical background on reverse alpha blending, see:
**[Removing Gemini AI Watermarks: A Deep Dive into Reverse Alpha Blending](https://allenkuo.medium.com/removing-gemini-ai-watermarks-a-deep-dive-into-reverse-alpha-blending-bbbd83af2a3f)**

## System Requirements

| Component | Requirement                                                         |
| --------- | ------------------------------------------------------------------- |
| OS        | Windows 10/11 x64, Linux x64, macOS (Intel + Apple Silicon)         |
| GPU       | Vulkan-capable GPU for AI Denoise acceleration (or fallback to CPU) |
| RAM       | 4 GB minimum                                                        |

> **Note:** AI denoise prefers a Vulkan GPU but transparently falls back to CPU when no Vulkan loader is available.
>
> **macOS users:** macOS does not ship Vulkan natively — install the [LunarG Vulkan SDK](https://vulkan.lunarg.com/) (which bundles MoltenVK) for GPU acceleration. Otherwise the tool runs in CPU mode by default; this is fully supported but slower than Vulkan inference.

## Download

> **Single file download — no installer, no setup.**

| Platform | File | Notes |
|----------|------|-------|
| **Windows x64** | `GeminiWatermarkTool-Video.exe` | Drag & drop supported |
| **Linux x64** | `GeminiWatermarkTool-Video` | `chmod +x` before running |
| **macOS Universal** | `GeminiWatermarkTool-Video` | Intel + Apple Silicon |

Download the latest release from the [Releases page](https://github.com/allenk/VeoWatermarkRemover/releases/latest).

### Verification & Safety

**Every release is built by GitHub Actions from this repository's public, MIT-licensed source** — in a clean, throwaway CI runner, with public build logs. No human ever touches the binary between source and release, so there is no step where anything could be tampered with. You can read the source, inspect the build workflow, and rebuild the exact binary yourself.

**Independent VirusTotal scans** for the v0.6.3 binaries — the SHA256 is in each link, so you can match it against the file you downloaded:

| Platform | VirusTotal scan |
|---|---|
| **Windows x64** | [virustotal.com/…de4ab955](https://www.virustotal.com/gui/file/e6a0fd8e1c6cbe26da02dafd8a1df4645ac35a565acab58e3171995dde4ab955) |
| **Linux x64** | [virustotal.com/…b43d74f9b](https://www.virustotal.com/gui/file/dd6d27547cee59555a87e720c8ef41c68373d78f94356cca31ab817b43d74f9b) |
| **macOS Universal** | [virustotal.com/…1def4d5e](https://www.virustotal.com/gui/file/b97c3c3d27c6c7e4e672e16b772a4e21ae4a93d4d15fcd6a6129ec441def4d5e) |

**About antivirus false positives.** The binaries are **unsigned**, and every new release is a brand-new file your antivirus has never seen. Heuristic / ML-based scanners are twitchy about unsigned executables with zero reputation, so a fresh release can occasionally trip a *generic* detection (a `Wacatac` / `AIDetect`-style label) even though nothing is wrong — it's about the file being new and unsigned, not about what the program does. If your antivirus flags it, match the SHA256 against the scans above, restore it from quarantine (or add an exclusion), or build it yourself from source. Proper code signing is on the roadmap to stop this recurring.

**Verify your download (SHA256):**

```bash
# Windows (PowerShell)
Get-FileHash .\GeminiWatermarkTool-Video.exe -Algorithm SHA256

# Linux / macOS
sha256sum GeminiWatermarkTool-Video
```

> **If you're not comfortable running an unsigned executable, that's completely fine.**
> This is a demo build for early testing. The Veo removal feature will be integrated into the main [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) release when ready, with full source code, CI/CD builds, and cross-platform support.

## First Run — OS Security Prompts

Downloaded binaries are not code-signed, so your OS may show a security warning on first launch. This is normal for open-source software distributed outside app stores.

<details>
<summary><b>Windows</b> — SmartScreen "Windows protected your PC"</summary>

**Option A:** Click **More info** → **Run anyway**.

**Option B (PowerShell):**

```powershell
Unblock-File .\GeminiWatermarkTool-Video.exe
```

</details>

<details>
<summary><b>macOS</b> — "Apple cannot check it for malicious software"</summary>

**Option A (recommended):** Right-click the binary → **Open** → click **Open** in the dialog. You only need to do this once.

**Option B (terminal):**

```bash
xattr -dr com.apple.quarantine GeminiWatermarkTool-Video
chmod +x GeminiWatermarkTool-Video
```

</details>

<details>
<summary><b>Linux</b> — No security prompt</summary>

Linux does not quarantine downloaded binaries. Just ensure the file is executable:

```bash
chmod +x GeminiWatermarkTool-Video
./GeminiWatermarkTool-Video video.mp4
```

</details>

## Demo Build Notice

This is a **preview/demo build** with the following limitations:

- **CLI only** — GUI support is planned for the main GWT release
- **Video only** — this build processes video files (.mp4/.mkv/.mov); for Gemini image watermarks, use the main [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool)

### What's Next

When the Veo feature is stable, it will be merged into [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) as a unified release supporting both Gemini image and Veo video watermark removal.

## About GeminiWatermarkTool

[GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) is an open-source tool for removing Gemini AI visible watermarks from images. It supports GUI + CLI dual-mode operation, cross-platform deployment (Windows / Linux / macOS / Android), and optional AI denoise with NCNN + Vulkan GPU acceleration.

**Author:** Allen Kuo ([@allenk](https://github.com/allenk))

## Support This Project

If this tool saved you time and you'd like to help keep it going, you can support via [Ko-fi](https://ko-fi.com/allenkoss) or [PayPal](https://paypal.me/allenkoss) — both go to the same place; pick whichever works for you (a few users have reported Ko-fi checkout issues from their region, so PayPal is the dependable fallback). Every public release goes through GitHub Actions CI on Windows / Linux / macOS, and the binary archives live in the Releases section — small contributions help cover runner minutes and storage so the project can keep building cross-platform binaries for free. Not required, just appreciated.

Bug reports, sample videos, and pull requests remain the most valuable contributions and always will be — if you don't have anything to send via Ko-fi, opening an [issue](https://github.com/allenk/VeoWatermarkRemover/issues) with a clip the tool can't handle is just as helpful (often more so).

## License

This demo build is based on [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) (MIT License).

It includes third-party open-source components (NCNN, OpenCV, etc.) under their respective permissive licenses. Full license texts are available in the respective project repositories.
