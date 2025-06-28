# PyClipper

**Quick-Cut Video Editor for YouTube and Social Media**  
_Fast, interactive video segment removal, overlays, captions, and advanced audio options using MoviePy 2.x+._

## Table of Contents

- [Overview](#Overview)
- [Features](#features)    
- [Requirements](#requirements)    
- [Installation](#installation)  
- [Quick Start](#quick-start)    
- [Usage](#usage)   
- [EDL Format](#edl-format)   
- [Audio Options](#audio-options)   
- [Rendering & Export](https://www.perplexity.ai/search/tell-me-about-editing-with-mov-wr4CClvyRaer2JHWViu2rw#rendering--export)   
- [License](#license)
    

## Overview

**PyClipper** is a command-line tool for quickly editing raw video footage. It lets you remove unwanted segments, add graphics or captions, and control audio (mute, replace, mix, fade, or loop) in just a few steps. PyClipper is optimized for fast turnaround—ideal for YouTube, vlogs, and social media creators.

## Features

- **Remove video segments** interactively or via EDL (Edit Decision List)
    
- **Add graphic overlays** and captions (before or after editing)
    
- **Mute audio segments** (manual or via EDL)
    
- **Flexible audio options:** keep, remove, replace, or mix soundtracks
    
- **Loop, fade, and adjust volume** of added audio
    
- **Hardware-accelerated rendering** (NVIDIA, AMD, Intel)
    
- **Safe, config-driven workflow** with overwrite protection
    
- **Cross-platform:** Windows, Mac, Linux
    

## Requirements

- **Python 3.8+**
- **FFmpeg** (must be installed and in your system PATH)
    
## **Required Python Modules**

- - `MoviePy 2.x+` (which itself depends on `numpy` and `imageio`)
    
- `numpy`
    
- `csv` (standard library)
    
- `json` (standard library)
    
- `os` (standard library)
    
- `pathlib` (standard library)
    
- `subprocess` (standard library)
    
- `tempfile` (standard library)
    

**Standard library modules** (`csv`, `json`, `os`, `pathlib`, `subprocess`, `tempfile`) do not need to be installed separately if you have Python.

**If you use advanced fonts or image features, you may also need:**

- `Pillow` (for image handling, sometimes required by MoviePy)
    
- `imageio[ffmpeg]` (MoviePy may use this internally for some operations)
- (Optional) GPU drivers for hardware acceleration
    

## Installation

1. Clone or download this repository.
    
2. Install dependencies:
    
3. [Install FFmpeg](https://ffmpeg.org/download.html) and ensure it’s in your PATH.
    

## Quick Start

bash

`python PyClipper_Beta.py`

- The script will guide you through video selection, segment removal, overlay/caption options, and audio controls.
    
- All settings are saved in a config file for quick reuse.
    

## Usage

1. **Video Selection:**  
    Enter or confirm the path to your video file.
    
2. **Segment Removal:**
    
    - Remove segments interactively or load an EDL CSV.
        
    - Segments are removed non-destructively; you can preview the result.
        
3. **Graphics & Captions:**
    
    - Add overlays or captions before or after segment removal.
    - For best results with font files keep the font file in the working directory rather than system fonts.
        
4. **Audio Options:**
    
    - Keep original audio, remove all audio, replace, or mix with a new soundtrack.
        
    - Mute specific audio segments (manual or via EDL).
        
    - Loop, fade, and adjust volume of new audio.
        
5. **Rendering:**
    
    - Choose hardware acceleration and quality.
        
    - Output is saved as `yourvideo_EDIT.mp4`.
        

## EDL Format

PyClipper supports modern EDLs (Edit Decision Lists) in CSV format:

|action|record_in|record_out|...other columns...|
|---|---|---|---|
|remove|00:00|00:10||
|mute_audio|00:12|00:14||

- `remove`: Removes video/audio between `record_in` and `record_out`
    
- `mute_audio`: Silences audio between `record_in` and `record_out`
    
- You can mix manual and EDL-driven edits in one workflow.
    

## Audio Options

- **Keep original audio only**
    
- **Remove all audio (silent video)**
    
- **Replace original audio with new soundtrack**
    
- **Mix original audio and new soundtrack**
    
- **Mute specific segments** (via prompt or EDL)
    
- **Loop, fade, and adjust volume** of new audio
    

## Rendering & Export

- **Hardware acceleration**: NVIDIA, AMD, Intel supported
    
- **Quality presets**: H.264, H.265, or lossless
    
- **Multi-threaded transcoding** for fast rendering
    
- **Safe overwrite checks** for output files
