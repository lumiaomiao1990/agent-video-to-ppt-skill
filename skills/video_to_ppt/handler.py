import os
import sys
import tempfile
import shutil
import requests

# 让 skill 能调用 utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    cookie_string: str = ""
):
    try:
        # 二选一校验
        if not video_path and not video_url:
            raise ValueError("必须提供 video_path（本地视频）或者 video_url（网络链接）")
        if video_path and video_url:
            raise ValueError("video_path 和 video_url 不能同时填写，二选一")

        source_type = "local"
        work_video_file = video_path

        # 网络链接模式：支持mp4直链 / B站 / 抖音 / 小红书
        if video_url:
            source_type = "url"
            tmp_dir = tempfile.mkdtemp()
            work_video_file = os.path.join(tmp_dir, "download_video.mp4")
            download_video(video_url, work_video_file, cookie_string)

        # 校验文件大小
        file_size_mb = os.path.getsize(work_video_file) / 1024 / 1024
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            raise ValueError(f"视频过大，上限{MAX_VIDEO_SIZE_MB}MB，当前{file_size_mb:.2f}MB")

        # 语音识别
        model = whisper.load_model("base")
        result = model.transcribe(work_video_file, language="zh")
        raw_text = result["text"].strip()

        # 清理临时文件夹（网络下载模式）
        if source_type == "url":
            shutil.rmtree(os.path.dirname(work_video_file), ignore_errors=True)

        # 生成PPT大纲
        if llm_api_key:
            outline_md = generate_outline_with_llm(raw_text, slide_count, llm_api_key, llm_base_url, llm_model)
        else:
            outline_md = generate_outline_basic(raw_text, slide_count)
        slides_info = parse_outline(outline_md)

        # 生成每页配图
        slide_images = []
        if enable_images:
            img_key = image_api_key or llm_api_key
            for slide in slides_info:
                try:
                    img_path = generate_image_for_slide(
                        title=slide["title"],
                        content=slide["content"],
                        provider=image_provider,
                        api_key=img_key,
                        base_url=image_base_url,
                        model=image_model
                    )
                    slide_images.append(img_path)
                except Exception as e:
                    slide_images.append(None)
                    print(f"【警告】页面「{slide['title']}」图片生成失败: {str(e)}")

        # 生成PPT文件
        ppt_file_path = build_pptx(output_pptx_path, slides_info, slide_images)

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
    except yt_dlp.utils.DownloadError as e:
        return {"success": False, "error": f"yt-dlp解析/下载失败：{str(e)}，部分平台视频需要填入cookie"}
    except FileNotFoundError as e:
        return {"success": False, "error": f"文件不存在：{str(e)}"}
    except ValueError as e:
        return {"success": False, "error": f"参数校验失败：{str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"运行异常：{str(e)}"}


def download_video(url: str, output_file: str, cookie_str: str = ""):
    """
    支持：mp4直链、B站、抖音、小红书链接
    cookie_str：可选，浏览器复制的cookie，用于需要登录才能观看的视频
    """
    ydl_opts = {
        "outtmpl": output_file,
        "format": "bestvideo+bestaudio/best",
        "socket_timeout": DOWNLOAD_TIMEOUT,
        "quiet": True,
        "no_warnings": True,
    }
    # 如果传入cookie，写入临时cookie文件给yt-dlp使用
    if cookie_str and cookie_str.strip():
        cookie_tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        cookie_tmp.write(cookie_str)
        cookie_tmp.close()
        ydl_opts["cookiefile"] = cookie_tmp.name

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    finally:
        # 删除临时cookie文件
        if cookie_str and cookie_str.strip():
            os.unlink(cookie_tmp.name)


def generate_outline_with_llm(raw_text: str, slide_count: int, api_key: str, base_url: str, model: str) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url or "https://api.openai.com/v1")
    prompt = f"""
你是PPT课件大纲专家。根据下面视频文字稿，生成{slide_count}页PPT大纲。
要求：
1. 每页包含标题 + 简短要点（3~6条）
2. 格式严格：## Slide 数字
标题：xxx
正文：
- 要点1
- 要点2

文稿内容（最多截取12000字）：
{raw_text[:12000]}
"""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"LLM生成大纲失败: {str(e)}")


def generate_outline_basic(raw_text: str, slide_count: int) -> str:
    sentences = raw_text.split("。")
    chunk_size = max(1, len(sentences) // slide_count)
    md = ""
    for i in range(slide_count):
        start = i * chunk_size
        end = start + chunk_size
        chunk = "。".join(sentences[start:end])
        md += f"## Slide {i+1}\n标题：第{i+1}页内容\n正文：\n- {chunk}\n\n"
    return md


def parse_outline(md: str):
    blocks = md.split("## Slide ")
    slide_list = []
    for block in blocks[1:]:
        lines = block.strip().splitlines()
        title = ""
        content_lines = []
        for line in lines:
            if line.startswith("标题："):
                title = line.replace("标题：", "").strip()
            elif line.startswith("-"):
                content_lines.append(line.strip())
        slide_list.append({
            "title": title or "幻灯片",
            "content": "\n".join(content_lines)
        })
    return slide_list


def build_pptx(output_path: str, slide_info_list, img_path_list):
    prs = Presentation()
    for idx, slide_data in enumerate(slide_info_list):
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        title = slide.shapes.title
        content = slide.placeholders[1]
        title.text = slide_data["title"]
        content.text = slide_data["content"]

        # 插入图片
        if idx < len(img_path_list):
            img_p = img_path_list[idx]
            if img_p and os.path.exists(img_p):
                left = Inches(5.2)
                top = Inches(1.8)
                height = Inches(3)
                slide.shapes.add_picture(img_p, left, top, height=height)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    prs.save(output_path)
    return output_path
