# agent-video-to-ppt-skill
Agent Skill：视频自动转PPT工具

## ✨ 功能介绍
将视频一键转为PPT课件，支持：
- 本地视频文件（mp4/mov）
- MP4直链网络视频URL
- B站、抖音、小红书网页视频链接

核心能力：
1. Whisper语音识别，提取视频字幕文本
2. LLM自动提炼PPT大纲，生成每页标题+要点
3. 根据每页内容自动生成课件配图
4. 输出标准`.pptx`文件，可以继续编辑

> ⚠️ 重要声明：
> 本工具仅供个人学习研究使用。下载平台视频请遵守各平台用户协议，**严禁商用、二次分发，注意版权风险**。
> 部分会员/需要登录观看的视频，需要填入浏览器Cookie才能解析；平台存在反爬机制，链接解析有可能会失效。
> 单视频上限 500MB，下载超时限制5分钟

## 📁 项目目录

## ✨ 使用说明
# video_to_ppt Skill
> 版本：v0.5.0
> 功能：读取视频（本地文件 / B站、抖音、小红书网页链接），自动语音转文字，大模型生成PPT大纲，自动配图，输出`.pptx`文件

## ✅ 前置依赖安装
```bash
pip install whisper python-pptx openai yt-dlp requests
```
> 额外说明：whisper需要ffmpeg环境，如缺少请自行安装ffmpeg。

## 📌 参数说明
| 参数 | 是否必填 | 说明 |
|---|---|---|
| video_path | 二选一 | 本地视频路径，支持mp4/mov；**和video_url不能同时填** |
| video_url | 二选一 | 网络视频链接，支持mp4直链、B站、抖音、小红书；部分视频需要cookie |
| cookie_string | 可选 | 浏览器复制的Cookie文本，用于需要登录才能观看的视频 |
| output_pptx_path | ✅必填 | PPT输出保存路径，例如 `./output/result.pptx` |
| slide_count | 可选 | PPT幻灯片页数，默认8页 |
| llm_api_key | 可选 | 大模型API密钥，用于生成PPT大纲；不填则使用简单文本切割 |
| llm_base_url | 可选 | LLM接口地址，默认OpenAI地址 |
| llm_model | 可选 | 大模型名称，默认`gpt-3.5-turbo` |
| enable_images | 可选 | 是否自动生成配图，默认true |
| image_provider | 可选 | 图片生成服务商，默认openai |
| image_api_key | 可选 | 图片生成密钥，不填自动复用llm_api_key |
| image_base_url | 可选 | 图生接口地址 |
| image_model | 可选 | 配图模型，默认dall-e-3 |

## 🚀 调用示例
### 示例1：本地视频生成PPT
```python
res = handler(
    video_path="./test.mp4",
    output_pptx_path="./output/local_video.pptx",
    slide_count=6,
    llm_api_key="sk-xxx",
)
```

### 示例2：网络链接（B站/抖音/小红书）
```python
res = handler(
    video_url="[https://www.bilibili.com/video/BVxxxxxx](https://www.bilibili.com/video/BVxxxxxx)",
    cookie_string="浏览器复制的cookie内容",
    output_pptx_path="./output/web_video.pptx",
    slide_count=10,
    llm_api_key="sk-xxx",
)
```

## 💡 cookie_string 获取方法（解决视频需要登录才能解析）
1. 浏览器打开目标视频网页，登录账号
2. 打开开发者工具(F12) → Application → Cookies
3. 复制该网站全部cookie文本，填入`cookie_string`参数

## ⚠️ 重要限制 & 注意事项
1. `video_path` 和 `video_url` **二选一，不可同时填写**
2. 视频上限：500MB，超出会直接报错
3. 网络下载受平台限制，部分加密视频无法解析，填入cookie可提升成功率
4. 生成图片依赖对应图片模型API，密钥错误会导致配图失败，但PPT文字部分依然可以输出
5. 返回结果`success=true`代表执行成功；查看`error`字段获取失败原因

