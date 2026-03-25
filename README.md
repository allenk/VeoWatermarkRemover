# Veo Watermark Remover

[![Download](https://img.shields.io/github/v/release/allenk/VeoWatermarkRemover?label=Download&color=brightgreen)](https://github.com/allenk/VeoWatermarkRemover/releases/latest)
[![Demo](https://img.shields.io/badge/Status-Demo%20Build-orange.svg)](#demo-build-notice)
[![Platform](https://img.shields.io/badge/Platform-Windows%20x64-blue.svg)](#system-requirements)
[![Based on GWT](https://img.shields.io/badge/Based%20on-GeminiWatermarkTool-green.svg)](https://github.com/allenk/GeminiWatermarkTool)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/allenk/GeminiWatermarkTool/blob/main/LICENSE)

> **This is a demo/preview build of the upcoming Veo watermark removal feature for [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool).**
> Once stabilized, this functionality will be merged into the main GWT release with full cross-platform support.

Remove the "Veo" text watermark from Google Veo-generated videos using **mathematically precise reverse alpha blending** — the same proven technique behind [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool).

No cloud services. No AI hallucination. No quality loss. Just math.

## How It Works

![Drag & Drop Demo](artworks/veo-watermark-remover.gif)

**Just drag and drop.** Drop your Veo video onto the executable — it automatically removes the watermark and outputs `video_processed.mp4` with audio preserved.

### Before / After

![Side by Side Comparison](artworks/GWT_VEO_Watermark_Removal_Demo.gif)

## Quick Start

### Drag & Drop (Easiest)

1. Download `GeminiWatermarkTool.exe` (see [Download](#download) below)
2. Drag your `.mp4` file onto the exe
3. Done — output appears as `yourfile_processed.mp4` in the same folder

### Command Line

```bash
# Simplest — auto-detect, auto-output
GeminiWatermarkTool.exe video.mp4

# Specify output path
GeminiWatermarkTool.exe -i video.mp4 -o cleaned.mp4

# Explicit Veo mode (same result)
GeminiWatermarkTool.exe --veo -i video.mp4 -o cleaned.mp4
```

## Features

- **Single executable** — 36 MB standalone, zero dependencies, zero installation
- **Direct mp4-to-mp4** — no intermediate files, no external tools needed
- **Audio preserved** — original audio track is kept without re-encoding
- **AI denoise** — GPU-accelerated FDnCNN cleanup for residual artifacts (Vulkan)
- **Fast** — 720p at ~50 fps, 1080p at ~18 fps (Release build, Ryzen 9 + RTX)
- **Supports 720p and 1080p** — auto-detects resolution and applies correct mask

## Technical Details

This tool uses the same **reverse alpha blending** algorithm as [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool):

```
original = (watermarked - alpha * logo_value) / (1 - alpha)
```

The Veo watermark alpha maps were extracted using frame differencing from dark-background Veo videos, with background correction for non-zero pixel values. AI denoise (FDnCNN, NCNN + Vulkan GPU) handles residual edge artifacts.

For the full technical background on reverse alpha blending, see:
**[Removing Gemini AI Watermarks: A Deep Dive into Reverse Alpha Blending](https://allenkuo.medium.com/removing-gemini-ai-watermarks-a-deep-dive-into-reverse-alpha-blending-bbbd83af2a3f)**

## System Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Windows 10/11 x64 |
| GPU | Vulkan-capable GPU (NVIDIA, AMD, Intel) for Denoise Algorithm Accerlated (or fallback to slower CPU) |
| RAM | 4 GB minimum |
| Disk | 36 MB for the executable |

> **Note:** AI denoise runs on Vulkan GPU. If no Vulkan GPU is available, the tool still works.

## Download

> **Single file download — no installer, no setup.**

| File | Size | Description |
|------|------|-------------|
| `GeminiWatermarkTool.exe` | 36 MB | Standalone executable (Windows x64) |

### Verification

To verify the download integrity, check the hash values:

```
SHA256: 2c2180f5c096cc4f13f4753338e3419c9c01f89fbfefd80640874be7918b47f0
MD5:    9f7de5fb4a31552a495d702ea29bc03d
```

You can verify with PowerShell:
```powershell
Get-FileHash .\GeminiWatermarkTool.exe -Algorithm SHA256
```

### VirusTotal

**0 detections / 72 engines** — verified clean.

[View full VirusTotal report](https://www.virustotal.com/gui/file/2c2180f5c096cc4f13f4753338e3419c9c01f89fbfefd80640874be7918b47f0/detection)

> **If you're not comfortable running an unsigned executable, that's completely fine.**
> This is a demo build for early testing. The Veo removal feature will be integrated into the main [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) release when ready, with full source code, CI/CD builds, and cross-platform support.

## Demo Build Notice

This is a **preview/demo build** with the following limitations:

- **Windows x64 only** — Linux and macOS support will come with the main GWT release
- **CLI only** — GUI support is planned for the main GWT release
- **Video only** — this build processes video files (.mp4/.mkv/.mov); for Gemini image watermarks, use the main [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool)

### What's Next

When the Veo feature is stable and cross-platform ready, it will be merged into [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) as a unified release supporting both Gemini image and Veo video watermark removal.

## About GeminiWatermarkTool

[GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) is an open-source tool for removing Gemini AI visible watermarks from images. It supports GUI + CLI dual-mode operation, cross-platform deployment (Windows / Linux / macOS / Android), and optional AI denoise with NCNN + Vulkan GPU acceleration.

**Author:** Allen Kuo ([@allenk](https://github.com/allenk))

## License

This demo build is based on [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) (MIT License).

It includes third-party open-source components (NCNN, OpenCV, etc.) under their respective permissive licenses. Full license texts are available in the respective project repositories.
