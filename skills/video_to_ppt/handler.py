import os
import sys
import tempfile
import shutil
import requests

# 让 skill 能调用到 utils
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import whisper
from pptx import Presentation
from pptx.util import Inches
from openai import OpenAI
from utils.image_generator import generate_image_for_slide
import yt_dlp

# 全局安全限制
MAX_VIDEO_SIZE_MB = 500  # 最大视频500MB
DOWNLOAD_TIMEOUT = 300   # 下载超时5分钟


def handler(
    video_path: str = "",
    video_url: str = "",
    output_pptx_path: str = "",
    slide_count: int = 8,
    llm_api_key: str = "",
    llm_base_url: str = "https://api.openai.com/v1",
    llm_model: str = "gpt-3.5-turbo",
    enable_images: bool = True,
    image_provider: str = "openai",
    image_api_key: str = "",
    image_base_url: str = "",
    image_model: str = "dall-e-3",
):
    try:
        # 二选一校验
        if not video_path and not video_url:
            raise ValueError("必须提供 video_path（本地）或 video_url（视频链接）其中一项")
        if video_path and video_url:
            raise ValueError("video_path 和 video_url 不能同时填写，请只选择一种视频来源")

        source_type = "local"
        work_video_file = video_path

        # 网络链接模式：下载视频到临时文件
        if video_url:
            source_type = "url"
            tmp_dir = tempfile.mkdtemp()
            work_video_file = os.path.join(tmp_dir, "download_video.mp4")
            download_video(video_url, work_video_file)

        # 校验本地文件大小
        file_size_mb = os.path.getsize(work_video_file) / 1024 / 1024
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            raise ValueError(f"视频过大，限制{MAX_VIDEO_SIZE_MB}MB，当前{file_size_mb:.2f}MB")

        # 校验文件
        if not os.path.exists(work_video_file):
            raise FileNotFoundError(f"视频文件不存在: {work_video_file}")

        # 1. 语音转文字
        model = whisper.load_model("base")
        result = model.transcribe(work_video_file)
        raw_text = result["text"].strip()

        # 清理临时下载文件夹
        if source_type == "url":
            shutil.rmtree(os.path.dirname(work_video_file), ignore_errors=True)

        # 2. LLM 生成每页标题和正文
        if llm_api_key:
            outline_md = generate_outline_with_llm(
                raw_text, slide_count, llm_api_key, llm_base_url, llm_model
            )
        else:
            outline_md = generate_outline_basic(raw_text, slide_count)

        slides = parse_outline(outline_md)

        # 3. 每页生成配图
        slide_images = []
        if enable_images:
            image_key = image_api_key or llm_api_key
            for slide in slides:
                try:
                    image_path = generate_image_for_slide(
                        title=slide["title"],
                        content=slide["body"],
                        provider=image_provider,
                        api_key=image_key,
                        base_url=image_base_url,
                        model=image_model,
                    )
                    slide_images.append(image_path)
                except Exception as e:
                    slide_images.append(None)
                    print(f"【警告】页面「{slide['title']}」图片生成失败: {str(e)}")

        # 4. 生成 PPT，插入配图
        ppt_file_path = build_pptx(output_pptx_path, slides, slide_images)

        return {
            "outline_markdown": outline_md,
            "ppt_file_path": ppt_file_path,
            "raw_transcript": raw_text,
            "slide_images": slide_images,
            "source_type": source_type,
            "success": True
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "下载超时，链接响应太慢，请检查网络或视频链接"}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"链接HTTP错误：{str(e)}"}
    except FileNotFoundError as e:
        return {"success": False, "error": f"文件不存在：{str(e)}"}
    except ValueError as e:
        return {"success": False, "error": f"参数校验失败：{str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"运行异常：{str(e)}"}


def download_video(url: str, output_file: str):
    """下载视频直链，yt-dlp + 超时捕获"""
    try:
        ydl_opts = {
            "outtmpl": output_file,
            "format": "bestvideo+bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": DOWNLOAD_TIMEOUT
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        raise Exception(f"视频下载失败：{str(e)}")
    except Exception as e:
        raise Exception(f"下载过程异常：{str(e)}")


def generate_outline_with_llm(raw_text: str, slide_count: int, api_key: str, base_url: str, model: str) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url)

    prompt = f"""
你是PPT课件大纲专家。请根据下面的视频文字稿，生成 {slide_count} 页PPT大纲。

要求：
1. 每页有一个明确标题。
2. 正文使用3到6个简短要点，适合放进PPT。
3. 结构清晰，有教学感。
4. 不要加入无关总结页或致谢页。

输出格式：
## Slide 1
标题：xxx
正文：
- 要点1
- 要点2
- 要点3

## Slide 2
标题：xxx
正文：
- 要点1
- 要点2

文字稿：
{raw_text[:12000]}
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"LLM生成大纲失败: {str(e)}")


def generate_outline_basic(raw_text: str, slide_count: int) -> str:
    sentences = raw_text.split("。")
    chunk_size = max(1, len(sentences) // slide_count)
    md = ""

    for i in range(slide_count):
        start = i * chunk_size
        end = start + chunk_size
        chunk = "。".join(sentences[start:end]).strip()
        md += f"## Slide {i + 1}\n标题：第{i + 1}页\n正文：\n- {chunk}\n\n"

    return md


def parse_outline(md: str):
    blocks = md.split("## Slide ")
    slides = []

    for block in blocks[1:]:
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        title = ""
        body_lines = []
        capture_body = False

        for line in lines:
            if line.startswith("标题："):
                title = line.replace("标题：", "").strip()
            elif line.startswith("正文："):
                capture_body = True
            elif capture_body:
                body_lines.append(line)

        slides.append({
            "title": title or "未命名页",
            "body": "\n".join(body_lines),
        })

    return slides


def build_pptx(output_pptx_path: str, slides: list, slide_images: list) -> str:
    prs = Presentation()

    for i, slide in enumerate(slides):
        layout = prs.slide_layouts[1]
        slide_obj = prs.slides.add_slide(layout)

        slide_obj.shapes.title.text = slide["title"]
        slide_obj.placeholders[1].text = slide["body"]

        # 如果有配图，放到页面右侧，不遮挡正文
        if slide_images and i < len(slide_images):
            image_path = slide_images[i]
            if image_path and os.path.exists(image_path):
                left = Inches(5.2)
                top = Inches(1.8)
                width = Inches(4.0)
                height = Inches(3.0)
                slide_obj.shapes.add_picture(image_path, left, top, width, height)

    out_dir = os.path.dirname(output_pptx_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    prs.save(output_pptx_path)
    return output_pptx_path
