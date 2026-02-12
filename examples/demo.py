"""
Seedance 2.0 API Python 调用示例

使用方法:
  1. 安装依赖: pip install requests
  2. 运行示例: python demo.py --api-key sk-your-api-key
  3. 或设置环境变量: export SUTUI_API_KEY=sk-your-api-key && python demo.py

获取 API Key: https://www.xskill.ai/#/v2/api-keys
模型文档:   https://www.xskill.ai/#/v2/models?model=st-ai%2Fsuper-seed2
"""

import argparse
import json
import os
import sys
import time

import requests

# ============================================================
# 配置
# ============================================================
BASE_URL = "https://api.xskill.ai"
CREATE_URL = f"{BASE_URL}/api/v3/tasks/create"
QUERY_URL = f"{BASE_URL}/api/v3/tasks/query"
MODEL_ID = "st-ai/super-seed2"

POLL_INTERVAL = 5        # 轮询间隔（秒）
MAX_POLL_TIME = 600      # 最大等待时间（秒）


# ============================================================
# 核心方法
# ============================================================
def get_headers(api_key: str) -> dict:
    """构建请求头"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def create_task(api_key: str, prompt: str, media_files: list,
                aspect_ratio: str = "16:9", duration: str = "5",
                mode: str = "seedance_2.0_fast") -> dict:
    """
    创建视频生成任务

    Args:
        api_key:      API 密钥
        prompt:       提示词，支持 @图片1、@视频1 等引用语法
        media_files:  媒体文件 URL 列表（图片/视频/音频）
        aspect_ratio: 画面比例，如 16:9、9:16、1:1
        duration:     视频时长（秒），范围 4-15
        mode:         速度模式：seedance_2.0_fast（快速，默认）/ seedance_2.0（标准）

    Returns:
        API 响应 JSON
    """
    payload = {
        "model": MODEL_ID,
        "params": {
            "prompt": prompt,
            "media_files": media_files,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "model": mode,
        },
        "channel": None,
    }

    print(f"[创建任务] 提示词: {prompt}")
    print(f"[创建任务] 媒体文件: {media_files}")

    resp = requests.post(CREATE_URL, json=payload, headers=get_headers(api_key), timeout=30)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    result = resp.json()

    if result.get("code") != 200:
        raise Exception(f"创建任务失败: {json.dumps(result, ensure_ascii=False)}")

    task_id = result["data"]["task_id"]
    price = result["data"].get("price", "未知")
    print(f"[创建任务] 成功! task_id={task_id}, 消耗积分={price}")
    return result


def query_task(api_key: str, task_id: str) -> dict:
    """
    查询任务状态

    Args:
        api_key: API 密钥
        task_id: 任务 ID

    Returns:
        API 响应 JSON
    """
    payload = {"task_id": task_id}
    resp = requests.post(QUERY_URL, json=payload, headers=get_headers(api_key), timeout=30)
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def wait_for_result(api_key: str, task_id: str) -> dict:
    """
    轮询等待任务完成

    Args:
        api_key: API 密钥
        task_id: 任务 ID

    Returns:
        最终查询结果 JSON

    Raises:
        TimeoutError: 超过最大等待时间
        Exception:    任务失败
    """
    print(f"\n[轮询] 开始等待任务完成 (最大 {MAX_POLL_TIME}s, 每 {POLL_INTERVAL}s 查询一次)...")
    elapsed = 0

    while elapsed < MAX_POLL_TIME:
        result = query_task(api_key, task_id)
        status = result["data"]["status"]
        print(f"[轮询] {elapsed}s - 状态: {status}")

        if status == "completed":
            output = result["data"]["output"]
            video_url = output.get("video_url", "")
            print(f"\n[完成] 视频生成成功!")
            print(f"[完成] 视频地址: {video_url}")
            return result

        if status == "failed":
            error_msg = result["data"].get("output", {}).get("error", "未知错误")
            raise Exception(f"任务失败: {error_msg}")

        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    raise TimeoutError(f"任务超时: 等待 {MAX_POLL_TIME}s 后仍未完成")


# ============================================================
# 使用示例
# ============================================================
def example_single_image(api_key: str):
    """示例 1: 单图生成视频"""
    print("\n" + "=" * 60)
    print("示例 1: 单图生成视频")
    print("=" * 60)

    result = create_task(
        api_key=api_key,
        prompt="@图片1 角色在森林中缓步行走，阳光透过树叶洒下斑驳光影，微风吹动发丝",
        media_files=[
            "https://your-character-image.png",
        ],
        aspect_ratio="9:16",
        duration="8",
    )
    task_id = result["data"]["task_id"]
    wait_for_result(api_key, task_id)


def example_image_and_video(api_key: str):
    """示例 2: 角色动作迁移（图片 + 视频）"""
    print("\n" + "=" * 60)
    print("示例 2: 角色动作迁移（图片 + 视频）")
    print("=" * 60)

    result = create_task(
        api_key=api_key,
        prompt="@图片1 让角色参考 @视频1 的动作和运镜风格进行表演，电影级光影",
        media_files=[
            "https://your-character-image.png",
            "https://your-reference-video.mp4",
        ],
        aspect_ratio="16:9",
        duration="5",
    )
    task_id = result["data"]["task_id"]
    wait_for_result(api_key, task_id)


def example_audio_lipsync(api_key: str):
    """示例 3: 音频驱动口型（图片 + 音频）"""
    print("\n" + "=" * 60)
    print("示例 3: 音频驱动口型（图片 + 音频）")
    print("=" * 60)

    result = create_task(
        api_key=api_key,
        prompt="@图片1 角色说话，配合 @音频1 的内容，表情自然生动",
        media_files=[
            "https://your-character-image.png",
            "https://your-audio-file.mp3",
        ],
        aspect_ratio="16:9",
        duration="5",
    )
    task_id = result["data"]["task_id"]
    wait_for_result(api_key, task_id)


# ============================================================
# 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Seedance 2.0 API Python Demo")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("SUTUI_API_KEY", ""),
        help="API Key (也可通过环境变量 SUTUI_API_KEY 设置)",
    )
    parser.add_argument(
        "--example",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="运行示例编号: 1=单图生成视频, 2=角色动作迁移, 3=音频驱动口型",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("错误: 请提供 API Key")
        print("  方式1: python demo.py --api-key sk-your-api-key")
        print("  方式2: export SUTUI_API_KEY=sk-your-api-key && python demo.py")
        print("\n获取 API Key: https://www.xskill.ai/#/v2/api-keys")
        sys.exit(1)

    examples = {
        1: example_single_image,
        2: example_image_and_video,
        3: example_audio_lipsync,
    }

    try:
        examples[args.example](args.api_key)
    except TimeoutError as e:
        print(f"\n[超时] {e}")
    except Exception as e:
        print(f"\n[错误] {e}")


if __name__ == "__main__":
    main()
