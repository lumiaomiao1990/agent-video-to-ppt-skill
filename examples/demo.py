from skills.video_to_ppt.handler import handler

if __name__ == "__main__":
    # ========== 模式1：本地视频（取消注释使用） ==========
    # res = handler(
    #     video_path="./demo.mp4",
    #     output_pptx_path="./output/demo_local.pptx",
    #     slide_count=6,
    #     llm_api_key="sk-xxx",
    #     llm_base_url="https://api.openai.com/v1",
    #     llm_model="gpt-3.5-turbo",
    #     enable_images=True,
    #     image_provider="openai",
    #     image_api_key="sk-xxx",
    # )

    # ========== 模式2：网络链接，支持B站/抖音/小红书/mp4直链 ==========
    res = handler(
        video_url="https://www.bilibili.com/video/BVxxxxxx/", #替换成你的视频链接
        cookie_string="", # 可选，需要登录的视频，在这里粘贴浏览器cookie
        output_pptx_path="./output/demo_url.pptx",
        slide_count=6,
        llm_api_key="sk-xxx",
        llm_base_url="https://api.openai.com/v1",
        llm_model="gpt-3.5-turbo",
        enable_images=True,
        image_provider="openai",
        image_api_key="sk-xxx",
    )

    if res.get("success"):
        print("✅ 任务执行成功！")
        print("=== PPT大纲 ===")
        print(res["outline_markdown"])
        print("\n=== 生成图片路径 ===")
        for img in res["slide_images"]:
            print(img)
        print(f"\n视频来源类型：{res['source_type']}")
        print(f"PPT文件输出位置：{res['ppt_file_path']}")
    else:
        print("❌ 任务失败：", res["error"])
