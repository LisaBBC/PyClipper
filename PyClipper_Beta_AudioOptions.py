#This program uses Moviepy v2.x+ syntax
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip, AudioArrayClip, concatenate_audioclips
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy import concatenate_videoclips
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut, AudioLoop
from moviepy.video.fx import FadeIn, FadeOut
from moviepy import TextClip, vfx
import os
import csv
import numpy as np
import json
from pathlib import Path
import subprocess
import tempfile


# ==============================
# CONFIG FILE HANDLING SECTION
# ==============================
def choose_config_location():
    prompt = "Where should the config file be stored? (home/h or local/l, default: home): "
    while True:
        choice = input(prompt).strip().lower()
        if choice in ("", "home", "h"):  # Default to home if empty or home/h
            return Path.home() / "moviepy_editor_config.json"
        if choice in ("local", "l"):
            return Path("moviepy_editor_config.json")
        print("Please enter 'home', 'h', 'local', or 'l' (or press Enter for home).")

CONFIG_PATH = choose_config_location()

def load_config():
    default_config = {"video": "", "audio": "", "graphic": "", "font": "", "gpu_type": ""}
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
            print("Loaded existing config:")
            print(json.dumps(config, indent=2))
            return config
        else:
            print("Config file does not exist. Using defaults.")
            return default_config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config


def save_config(config, config_path=None):
    if config_path is None:
        config_path = CONFIG_PATH
    try:
        with open(str(config_path), "w") as f:
            json.dump(config, f, indent=2)
        print("Saved updated config:")
        print(json.dumps(config, indent=2))
    except Exception as e:
        print(f"Error saving config: {e}")

def get_input(prompt, config_key, config):
    saved_value = config.get(config_key, "").strip()
    if saved_value:
        reuse = input(f"Use last {config_key} path '{saved_value}'? (y/n): ").lower()
        if reuse == "y":
            print(f"Using saved {config_key}: {saved_value}")
            return saved_value
    new_value = input(prompt).strip('"')
    new_value = new_value.replace("\\", "/")
    config[config_key] = new_value
    save_config(config)
    return new_value

config = load_config()
# --- End Config Handling Section

# =========================
# AUDIO PRE-PROCESSING SECTION
# =========================

def convert_mp3_to_wav(mp3_path):
    """Converts MP3 to WAV using ffmpeg, returns path to temporary WAV file"""
    if not mp3_path.lower().endswith(".mp3"):
        return mp3_path  # Not an MP3, return original path

    wav_path = tempfile.mktemp(suffix=".wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i", mp3_path,
        "-ac", "2",
        "-ar", "44100",
        "-acodec", "pcm_s16le",
        wav_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Converted MP3 to temporary WAV: {wav_path}")
        return wav_path
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg conversion failed: {e.stderr.decode()}")
        return mp3_path  # Fallback to original file
# --- End Audio pre-processing section

# =========================
# AUDIO UTILITY FUNCTIONS SECTION
# =========================
def build_audio_with_fades_and_padding(audio_clip, fades, total_duration):
    """Handles multiple fades with padding"""
    fades = sorted(fades, key=lambda x: x[1])
    segments = []
    fps = audio_clip.fps
    prev_end = 0

    for idx, (fade_type, fade_start, fade_duration) in enumerate(fades):
        fade_end = fade_start + fade_duration
        if fade_start > prev_end:
            silence = AudioArrayClip(np.zeros((int((fade_start - prev_end) * fps), 2)), fps=fps)
            segments.append(silence)
            
        seg = audio_clip.subclipped(fade_start, fade_end)
        if fade_type == "in":
            seg = seg.with_effects([AudioFadeIn(fade_duration)])
        elif fade_type == "out":
            seg = seg.with_effects([AudioFadeOut(fade_duration)])
        segments.append(seg)
        prev_end = fade_end

        # Handle space between fades
        if fade_type == "in" and idx + 1 < len(fades):
            next_fade_type, next_fade_start, _ = fades[idx + 1]
            if next_fade_type == "out" and next_fade_start > prev_end:
                full_vol = audio_clip.subclipped(prev_end, next_fade_start)
                segments.append(full_vol)
                prev_end = next_fade_start

    if prev_end < total_duration:
        remaining = audio_clip.subclipped(prev_end, total_duration)
        segments.append(remaining)

    total_length = sum([s.duration for s in segments])
    if total_length < total_duration:
        silence = AudioArrayClip(np.zeros((int((total_duration - total_length) * fps), 2)), fps=fps)
        segments.append(silence)

    return concatenate_audioclips(segments)

# ============================
# GENERAL FUNCTIONS SECTION
# ============================
def get_valid_input(prompt, invalid_responses=None, default=None):
    if invalid_responses is None:
        invalid_responses = {"y", "n"}
    while True:
        user_input = input(prompt).strip()
        if not user_input and default is not None:
            return default
        if user_input.lower() in invalid_responses:
            print(f"Invalid input: '{user_input}' is not allowed here. Please provide a valid value.")
        else:
            return user_input
        
def check_overwrite(output_path):
    while os.path.exists(output_path):
        overwrite = get_valid_input(
            f"File {output_path} already exists. Overwrite? (y/n/q to enter new name): ",
            invalid_responses=set()
        ).strip().lower()
        if overwrite == "y":
            return output_path
        elif overwrite == "q":
            return None  # User wants to quit
        else:
            # Prompt for new filename
            new_name = input("Enter new filename (or 'q' to quit): ").strip()
            if new_name.lower() == "q":
                return None

            base, ext = os.path.splitext(output_path)
            if not new_name:
                # If user hits Enter without typing a name, append "_NEW" to the base name
                new_name = os.path.basename(base) + "_NEW" + ext
            elif not new_name.endswith(ext):
                new_name += ext

            output_path = os.path.join(os.path.dirname(output_path), new_name)
    return output_path

def get_timestamp(prompt, video_duration, default=0.0):
    user_input = input(prompt).strip().lower()
    if not user_input:
        return default
    if user_input in ("start", "from start"):
        return 0.0
    if user_input in ("end", "until end"):
        return video_duration
    if ':' in user_input:
        parts = user_input.split(':')
        try:
            if len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except Exception:
            print("Invalid timestamp format. Please enter as seconds or MM:SS or HH:MM:SS.")
            return get_timestamp(prompt, video_duration, default)
    try:
        return float(user_input)
    except ValueError:
        print("Invalid timestamp. Please enter as seconds or MM:SS or HH:MM:SS.")
        return get_timestamp(prompt, video_duration, default)

def parse_timestamp_string(s, video_duration):
    """Converts timestamp strings to seconds. Handles:
    - 'start' (0.0)
    - 'end' (video_duration)
    - seconds (float)
    - MM:SS
    - HH:MM:SS
    """
    s = s.strip().lower()
    
    # Handle special keywords
    if s == "start":
        return 0.0
    if s == "end":
        return video_duration
    
    # Handle HH:MM:SS or MM:SS formats
    if ':' in s:
        parts = list(map(float, s.split(':')))
        if len(parts) == 2:  # MM:SS
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:  # HH:MM:SS
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        else:
            raise ValueError(f"Invalid time format: {s}")
    
    # Handle raw seconds
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Could not parse timestamp: {s}")

# def load_edl_csv(file_path, video_duration, strict=False):
#     """
#     Loads an Edit Decision List (EDL) from a CSV file.
#     Supports both header-based ('start', 'stop') and plain two-column formats.
#     Returns a list of (start, end) tuples in seconds.
#     """
#     segments = []
#     
#     with open(file_path, newline='', encoding='utf-8') as csvfile:
#         # Detect header
#         sample = csvfile.read(1024)
#         csvfile.seek(0)
#         has_header = ('start' in sample.lower()) and ('stop' in sample.lower())
#         
#         reader = csv.DictReader(csvfile) if has_header else csv.reader(csvfile)
#         
#         for row_idx, row in enumerate(reader, 1):
#             try:
#                 if has_header:
#                     start_str = str(row['start']).strip()
#                     end_str = str(row['stop']).strip()
#                 else:
#                     if len(row) < 2:
#                         raise ValueError("Row must have at least two columns")
#                     start_str, end_str = str(row[0]).strip(), str(row[1]).strip()
#                 
#                 # Parse timestamps
#                 start = parse_timestamp_string(start_str, video_duration)
#                 end = parse_timestamp_string(end_str, video_duration)
#                 
#                 # Validate segment
#                 if not (0 <= start < end <= video_duration):
#                     raise ValueError(f"Invalid time range: {start:.2f}-{end:.2f}s")
#                 
#                 segments.append((start, end))
#                 
#             except Exception as e:
#                 if strict:
#                     raise ValueError(f"Error in row {row_idx}: {e}") from e
#                 else:
#                     print(f"Skipping invalid row {row_idx}: {e}")
#     
#     return segments
def load_edl_csv(file_path, video_duration, strict=False):
    """
    Loads an EDL CSV with new headers.
    Supports actions: remove, keep, insert.
    Returns a list of edit operation dicts.
    """
    operations = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row_idx, row in enumerate(reader, 1):
            try:
                action = row.get('action', '').strip().lower()
                op = {'action': action}

                # For all actions, parse record_in/out if present
                if 'record_in' in row and row['record_in']:
                    op['record_in'] = parse_timestamp_string(row['record_in'], video_duration)
                if 'record_out' in row and row['record_out']:
                    op['record_out'] = parse_timestamp_string(row['record_out'], video_duration)

                # REMOVE/KEEP: Only need timeline in/out
                if action in {'remove', 'keep'}:
                    if op.get('record_in') is None or op.get('record_out') is None:
                        raise ValueError(f"Missing record_in or record_out for action '{action}'")
                    if not (0 <= op['record_in'] < op['record_out'] <= video_duration):
                        raise ValueError(f"Invalid time range: {op['record_in']:.2f}-{op['record_out']:.2f}s")

                # INSERT: Needs insert_source and source_in/out
                if action == 'insert':
                    op['insert_source'] = row.get('insert_source', '').strip()
                    if not op['insert_source']:
                        raise ValueError("Missing insert_source for insert action")
                    op['source_in'] = parse_timestamp_string(row.get('source_in', '0'), None)
                    op['source_out'] = parse_timestamp_string(row.get('source_out', ''), None)
                    if op['source_out'] is None or op['source_in'] is None:
                        raise ValueError("Missing source_in or source_out for insert action")
                    if op['source_in'] >= op['source_out']:
                        raise ValueError(f"Invalid source range: {op['source_in']:.2f}-{op['source_out']:.2f}s")
                    # Insert must have a record_in (timeline position)
                    if op.get('record_in') is None:
                        raise ValueError("Missing record_in for insert action")

                    # Optional transitions
                    op['transition_in'] = row.get('transition_in', '').strip().lower() or None
                    op['transition_in_duration'] = float(row.get('transition_in_duration', '0') or 0)
                    op['transition_out'] = row.get('transition_out', '').strip().lower() or None
                    op['transition_out_duration'] = float(row.get('transition_out_duration', '0') or 0)

                operations.append(op)

            except Exception as e:
                if strict:
                    raise ValueError(f"Error in row {row_idx}: {e}") from e
                else:
                    print(f"Skipping invalid row {row_idx}: {e}")

    return operations

def parse_percentage_input(user_input: str) -> float:
    user_input = user_input.strip()
    if user_input.endswith('%'):
        user_input = user_input[:-1].strip()
    try:
        value = float(user_input)
    except ValueError:
        raise ValueError(f"Invalid percentage input: {user_input}")
    return value / 100

def parse_position_input(user_input):
    user_input = user_input.strip().lower()
    if user_input in ("left", "center", "right", "top", "bottom"):
        return user_input
    if user_input.endswith('%'):
        try:
            return float(user_input.strip('%')) / 100
        except ValueError:
            pass
    try:
        val = float(user_input)
        if 0 <= val <= 1:
            return val
        elif 1 < val <= 100:
            return val / 100
    except ValueError:
        pass
    print("Invalid position input, defaulting to 'center'")
    return "center"
#

def safe_position(pos, safe_margin_frac=0.10):
    """
    Converts 'left', 'right', 'top', 'bottom' to safe margin positions (10%/90%).
    Passes through floats and 'center' unchanged.
    """
    if pos == "left" or pos == "top":
        return safe_margin_frac
    elif pos == "right" or pos == "bottom":
        return 1.0 - safe_margin_frac
    elif pos == "center":
        return 0.5
    elif isinstance(pos, float):
        return pos
    else:
        return 0.5  # fallback to center


def add_graphic_to_video(video, config):
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy import vfx

    graphics = []
    while True:
        add_graphic = get_valid_input(
            "Add a graphic? (y/n): ", invalid_responses=set()
        ).strip().lower()
        if add_graphic != "y":
            break

        graphic_path = get_input(
            "Enter the path to the graphic image (PNG recommended): ",
            "graphic",
            config
        )

        # Duration and conditional start time
        duration_input = get_valid_input(
            "How many seconds should the graphic stay on screen? Or enter ALL for the total duration: ",
            invalid_responses={"y", "n"}
        ).strip().lower()

        if duration_input == "all":
            graphic_duration = video.duration
            start_time = 0.0
        else:
            graphic_duration = float(duration_input)
            start_time = get_timestamp(
                "At what time should the graphic appear? (seconds, MM:SS, HH:MM:SS, or 'start', default 0): ",
                video.duration
            )

        # Create graphic with start time and duration
        graphic = ImageClip(graphic_path).with_duration(graphic_duration).with_start(start_time)

        # Fade-in and fade-out (using crossfade for best results)
        fadein_input = get_valid_input("Fade-in duration in seconds (default 0): ", invalid_responses={"y", "n"})
        fadeout_input = get_valid_input("Fade-out duration in seconds (default 0): ", invalid_responses={"y", "n"})

        try:
            fadein_duration = float(fadein_input) if fadein_input else 0.0
            fadeout_duration = float(fadeout_input) if fadeout_input else 0.0
        except ValueError:
            print("Invalid fade duration. Using 0.")
            fadein_duration = fadeout_duration = 0.0

        effects = []
        if fadein_duration > 0:
            effects.append(vfx.CrossFadeIn(fadein_duration))
        if fadeout_duration > 0:
            effects.append(vfx.CrossFadeOut(fadeout_duration))
        if effects:
            graphic = graphic.with_effects(effects)

        # Scaling
        scale = get_valid_input("Do you want to scale the graphic? (y/n): ", invalid_responses=set()).strip().lower()
        if scale == 'y':
            scale_mode = get_valid_input(
                "Scale by percent (%) or pixel dimensions (pixels)? (enter % or pixels): ",
                invalid_responses=set()
            ).strip().lower()
            if scale_mode == '%':
                percent_input = get_valid_input("Enter scale percentage (e.g., 25 or 25%): ", invalid_responses={"y", "n"})
                scale_factor = parse_percentage_input(percent_input)
                graphic = graphic.resized(scale_factor)
            elif scale_mode == 'pixels':
                width_or_height = get_valid_input(
                    "Scale by width, height, or both? (width/height/both): ",
                    invalid_responses=set()
                ).strip().lower()
                if width_or_height == 'width':
                    new_width = int(get_valid_input("New width in pixels: ", invalid_responses={"y", "n"}))
                    graphic = graphic.resized(width=new_width)
                elif width_or_height == 'height':
                    new_height = int(get_valid_input("New height in pixels: ", invalid_responses={"y", "n"}))
                    graphic = graphic.resized(height=new_height)
                elif width_or_height == 'both':
                    new_width = int(get_valid_input("New width in pixels: ", invalid_responses={"y", "n"}))
                    new_height = int(get_valid_input("New height in pixels: ", invalid_responses={"y", "n"}))
                    graphic = graphic.resized(width=new_width, height=new_height)

        # Positioning with symmetric margins
        graphic_w, graphic_h = graphic.size
        margin_px = 10

        horizontal_input = get_valid_input(
            "Horizontal position (left/center/right or 0-100%): ",
            invalid_responses={"y", "n"}
        )
        vertical_input = get_valid_input(
            "Vertical position (top/center/bottom or 0-100%): ",
            invalid_responses={"y", "n"}
        )
        horizontal = parse_position_input(horizontal_input)
        vertical = parse_position_input(vertical_input)

        # X position
        if isinstance(horizontal, str):
            if horizontal == "left":
                pos_x = margin_px
            elif horizontal == "center":
                pos_x = (video.w - graphic_w) // 2
            elif horizontal == "right":
                pos_x = video.w - graphic_w - margin_px
            else:
                pos_x = (video.w - graphic_w) // 2
        elif isinstance(horizontal, float):
            pos_x = int(horizontal * (video.w - graphic_w))
        else:
            pos_x = (video.w - graphic_w) // 2

        # Y position
        if isinstance(vertical, str):
            if vertical == "top":
                pos_y = margin_px
            elif vertical == "center":
                pos_y = (video.h - graphic_h) // 2
            elif vertical == "bottom":
                pos_y = video.h - graphic_h - margin_px
            else:
                pos_y = (video.h - graphic_h) // 2
        elif isinstance(vertical, float):
            pos_y = int(vertical * (video.h - graphic_h))
        else:
            pos_y = (video.h - graphic_h) // 2

        # Clamp to video bounds (optional)
        pos_x = max(0, min(video.w - graphic_w, pos_x))
        pos_y = max(0, min(video.h - graphic_h, pos_y))

        graphic = graphic.with_position((pos_x, pos_y))
        graphics.append(graphic)

    if graphics:
        return CompositeVideoClip([video] + graphics)
    else:
        return video

def get_caption_settings(config, mode, video_width):
    # Only update the font in the config file
    font_path = get_input("Font name or path: ", "font", config)
    config['font'] = font_path
    save_config(config)

    # The rest of the settings are session-only, not saved in config
    settings = {}
    settings['font'] = font_path
    settings['fontsize'] = int(input("Font size (e.g. 70): ").strip() or "70")
    settings['color'] = input("Font color\nSee https://imagemagick.org/script/color.php#color_names for list of color names.\n(Default white): ").strip() or "white"
    if mode == "advanced":
        settings['bg_color'] = input("Background color (or leave blank for none): ").strip() or None
        settings['stroke_color'] = input("Stroke (outline) color (or leave blank): ").strip() or None
        settings['stroke_width'] = int(input("Stroke width (e.g. 2): ").strip() or "0")
        settings['interline'] = int(input("Interline spacing (e.g. 4): ").strip() or "4")
        settings['align'] = input("Text alignment (left/center/right): ").strip() or "center"
        settings['transparent'] = input("Transparent background? (y/n): ").strip().lower() == 'y'
        settings['method'] = "caption"
        settings['size'] = (int(video_width * 0.9), None)
    else:
        settings['method'] = "label"
        settings['size'] = (None, None)
    return settings

def add_captions_to_video(video, config):
    from moviepy import TextClip, CompositeVideoClip, vfx
    captions = []
    mode = input("Use simple or advanced caption settings? (simple/advanced): ").strip().lower()
    font_path = get_input("Font name or path: ", "font", config)
    config['font'] = font_path
    save_config(config)
    font_size = int(get_valid_input("Font size (e.g. 70): ", invalid_responses={"y", "n"}, default="70"))
    color = get_valid_input("Font color (default white): ", invalid_responses={"y", "n"}, default="white")
#     font_size = int(get_valid_input("Font size (e.g. 70): ").strip() or "70")
#     color = input("Font color\nSee https://imagemagick.org/script/color.php#color_names for list of color names.\n(Default white): ").strip() or "white"
    margin = (40, 40)  # (horizontal, vertical) in pixels

    if mode == "advanced":
        bg_color = input("Background color (or leave blank for none): ").strip() or None
        stroke_color = input("Stroke (outline) color (or leave blank): ").strip() or None
        stroke_width = int(input("Stroke width (e.g. 2): ").strip() or "0")
        interline = int(input("Interline spacing (e.g. 4): ").strip() or "4")
        align = input("Text alignment (left/center/right): ").strip() or "center"
        transparent = input("Transparent background? (y/n): ").strip().lower() == 'y'
        method = "caption"
        size = (int(video.w * 0.90), int(video.h * 0.50))  # 80% of video width, 25% of height
        vertical_align = "center"
    else:
        bg_color = None
        stroke_color = None
        stroke_width = 0
        interline = 4
        align = "center"
        transparent = True
        method = "label"
        size = (None, None)
        vertical_align = "center"

    while True:
#         add_caption = input("Add a caption? (y/n): ").strip().lower()
        add_caption = get_valid_input("Add a caption? (y/n): ", invalid_responses=set()).strip().lower()
        if add_caption != "y":
            break

        text = input("Enter caption text: ").strip()
        if not text:
            print("Caption text cannot be empty.")
            continue

        start_time = get_timestamp(
            "Start time (seconds, MM:SS, HH:MM:SS, or 'start', default 0): ",
            video.duration,
            default=0.0
        )
#         duration = float(input("Duration in seconds (default 5): ").strip() or "5")
#         fadein = float(input("Fade-in duration (default 0): ").strip() or "0")
#         fadeout = float(input("Fade-out duration (default 0): ").strip() or "0")
# 
#         horizontal_input = input("Horizontal position (left/center/right or %): ").strip() or "center"
#         vertical_input = input("Vertical position (top/center/bottom or %): ").strip() or "bottom"
#         horizontal = parse_position_input(horizontal_input)
#         vertical = parse_position_input(vertical_input)
        duration = float(get_valid_input("Duration in seconds (default 5): ", invalid_responses={"y", "n"}, default="5"))
        fadein = float(get_valid_input("Fade-in duration (default 0): ", invalid_responses={"y", "n"}, default="0"))
        fadeout = float(get_valid_input("Fade-out duration (default 0): ", invalid_responses={"y", "n"}, default="0"))
        horizontal = get_valid_input("Horizontal position (left/center/right or %): ", invalid_responses={"y", "n"}, default="center")
        vertical = get_valid_input("Vertical position (top/center/bottom or %): ", invalid_responses={"y", "n"}, default="bottom")


        # Create the TextClip
        clip = TextClip(
            text=text,
            font=font_path,
            font_size=font_size,
            color=color,
            method=method,
            size=size,
            bg_color=bg_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            interline=interline,
            text_align=align,
            vertical_align=vertical_align,
            transparent=transparent,
            margin=margin
        ).with_duration(duration).with_start(start_time)

        clip_w, clip_h = clip.size
        margin_px = 30  # Extra margin for position

        # Positioning logic
        if isinstance(horizontal, str):
            if horizontal == "left":
                pos_x = margin_px
            elif horizontal == "center":
                pos_x = (video.w - clip_w) // 2
            elif horizontal == "right":
                pos_x = video.w - clip_w - margin_px
            else:
                pos_x = (video.w - clip_w) // 2
        elif isinstance(horizontal, float):
            pos_x = int(horizontal * (video.w - clip_w))
        else:
            pos_x = (video.w - clip_w) // 2

        if isinstance(vertical, str):
            if vertical == "top":
                pos_y = margin_px
            elif vertical == "center":
                pos_y = (video.h - clip_h) // 2
            elif vertical == "bottom":
                pos_y = video.h - clip_h - margin_px
            else:
                pos_y = (video.h - clip_h) // 2
        elif isinstance(vertical, float):
            pos_y = int(vertical * (video.h - clip_h))
        else:
            pos_y = (video.h - clip_h) // 2

        pos_x = max(0, min(video.w - clip_w, pos_x))
        pos_y = max(0, min(video.h - clip_h, pos_y))

        clip = clip.with_position((pos_x, pos_y))

        # --- Use CrossFadeIn/CrossFadeOut for clean fades ---
        effects = []
        if fadein > 0:
            effects.append(vfx.CrossFadeIn(fadein))
        if fadeout > 0:
            effects.append(vfx.CrossFadeOut(fadeout))
        if effects:
            clip = clip.with_effects(effects)

        captions.append(clip)

    if captions:
        return CompositeVideoClip([video] + captions)
    else:
        return video



# --- End General Functions Section

# =========================
# EDITING SECTION
# =========================

# --- Video Path Input Section ---
video_path = get_input("Enter the path to your video file: ", "video", config)
video = VideoFileClip(video_path)
print(f"Loaded video: {video_path}, duration: {video.duration} seconds")

# --- Check if output file already exists ---
base, ext = os.path.splitext(video_path)
output_path = f"{base}_EDIT{ext}"
if os.path.exists(output_path):
    print(f"\nWARNING: Output file {output_path} already exists!")
    overwrite = get_valid_input(
        "Do you want to overwrite it? (y/n/q to enter new name): ",
        invalid_responses=set()
    ).strip().lower()
    if overwrite == "y":
        pass  # Proceed as normal
    elif overwrite == "q":
        print("Export cancelled by user.")
        exit(0)
    else:
        # Prompt for new filename
        new_name = input("Enter new filename (or 'q' to quit): ").strip()
        if new_name.lower() == "q":
            print("Export cancelled by user.")
            exit(0)
        # Ensure the new filename has the right extension
        if not new_name.endswith(ext):
            new_name += ext
        output_path = os.path.join(os.path.dirname(output_path), new_name)
        print(f"Will save to: {output_path}")

# --- Asking if user wants to add a graphic overlay section ---
while True:
    add_graphic = get_valid_input(
        "\nDo you want to add a graphic overlay? (y/n): ",
        invalid_responses=set()
    ).strip().lower()
    if add_graphic in {"y", "n"}:
        break
    print("Please enter 'y' or 'n'.")

graphic_timing = None
if add_graphic == "y":
    while True:
        graphic_timing = get_valid_input(
            "Add graphic before or after segment removal? (enter 'before' or 'after'): ",
            invalid_responses={"y", "n"}
        ).strip().lower()
        if graphic_timing in {"before", "after"}:
            break
        print("Please enter 'before' or 'after'.")

# --- Asking if user wants to add captions section ---
while True:
    add_captions = get_valid_input(
        "Do you want to add captions? (y/n): ",
        invalid_responses=set()
    ).strip().lower()
    if add_captions in {"y", "n"}:
        break
    print("Please enter 'y' or 'n'.")

caption_timing = None
if add_captions == "y":
    while True:
        caption_timing = get_valid_input(
            "Add captions before or after segment removal? (enter 'before' or 'after'): ",
            invalid_responses={"y", "n"}
        ).strip().lower()
        if caption_timing in {"before", "after"}:
            break
        print("Please enter 'before' or 'after'.")

if graphic_timing == "before":
    video = add_graphic_to_video(video, config)

if caption_timing == "before":
    video = add_captions_to_video(video, config)

# --- Destructive Editing aka Remove Segments Section ---
print(f"\n*** WARNING THIS WILL DELETE SOME OR ALL OF YOUR VIDEO, USE WITH CARE. *** \n")

remove_segments = []


# --- Destructive Editing aka Remove Segments Section ---
print(f"\n*** WARNING THIS WILL DELETE SOME OR ALL OF YOUR VIDEO, USE WITH CARE. *** \n")

remove_segments = []
use_edl = input("\nUse an Edit Decision List (EDL) CSV for segment removal? (y/n): ").strip().lower()
if use_edl == 'y':
    # Use config-aware input for EDL path
    edl_path = get_input("Enter the path to the EDL CSV file: ", "edl", config)
    edl_operations = load_edl_csv(edl_path, video.duration, strict=False)
    # Extract only 'remove' actions as (start, end) tuples for legacy code compatibility
    remove_segments = [
        (op['record_in'], op['record_out'])
        for op in edl_operations
        if op['action'] == 'remove'
    ]
    for start, end in remove_segments:
        print(f"Marked for removal from EDL: {start:.2f}s to {end:.2f}s")

# use_edl = input("\nUse an Edit Decision List (EDL) CSV for segment removal? (y/n): ").strip().lower()
# if use_edl == 'y':
#     # Use config-aware input for EDL path
#     edl_path = get_input("Enter the path to the EDL CSV file: ", "edl", config)
#     remove_segments = load_edl_csv(edl_path, video.duration, strict=False)
#     for start, end in remove_segments:
#         print(f"Marked for removal from EDL: {start:.2f}s to {end:.2f}s")
# else:
#     while True:
#         do_remove = input("\nRemove a segment? (y/n): ").strip().lower()
#         if do_remove != 'y':
#             break
#         start = get_timestamp("Segment START time (seconds, MM:SS, or 'start'): ", video.duration)
#         end = get_timestamp("Segment END time (seconds, MM:SS, or 'end'): ", video.duration)
#         if start >= end or start < 0 or end > video.duration:
#             print("Invalid segment. Start must be before end and within video duration.")
#             continue
#         remove_segments.append((start, end))
#         print(f"Marked for removal: {start:.2f}s to {end:.2f}s")

# Sort and merge overlapping/adjacent segments
remove_segments.sort()
merged = []
for seg in remove_segments:
    if not merged or seg[0] > merged[-1][1]:
        merged.append(list(seg))
    else:
        merged[-1][1] = max(merged[-1][1], seg[1])
remove_segments = merged

# Build list of segments to KEEP
keep_segments = []
last_end = 0.0
for start, end in remove_segments:
    if last_end < start:
        keep_segments.append((last_end, start))
    last_end = end
if last_end < video.duration:
    keep_segments.append((last_end, video.duration))

if not keep_segments:
    print("No video left after removals!")
    exit(1)

# Extract and concatenate segments to keep
clips = [video.subclipped(start, end) for start, end in keep_segments if end > start]

# Debugging: print durations
for idx, c in enumerate(clips):
    print(f"Clip {idx}: duration={getattr(c, 'duration', None)}")
print(f"Number of segments removed: {len(remove_segments)}")
print(f"Number of segments kept: {len(clips)}")

if not clips:
    print("No valid segments to keep after removal!")
    exit(1)

video = concatenate_videoclips(clips, method="compose")
video = video.with_duration(sum(c.duration for c in clips))
#print("\nMoving on to titles, graphics and captions...\n")

# --- End Desctructive Video Editing Section ---

# --- Post Edit Captioning and/or Graphics Section
if graphic_timing == "after":
    video = add_graphic_to_video(video, config)

if caption_timing == "after":
    video = add_captions_to_video(video, config)
    
# --- End Edit Captioning and/or Graphics Section


# --- Audio Processing Section ---

# Prompt user for audio handling mode
audio_mode = None
if video.audio is not None:
    print("\nAudio options:")
    print("1. Remove all audio (silent video)")
    print("2. Replace original audio with new soundtrack")
    print("3. Mix original audio and new soundtrack")
    while True:
        audio_mode = input("Choose audio mode (1/2/3): ").strip()
        if audio_mode in {"1", "2", "3"}:
            break
        print("Please enter 1, 2, or 3.")
else:
    print("\nNo original audio detected in the video.")
    print("1. Silent video")
    print("2. Add new soundtrack")
    while True:
        audio_mode = input("Choose audio mode (1/2): ").strip()
        if audio_mode in {"1", "2"}:
            break
        print("Please enter 1 or 2.")

# Prepare variables
video_with_audio = video  # fallback

# --- Handle Silent Video ---
if audio_mode == "1":
    video_with_audio = video.without_audio()
    print("Original audio removed. Video will be silent.")

# --- Handle Replace or Mix ---
elif audio_mode in {"2", "3"}:
    add_audio = input("Do you want to add an additional audio track? (y/n): ").strip().lower()
    if add_audio == 'y':
        # --- Audio Input ---
        audio_path = get_input("Enter the path to your additional audio track: ", "audio", config)
        converted_audio_path = convert_mp3_to_wav(audio_path)
        new_audio = AudioFileClip(converted_audio_path)
        print(f"Loaded audio: {converted_audio_path}, duration: {new_audio.duration} seconds")

        # --- Audio Looping ---
        loop_choice = input("Loop audio? (never/entire/custom): ").strip().lower()
        if loop_choice == "entire":
            new_audio = new_audio.with_effects([AudioLoop(duration=video.duration)])
        elif loop_choice == "custom":
            while True:
                n_loops_str = get_valid_input("How many times should the audio loop? ", invalid_responses={"y", "n"})
                try:
                    n_loops = int(n_loops_str)
                    if n_loops > 0:
                        break
                    else:
                        print("Please enter a positive integer.")
                except ValueError:
                    print("Please enter a valid integer.")
            new_audio = new_audio.with_effects([AudioLoop(n_loops=n_loops)])

        # --- Volume Adjustment Section ---
        volume_percent = float(get_valid_input("Enter volume percentage (0-100): ", invalid_responses={"y", "n"} ))
        new_audio = new_audio.with_volume_scaled(volume_percent / 100)

        # --- PAD AUDIO BEFORE FADE PROMPTS ---
        tolerance = 0.05 # 50 ms
        pad_needed = (video.duration + tolerance) - new_audio.duration
        if pad_needed > 0:
            fps = new_audio.fps
            silence = AudioArrayClip(np.zeros((int(pad_needed * fps), 2)), fps=fps)
            new_audio = concatenate_audioclips([new_audio, silence])
        elif new_audio.duration > video.duration + tolerance:
            new_audio = new_audio.subclipped(0, video.duration + tolerance)

        # --- Fades Section (only if adding audio) ---
        fades = []
        while True:
            add_fade = input("\nAdd a fade? (y/n): ").strip().lower()
            if add_fade != 'y':
                break
            fade_type = input("Fade type (in/out): ").strip().lower()
            while fade_type not in ("in", "out"):
                print("Invalid type. Enter 'in' or 'out'.")
                fade_type = input("Fade type (in/out): ").strip().lower()
            fade_start = get_timestamp("Fade START time (seconds or MM:SS): ", video.duration)
            fade_duration_input = get_valid_input("Fade DURATION (seconds or MM:SS, or 'end' to fade to end): ", invalid_responses={"y", "n"}).strip().lower()
            if fade_duration_input in ("end", "until end"):
                fade_duration = video.duration - fade_start
            else:
                try:
                    fade_duration = parse_timestamp_string(fade_duration_input, video.duration)
                except Exception:
                    print("Invalid fade duration. Please enter as seconds or MM:SS or HH:MM:SS.")
                    continue
            if fade_start < 0 or fade_start >= video.duration:
                print("Error: Fade start must be within video duration.")
                continue
            if fade_duration <= 0 or (fade_start + fade_duration) > video.duration + tolerance:
                print(f"Error: Fade exceeds video duration ({video.duration:.2f}s)")
                continue
            fades.append((fade_type, fade_start, fade_duration))

        # --- Apply Fades ---
        if fades:
            new_audio = build_audio_with_fades_and_padding(new_audio, fades, video.duration)
        else:
            # Final trim/pad to match video duration exactly
            if new_audio.duration < video.duration:
                fps = new_audio.fps
                silence = AudioArrayClip(np.zeros((int((video.duration - new_audio.duration) * fps), 2)), fps=fps)
                new_audio = concatenate_audioclips([new_audio, silence])
            elif new_audio.duration > video.duration:
                new_audio = new_audio.subclipped(0, video.duration)
            new_audio = new_audio.with_duration(video.duration)

        # --- Audio Mix/Replace Logic ---
        if audio_mode == "2":
            # Replace original audio with new soundtrack
            video_with_audio = video.without_audio().with_audio(new_audio)
            print("Original audio replaced with new soundtrack.")
        elif audio_mode == "3":
            # Mix original audio and new soundtrack
            mixed_audio = CompositeAudioClip([video.audio, new_audio])
            mixed_audio = mixed_audio.with_duration(video.duration)
            video_with_audio = video.with_audio(mixed_audio)
            print("Original audio and new soundtrack mixed.")

        # --- Audio Cleanup ---
        new_audio.close()
        if 'mixed_audio' in locals() and hasattr(mixed_audio, "close"):
            mixed_audio.close()
        if converted_audio_path != audio_path:
            try:
                Path(converted_audio_path).unlink(missing_ok=True)
            except Exception as e:
                print(f"Could not delete temp WAV: {e}")

    else:
        # User chose not to add new audio
        if audio_mode == "2":
            video_with_audio = video.without_audio()
            print("Original audio removed (no new audio added).")
        elif audio_mode == "3":
            video_with_audio = video  # Keep original audio only

# --- Handle Silence for No Additional Audio ---
if audio_mode == "1" or (audio_mode in {"2", "3"} and video_with_audio.audio is None):
    duration = video.duration
    fps_audio = 44100
    silence = AudioArrayClip(np.zeros((int(duration * fps_audio), 2)), fps=fps_audio)
    video_with_audio = video.with_audio(silence)

# --- End Audio Processing Section ---

# =========================
# RENDER SECTION
# =========================
# --- Render Quality and Hardware Acceleration Prompt Section ---

# Ask if hardware acceleration is wanted
use_hw = get_valid_input(
    "Use hardware acceleration for rendering? (y/n): ",
    invalid_responses=set()
).strip().lower() == "y"

# Only prompt for GPU type if hardware acceleration is enabled
gpu_type = None
if use_hw:
    # Load or prompt for GPU type
    saved_gpu = config.get("gpu_type", "").strip().lower()
    if saved_gpu:
        reuse = input(f"Use saved GPU type '{saved_gpu}'? (y/n): ").strip().lower()
        if reuse == "y":
            gpu_type = saved_gpu
    if not gpu_type:
        while True:
            gpu_type = get_valid_input(
                "Enter your GPU type (nvidia/amd/intel): ",
                invalid_responses={"y", "n"}
            ).strip().lower()
            if gpu_type in {"nvidia", "amd", "intel"}:
                config["gpu_type"] = gpu_type
                save_config(config)
                break
            print("Invalid input. Please enter 'nvidia', 'amd', or 'intel'.")

# Prompt for render quality
while True:
    quality = get_valid_input(
        "Render quality? Enter 'good' (H.264), 'better' (H.265), or 'ultra' (H.265 lossless): ",
        invalid_responses={"y", "n"}
    ).strip().lower()
    if quality in {"good", "better", "ultra"}:
        break
    print("Please enter 'good', 'better', or 'ultra'.")

# Build codec and ffmpeg_params for intermediate export (CPU-only)
if quality == "ultra":
    codec = "libx265"
    ffmpeg_params = [
        "-x265-params", "lossless=1",
        "-preset", "medium",
        "-pix_fmt", "yuv444p10le"
    ]
    print("Using H.265 (libx265) lossless mode for maximum quality (very large files).")
elif quality == "better":
    codec = "libx265"
    ffmpeg_params = [
        "-crf", "23",
        "-preset", "fast",
        "-pix_fmt", "yuv420p10le"
    ]
    print("Using H.265 (libx265) for better quality and smaller file size.")
else:
    codec = "libx264"
    ffmpeg_params = [
        "-crf", "18",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p"
    ]
    print("Using H.264 (libx264) for good quality and maximum compatibility.")

# Export the edited video to a temporary file
base, ext = os.path.splitext(video_path)
temp_path = f"{base}_EDIT_TEMP.mp4"

if 'video_with_audio' not in locals():
    video_with_audio = video

video_with_audio.write_videofile(
    temp_path,
    codec=codec,
    audio_codec='aac',
    audio_bitrate="192k",
    ffmpeg_params=ffmpeg_params,
    temp_audiofile='temp-audio.m4a',
    remove_temp=True,
    threads=os.cpu_count()
)

print(f"Saved intermediate video to: {temp_path}")

if use_hw and gpu_type:
    # output_path is already set and checked for overwrite
    # Set FFmpeg codec and params based on GPU type
    if gpu_type == "nvidia":
        hw_codec = "hevc_nvenc" if quality in {"better", "ultra"} else "h264_nvenc"
        hw_params = [
            "-preset", "p7",
            "-tune", "hq"
        ]
        if quality == "ultra":
            hw_params.extend(["-profile:v", "main10", "-pix_fmt", "p010le"])
        else:
            hw_params.extend(["-pix_fmt", "yuv420p"])  # Optional: force 8-bit for compatibility
    elif gpu_type == "amd":
        hw_codec = "hevc_amf" if quality in {"better", "ultra"} else "h264_amf"
        hw_params = [
            "-quality", "quality",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-color_range", "tv",
            "-pix_fmt", "yuv420p"  # Required for AMD AMF
        ]
    elif gpu_type == "intel":
        hw_codec = "hevc_qsv" if quality in {"better", "ultra"} else "h264_qsv"
        hw_params = [
            "-preset", "slower",
            "-pix_fmt", "yuv420p"  # Optional: force 8-bit for compatibility
        ]

    # Build FFmpeg command with colorspace filter
    cmd = [
        "ffmpeg",
        "-y",
        "-i", temp_path,
        "-vf", "colorspace=all=bt709:iall=bt709:itrc=bt709:ispace=bt709:range=tv:irange=tv",
        "-c:v", hw_codec,
        *hw_params,
        "-c:a", "copy",
        output_path
    ]

    print(f"Re-encoding with {hw_codec} using hardware acceleration...")
    subprocess.run(cmd, check=True)
    print(f"Saved final video to: {output_path}")

    # Clean up temporary file
    if os.path.exists(temp_path):
        os.unlink(temp_path)
else:
    # If not using hardware acceleration, just rename the temp file
    output_path = f"{base}_EDIT{ext}"
#     output_path = check_overwrite(output_path)  # Use the return value!
    if output_path is None:
        print("Export cancelled by user.")
        exit(0)
    os.replace(temp_path, output_path)
    print(f"Saved final video to: {output_path}")
# ==============================
# DONE!
# ==============================



