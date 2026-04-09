import argparse
import json
import os
from skills.scraper import get_transcript
from config import get_video_dir

def main():
    parser = argparse.ArgumentParser(description="提取视频字幕并输出为文本信息集")
    parser.add_argument("url", help="视频的 URL (YouTube 或 Bilibili 等)")
    parser.add_argument("--cookies-from", default=None, help="从浏览器如 chrome 中获取 cookie")
    args = parser.parse_args()
    
    result = get_transcript(args.url, args.cookies_from)
    
    if not result:
        print("执行失败，未能获取有效数据。")
        return
        
    video_id = result["video_id"]
    out_dir = get_video_dir(video_id)
    out_file = os.path.join(out_dir, "transcript.json")
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ 成功获取视频信息，Video ID: {video_id}")
    print(f"✅ 字幕数据已保存至: {out_file}")
    print(f"\nAI Agent，你可以阅读上述 JSON 文件并根据 prompts/stitcher_system.md 重新排版生成指南啦。")

if __name__ == "__main__":
    main()
