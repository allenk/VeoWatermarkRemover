# Veo Watermark Remover

[![Download](https://img.shields.io/github/v/release/allenk/VeoWatermarkRemover?label=Download&color=brightgreen)](https://github.com/allenk/VeoWatermarkRemover/releases/latest)
[![Demo](https://img.shields.io/badge/Status-Demo%20Build-orange.svg)](#demo-build-notice)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-blue.svg)](#download)
[![Based on GWT](https://img.shields.io/badge/Based%20on-GeminiWatermarkTool-green.svg)](https://github.com/allenk/GeminiWatermarkTool)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/allenk/GeminiWatermarkTool/blob/main/LICENSE)

> **This is a demo/preview build of the upcoming Veo watermark removal feature for [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool).**
> Once stabilized, this functionality will be merged into the main GWT release with full GUI support.

Remove the "Veo" text watermark from Google Veo-generated videos using **mathematically precise reverse alpha blending** — the same proven technique behind [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool).

No cloud services. No AI hallucination. No quality loss. Just math.

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
# Simplest — auto-detect, auto-output
./GeminiWatermarkTool-Video video.mp4

# Specify output path
./GeminiWatermarkTool-Video -i video.mp4 -o cleaned.mp4

# Explicit Veo mode (same result)
./GeminiWatermarkTool-Video --veo -i video.mp4 -o cleaned.mp4
```

## Features

- **Single executable** — standalone, zero dependencies, zero installation
- **Cross-platform** — Windows, Linux, and macOS (Universal Binary)
- **Direct mp4-to-mp4** — no intermediate files, no external tools needed
- **Audio preserved** — original audio track is kept without re-encoding
- **AI denoise** — GPU-accelerated FDnCNN cleanup for residual artifacts (Vulkan)
- **Fast** — 720p at ~50 fps, 1080p at ~18 fps (Release build, Ryzen 9 + RTX)
- **Landscape + Portrait** — supports both orientations at 720p and 1080p

## Technical Details

This tool uses the same **reverse alpha blending** algorithm as [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool):

```text
original = (watermarked - alpha * logo_value) / (1 - alpha)
```

The Veo watermark alpha maps were extracted using frame differencing from dark-background Veo videos, with background correction for non-zero pixel values. AI denoise (FDnCNN, NCNN + Vulkan GPU) handles residual edge artifacts.

For the full technical background on reverse alpha blending, see:
**[Removing Gemini AI Watermarks: A Deep Dive into Reverse Alpha Blending](https://allenkuo.medium.com/removing-gemini-ai-watermarks-a-deep-dive-into-reverse-alpha-blending-bbbd83af2a3f)**

## System Requirements

| Component | Requirement                                                         |
| --------- | ------------------------------------------------------------------- |
| OS        | Windows 10/11 x64, Linux x64, macOS (Intel + Apple Silicon)         |
| GPU       | Vulkan-capable GPU for AI Denoise acceleration (or fallback to CPU) |
| RAM       | 4 GB minimum                                                        |

> **Note:** AI denoise runs on Vulkan GPU. If no Vulkan GPU is available, the tool still works using CPU.

## Download

> **Single file download — no installer, no setup.**

| Platform | File | Size | Notes |
|----------|------|------|-------|
| **Windows x64** | `GeminiWatermarkTool-Video.exe` | 16 MB (zip) / 36 MB | Drag & drop supported |
| **Linux x64** | `GeminiWatermarkTool-Video` | 20 MB (zip) / 46 MB | `chmod +x` before running |
| **macOS Universal** | `GeminiWatermarkTool-Video` | 31 MB (zip) / 65 MB | Intel + Apple Silicon |

### Why is the Video build larger than standard GWT?

The standard [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) (image-only) is ~18 MB. The Video build adds ~18 MB for the embedded H.264 video codec (OpenH264, BSD license) and MP4 container support — a necessary cost for standalone mp4-to-mp4 processing without external dependencies.

macOS Universal is larger because it contains **two architectures** (x86_64 + ARM64) in a single binary.

### Verification

SHA256 checksums for each platform:

| Platform | SHA256 |
|----------|--------|
| Windows | `182f60c539a8ca5a236b481835c7f38e8a9c41f5ad6ec99281cf5c2e44de4a42` |
| Linux | *(see release page)* |
| macOS | *(see release page)* |

You can verify with:
```bash
# Windows (PowerShell)
Get-FileHash .\GeminiWatermarkTool-Video.exe -Algorithm SHA256

# Linux / macOS
sha256sum GeminiWatermarkTool-Video
```

### VirusTotal (Windows)

**0 detections / 72 engines** — verified clean.

[View full VirusTotal report](https://www.virustotal.com/gui/file/182f60c539a8ca5a236b481835c7f38e8a9c41f5ad6ec99281cf5c2e44de4a42)

> **If you're not comfortable running an unsigned executable, that's completely fine.**
> This is a demo build for early testing. The Veo removal feature will be integrated into the main [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) release when ready, with full source code, CI/CD builds, and cross-platform support.

## Demo Build Notice

This is a **preview/demo build** with the following limitations:

- **CLI only** — GUI support is planned for the main GWT release
- **Video only** — this build processes video files (.mp4/.mkv/.mov); for Gemini image watermarks, use the main [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool)

### What's Next

When the Veo feature is stable, it will be merged into [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) as a unified release supporting both Gemini image and Veo video watermark removal.

## About GeminiWatermarkTool

[GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) is an open-source tool for removing Gemini AI visible watermarks from images. It supports GUI + CLI dual-mode operation, cross-platform deployment (Windows / Linux / macOS / Android), and optional AI denoise with NCNN + Vulkan GPU acceleration.

**Author:** Allen Kuo ([@allenk](https://github.com/allenk))

## License

This demo build is based on [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) (MIT License).

It includes third-party open-source components (NCNN, OpenCV, OpenH264, etc.) under their respective permissive licenses. Full license texts are available in the respective project repositories.
