import subprocess
import sys
import os
import json
from PIL import Image, ImageDraw, ImageFont

def get_video_info(video_path):
    """Get video metadata using ffprobe"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def get_frame_rate(info):
    """Extract frame rate as a float"""
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            fps_str = stream.get("r_frame_rate", "25/1")
            num, den = fps_str.split("/")
            return float(num) / float(den)
    return 25.0

def get_resolution(info):
    """Extract video resolution"""
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream.get("width"), stream.get("height")
    return None, None

def get_duration(info):
    """Extract duration in seconds"""
    return float(info["format"]["duration"])

def seconds_to_timecode(seconds, fps, escape=False):
    """Convert seconds to HH:MM:SS:FF"""
    total_frames = round(seconds * fps)
    ff = total_frames % round(fps)
    total_seconds = total_frames // round(fps)
    ss = total_seconds % 60
    mm = (total_seconds // 60) % 60
    hh = total_seconds // 3600
    if escape:
        return f"{hh:02d}\\:{mm:02d}\\:{ss:02d}\\:{ff:02d}"
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

def seconds_to_hhmmss(seconds):
    """Convert seconds to HH:MM:SS for metadata display"""
    hh = int(seconds // 3600)
    mm = int((seconds % 3600) // 60)
    ss = int(seconds % 60)
    return f"{hh:02d}:{mm:02d}:{ss:02d}"

def extract_frame(video_path, timestamp, output_path, timecode, fps, video_width):
    """Extract a single frame and burn timecode onto it"""
    escaped_timecode = seconds_to_timecode(timestamp, fps, escape=True)
    font_size = max(18, int(video_width * 0.05))
    font_path = "C\\:/Windows/Fonts/arial.ttf"
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(max(0, timestamp - 5)),
        "-i", video_path,
        "-ss", "5",
        "-map", "0:v:0",
        "-vframes", "1",
        "-update", "1",
        "-vf", f"drawtext=fontfile='{font_path}':text='{escaped_timecode}':fontcolor=white:fontsize={font_size}:box=1:boxcolor=black@0.6:boxborderw=5:x=10:y=H-th-10",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"    Return code: {result.returncode}")
    if result.stderr:
        print(f"    STDERR: {result.stderr[-500:]}")
    if not os.path.exists(output_path):
        print(f"    Output file was NOT created")

def make_contact_sheet(video_path, output_folder, cols=4, rows=8):
    """Generate a contact sheet for a single video"""
    print(f"Processing: {os.path.basename(video_path)}")

    info = get_video_info(video_path)
    fps = get_frame_rate(info)
    duration = get_duration(info)
    width, height = get_resolution(info)
    filename = os.path.basename(video_path)
    duration_str = seconds_to_hhmmss(duration)
    resolution_str = f"{width}x{height}"

    print(f"  FPS: {fps:.3f} | Duration: {duration_str} | Resolution: {resolution_str}")

    # Calculate evenly spaced timestamps
    num_thumbs = cols * rows
    interval = duration / (num_thumbs + 1)
    timestamps = [interval * (i + 1) for i in range(num_thumbs)]

    # Extract frames to temp folder
    temp_dir = os.path.join(os.environ.get("TEMP", "."), "contact_sheet_frames")
    os.makedirs(temp_dir, exist_ok=True)

    thumb_paths = []
    for i, ts in enumerate(timestamps):
        timecode = seconds_to_timecode(ts, fps)
        frame_path = os.path.join(temp_dir, f"frame_{i:03d}.png")
        extract_frame(video_path, ts, frame_path, timecode, fps, width)
        thumb_paths.append(frame_path)
        print(f"  Extracted frame {i+1}/{num_thumbs} at {timecode}")

    # Thumbnail dimensions
    thumb_w = 320
    thumb_h = int(thumb_w * height / width)

    # Layout
    padding = 10
    header_h = 80

    sheet_w = cols * thumb_w + (cols + 1) * padding
    sheet_h = header_h + rows * thumb_h + (rows + 1) * padding

    sheet = Image.new("RGB", (sheet_w, sheet_h), color=(30, 30, 30))
    draw = ImageDraw.Draw(sheet)

    try:
        font_large = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 20)
        font_small = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 15)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Header
    draw.text((padding, padding), f"File: {filename}", fill="white", font=font_large)
    draw.text((padding, padding + 28), f"Duration: {duration_str}   Resolution: {resolution_str}   FPS: {fps:.3f}", fill=(180, 180, 180), font=font_small)

    # Place thumbnails
    for i, thumb_path in enumerate(thumb_paths):
        if not os.path.exists(thumb_path):
            continue
        col = i % cols
        row = i // cols
        x = padding + col * (thumb_w + padding)
        y = header_h + padding + row * (thumb_h + padding)
        thumb = Image.open(thumb_path).resize((thumb_w, thumb_h))
        sheet.paste(thumb, (x, y))

    output_name = os.path.splitext(filename)[0] + "_contact_sheet.png"
    output_path = os.path.join(output_folder, output_name)
    sheet.save(output_path)
    print(f"  Saved: {output_path}")

    # Clean up temp frames
    for p in thumb_paths:
        if os.path.exists(p):
            os.remove(p)

def process_folder(input_folder, output_folder=None):
    video_extensions = ('.mp4', '.mov', '.mkv', '.avi', '.wmv', '.flv', '.webm', '.mts', '.m2ts')

    if output_folder is None:
        output_folder = input_folder
    os.makedirs(output_folder, exist_ok=True)

    videos = [f for f in os.listdir(input_folder)
              if f.lower().endswith(video_extensions)
              and not f.startswith("._")
              and not f.startswith(".")]

    if not videos:
        print("No video files found.")
        return

    print(f"Found {len(videos)} video(s) to process.\n")
    for filename in videos:
        video_path = os.path.join(input_folder, filename)
        make_contact_sheet(video_path, output_folder)
        print()

    print("All done!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py contact_sheets.py <input_folder> [output_folder]")
    else:
        input_folder = sys.argv[1]
        output_folder = sys.argv[2] if len(sys.argv) > 2 else None
        process_folder(input_folder, output_folder)