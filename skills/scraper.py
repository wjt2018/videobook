import json
import os
import subprocess
import sys
import urllib.parse as urlparse
import glob
from typing import Dict, Any, List
import webvtt
import shutil

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

def extract_youtube_id(url: str) -> str:
    """从 YouTube URL 中提取 Video ID"""
    parsed = urlparse.urlparse(url)
    if "youtube.com" in parsed.netloc:
        qs = urlparse.parse_qs(parsed.query)
        return qs.get("v", [None])[0]
    elif "youtu.be" in parsed.netloc:
        return parsed.path[1:]
    return None

def fetch_via_transcript_api(video_id: str) -> List[Dict[str, Any]]:
    """使用 youtube-transcript-api 获取字幕（兼容新版实例化 API）"""
    if not YouTubeTranscriptApi:
        raise ImportError("youtube-transcript-api is not installed")
    
    # 新版 API（v1.0+）需要先实例化再调用 .fetch()
    ytt_api = YouTubeTranscriptApi()
    
    # 按优先级尝试中英文字幕
    try:
        transcript = ytt_api.fetch(video_id, languages=['zh-CN', 'zh', 'zh-Hans', 'zh-Hant', 'en', 'en-US'])
        return transcript.to_raw_data()
    except Exception:
        pass

    # 不指定语言，让它自动选择默认字幕
    try:
        transcript = ytt_api.fetch(video_id)
        return transcript.to_raw_data()
    except Exception as e:
        raise ValueError(f"无法获取任何可用字幕，详情: {e}")

def convert_vtt_to_json(vtt_file: str) -> List[Dict[str, Any]]:
    """解析 VTT 内容到统一 JSON 格式"""
    results = []
    for caption in webvtt.read(vtt_file):
        start_str = caption.start
        end_str = caption.end
        text = caption.text.strip().replace('\n', ' ')
        
        if not text:
            continue
            
        results.append({
            "start": start_str,
            "end": end_str,
            "text": text
        })
    return results

def fetch_via_ytdlp(video_url: str, cookies_from: str = None) -> List[Dict[str, Any]]:
    """使用 yt-dlp 作为兜底方案获取字幕（支持 B 站等）"""
    tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tmp_subs")
    os.makedirs(tmp_dir, exist_ok=True)
    
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "en.*,zh.*",
        "--skip-download",
        "--sub-format", "vtt/best",
        "--no-check-certificates",
        "--ignore-errors",
        "-o", os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        video_url
    ]
    
    if cookies_from:
        cmd.extend(["--cookies-from-browser", cookies_from])
        
    print(f">> 正在使用 yt-dlp 获取字幕...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    # 即使 returncode != 0，也检查是否已经有部分 vtt 下载成功
    vtt_files = glob.glob(os.path.join(tmp_dir, "*.vtt"))
    
    if not vtt_files:
        stderr_msg = proc.stderr.strip() if proc.stderr else "未知错误"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        raise ValueError(f"yt-dlp 未能获取到任何字幕文件: {stderr_msg}")
        
    # 如果有多个，优先选择中文或英文
    target_vtt = vtt_files[0]
    for vtt in vtt_files:
        if ".zh" in vtt or ".en" in vtt:
            target_vtt = vtt
            break
    
    print(f">> 找到字幕文件: {os.path.basename(target_vtt)}")
            
    try:
        segments = convert_vtt_to_json(target_vtt)
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
            
    return segments

def format_timestamp(seconds_float):
    """把秒数格式化成 HH:MM:SS 字符串，便于展示"""
    try:
        seconds_float = float(seconds_float)
    except ValueError:
        return seconds_float # 如果已经是字符串，比如来自 VTT

    m, s = divmod(int(seconds_float), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"00:{m:02d}:{s:02d}"

def get_transcript(video_url: str, cookies_from: str = None) -> Dict[str, Any]:
    """主入口：获取视频字幕并统一输出格式"""
    yt_id = extract_youtube_id(video_url)
    segments = None
    
    # 获取视频基础信息 (用 yt-dlp)
    cmd_info = [sys.executable, "-m", "yt_dlp", "-j", video_url]
    if cookies_from:
        cmd_info.extend(["--cookies-from-browser", cookies_from])
        
    print(f">> 正在拉取视频元数据...")
    info_proc = subprocess.run(cmd_info, capture_output=True, text=True)
    video_info = {}
    if info_proc.returncode == 0:
        try:
            video_info = json.loads(info_proc.stdout.splitlines()[0])
        except Exception:
            pass

    # 策略 1: YouTube 专用 API (最快)
    if yt_id:
        try:
            print(f">> 尝试使用 youtube-transcript-api 抓取...")
            raw_segments = fetch_via_transcript_api(yt_id)
            segments = []
            for seg in raw_segments:
                start_fmt = format_timestamp(seg['start'])
                end_fmt = format_timestamp(seg['start'] + seg['duration'])
                segments.append({
                    "start": start_fmt,
                    "end": end_fmt,
                    "text": seg['text'].replace('\n', ' ')
                })
        except Exception as e:
            print(f">> youtube-transcript-api 失败: {e}")
            segments = None

    # 策略 2: yt-dlp (B站和 YT 兜底)
    if not segments:
        try:
            segments = fetch_via_ytdlp(video_url, cookies_from)
        except Exception as e:
            print(f"❌ 抓取失败: 该视频可能未提供字幕 ({e})")
            return None
            
    result = {
        "video_url": video_url,
        "title": video_info.get("title", "Unknown Title"),
        "video_id": video_info.get("id", "Unknown_ID"),
        "segments": segments
    }
    
    return result
