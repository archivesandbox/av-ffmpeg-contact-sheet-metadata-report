import subprocess
import sys
import os
import json
import csv
import hashlib
from PIL import Image, ImageDraw, ImageFont

def get_video_info(video_path):
    """Get video metadata using ffprobe"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def get_md5(file_path):
    """Calculate MD5 checksum of file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

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

def extract_preservation_metadata(video_path, info):
    """Extract preservation-focused metadata from ffprobe output"""
    fmt = info.get("format", {})
    fmt_tags = fmt.get("tags", {})

    # Find video and audio streams
    video_stream = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    audio_stream = next((s for s in info["streams"] if s["codec_type"] == "audio"), {})

    video_tags = video_stream.get("tags", {})
    audio_tags = audio_stream.get("tags", {})

    # Frame rate
    fps_str = video_stream.get("r_frame_rate", "0/1")
    num, den = fps_str.split("/")
    fps = round(float(num) / float(den), 3) if float(den) else 0

    # Duration
    duration_secs = float(fmt.get("duration", 0))
    duration_str = seconds_to_hhmmss(duration_secs)

    # File size in MB
    file_size_bytes = os.path.getsize(video_path)
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    # Bit depth
    bits_per_sample = video_stream.get("bits_per_raw_sample", "")

    # Field order
    field_order = video_stream.get("field_order", "progressive")

    # MD5
    print(f"  Calculating MD5 checksum...")
    md5 = get_md5(video_path)

    return {
        # File info
        "filename": os.path.basename(video_path),
        "file_path": video_path,
        "file_size_mb": file_size_mb,
        "md5_checksum": md5,

        # Container
        "container_format": fmt.get("format_long_name", ""),
        "overall_bitrate_kbps": round(float(fmt.get("bit_rate", 0)) / 1000, 2),
        "duration": duration_str,
        "duration_seconds": round(duration_secs, 3),
        "creation_date": fmt_tags.get("creation_time", video_tags.get("creation_time", "")),

        # Video stream
        "video_codec": video_stream.get("codec_long_name", ""),
        "video_codec_tag": video_stream.get("codec_tag_string", ""),
        "width": video_stream.get("width", ""),
        "height": video_stream.get("height", ""),
        "pixel_format": video_stream.get("pix_fmt", ""),
        "bit_depth": bits_per_sample,
        "frame_rate": fps,
        "color_space": video_stream.get("color_space", ""),
        "color_primaries": video_stream.get("color_primaries", ""),
        "color_transfer": video_stream.get("color_transfer", ""),
        "field_order": field_order,
        "video_bitrate_kbps": round(float(video_stream.get("bit_rate", 0)) / 1000, 2) if video_stream.get("bit_rate") else "",

        # Embedded timecode
        "embedded_timecode": video_tags.get("timecode", fmt_tags.get("timecode", "")),

        # Camera metadata
        "camera_make": fmt_tags.get("com.apple.quicktime.make", fmt_tags.get("make", "")),
        "camera_model": fmt_tags.get("com.apple.quicktime.model", fmt_tags.get("model", "")),

        # Audio stream
        "audio_codec": audio_stream.get("codec_long_name", ""),
        "audio_sample_rate_hz": audio_stream.get("sample_rate", ""),
        "audio_channels": audio_stream.get("channels", ""),
        "audio_bit_depth": audio_stream.get("bits_per_raw_sample", audio_stream.get("bits_per_sample", "")),
        "audio_bitrate_kbps": round(float(audio_stream.get("bit_rate", 0)) / 1000, 2) if audio_stream.get("bit_rate") else "",
    }

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

    # Extract preservation metadata
    metadata = extract_preservation_metadata(video_path, info)

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
    header_h = 120

    sheet_w = cols * thumb_w + (cols + 1) * padding
    sheet_h = header_h + rows * thumb_h + (rows + 1) * padding

    sheet = Image.new("RGB", (sheet_w, sheet_h), color=(30, 30, 30))
    draw = ImageDraw.Draw(sheet)

    try:
        font_large = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 20)
        font_small = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Header metadata
    draw.text((padding, padding),       f"File: {filename}", fill="white", font=font_large)
    draw.text((padding, padding + 28),  f"Duration: {duration_str}   Resolution: {resolution_str}   FPS: {fps:.3f}", fill=(180, 180, 180), font=font_small)
    draw.text((padding, padding + 48),  f"Codec: {metadata['video_codec_tag']}   Container: {metadata['container_format']}", fill=(180, 180, 180), font=font_small)
    draw.text((padding, padding + 68),  f"Color: {metadata['color_primaries']}   Transfer: {metadata['color_transfer']}   Pixel fmt: {metadata['pixel_format']}", fill=(180, 180, 180), font=font_small)
    draw.text((padding, padding + 88),  f"MD5: {metadata['md5_checksum']}", fill=(150, 150, 150), font=font_small)

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
    print(f"  Saved contact sheet: {output_path}")

    # Clean up temp frames
    for p in thumb_paths:
        if os.path.exists(p):
            os.remove(p)

    return metadata

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

    all_metadata = []
    for filename in videos:
        video_path = os.path.join(input_folder, filename)
        metadata = make_contact_sheet(video_path, output_folder)
        all_metadata.append(metadata)
        print()

    # Write CSV
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(output_folder, f"preservation_metadata_{timestamp}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=all_metadata[0].keys())
        writer.writeheader()
        writer.writerows(all_metadata)

    print(f"Metadata CSV saved: {csv_path}")
    print("All done!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py contact_sheets.py <input_folder> [output_folder]")
    else:
        input_folder = sys.argv[1]
        output_folder = sys.argv[2] if len(sys.argv) > 2 else None
        process_folder(input_folder, output_folder)