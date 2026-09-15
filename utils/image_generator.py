import os
import requests
from PIL import Image
from io import BytesIO


def generate_image_for_slide(title: str, content: str, provider: str = "openai", **kwargs) -> str:
    """
    根据单页PPT标题和内容生成配图，返回保存后的图片本地路径。
    provider: openai / siliconflow / custom
    """

    prompt = build_image_prompt(title, content)

    if provider == "openai":
        image_url = generate_image_openai(prompt, **kwargs)
    elif provider == "siliconflow":
        image_url = generate_image_siliconflow(prompt, **kwargs)
    else:
        image_url = generate_image_custom(prompt, **kwargs)

    return download_image(image_url, title)


def build_image_prompt(title: str, content: str) -> str:
    return (
        f"生成一张适合教学演示页的配图。"
        f"页面主题：{title}。"
        f"页面内容：{content}。"
        f"风格：干净、专业、扁平插画与信息图结合，浅色背景，结构清晰，"
        f"适合课件PPT，避免大段文字，避免复杂背景。"
    )


def generate_image_openai(prompt: str, api_key: str = "", base_url: str = "", model: str = "dall-e-3") -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=base_url or "https://api.openai.com/v1",
    )

    response = client.images.generate(
        model=model,
        prompt=prompt,
        size="1024x1024",
        n=1,
    )

    return response.data[0].url


def generate_image_siliconflow(prompt: str, api_key: str = "", model: str = "black-forest-labs/FLUX.1-dev") -> str:
    url = "https://api.siliconflow.cn/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["data"][0]["url"]


def generate_image_custom(prompt: str, api_key: str = "", base_url: str = "", model: str = "") -> str:
    url = f"{base_url}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["data"][0]["url"]


def download_image(url: str, title: str, output_dir: str = "./output/images") -> str:
    os.makedirs(output_dir, exist_ok=True)

    safe_name = "".join(c if c.isalnum() else "_" for c in title[:30]) or "slide"
    filename = f"{safe_name}_{abs(hash(url)) % 10000}.png"
    filepath = os.path.join(output_dir, filename)

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    image = Image.open(BytesIO(resp.content))
    image.save(filepath)

    return filepath
