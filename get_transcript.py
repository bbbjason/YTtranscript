import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "v" in qs and qs["v"]:
        vid = qs["v"][0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            return vid

    path_parts = [p for p in parsed.path.split("/") if p]
    # youtu.be/{id}
    if parsed.netloc.endswith("youtu.be") and path_parts:
        cand = path_parts[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", cand):
            return cand

    # youtube.com/live/{id} 或 youtube.com/shorts/{id}
    if len(path_parts) >= 2 and path_parts[0] in ("live", "shorts"):
        cand = path_parts[1]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", cand):
            return cand

    # 最後用 regex 搜尋
    m = re.search(
        r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|live/|shorts/))([A-Za-z0-9_-]{11})",
        url
    )
    if m:
        return m.group(1)

    raise ValueError("無法從提供的連結中抓取到有效的 video_id，請確認 URL 格式。")


def get_transcript_text(video_id: str, languages=("zh-Hant","zh-Hans","en")) -> str:
    api = YouTubeTranscriptApi()
    
    # 先嘗試指定語言的字幕
    for lang in languages:
        try:
            transcripts = api.list(video_id)
            transcript = transcripts.find_transcript([lang])
            caption_data = transcript.fetch()
            return "\n".join(item["text"] for item in caption_data)
        except Exception:
            pass

    # 嘗試獲取任何可用的字幕
    try:
        transcripts = api.list(video_id)
        # 嘗試自動翻譯成繁體中文
        transcript = transcripts.find_transcript(languages)
        caption_data = transcript.translate("zh-Hant").fetch()
        return "\n".join(item["text"] for item in caption_data)
    except Exception:
        pass

    # 如果都失敗
    raise Exception("找不到符合需求的字幕，或該影片沒有公開/可取得的字幕。")


def main():
    YOUTUBE_URL = "https://youtu.be/Tld91M_bcEI?si=vJ5M5t7AbJon_uqK"
    OUTPUT_FILE = "captions.txt"

    try:
        video_id = extract_video_id(YOUTUBE_URL)
    except Exception as e:
        print(f"URL 錯誤：{e}")
        return

    print(f"解析到 video_id：{video_id}")
    print("正在擷取字幕...")

    try:
        txt = get_transcript_text(video_id)
    except TranscriptsDisabled:
        print("此影片禁用字幕（TranscriptsDisabled）。")
        return
    except NoTranscriptFound:
        print("沒有可用字幕（NoTranscriptFound）。可能是直播尚未產生字幕或未公開。")
        return
    except VideoUnavailable:
        print("影片無法使用（VideoUnavailable）。")
        return
    except Exception as e:
        print(f"擷取字幕時發生錯誤：{e}")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"字幕擷取完成：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
