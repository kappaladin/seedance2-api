"""
Seedance 2.0 API Python 调用示例

使用方法:
  1. 安装依赖: pip install requests
  2. 运行示例: python demo.py --api-key sk-your-api-key
  3. 或设置环境变量: export XSKILL_API_KEY=sk-your-api-key && python demo.py

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


def create_task(api_key: str, prompt: str,
                image_files: list = None,
                video_files: list = None,
                audio_files: list = None,
                file_paths: list = None,
                function_mode: str = "omni_reference",
                ratio: str = "16:9",
                duration: int = 5,
                mode: str = "seedance_2.0_fast") -> dict:
    """
    创建视频生成任务

    Args:
        api_key:        API 密钥
        prompt:         提示词，支持 @image_file_1/@video_file_1/@audio_file_1 引用语法
                        （也兼容旧版 @图片1/@视频1/@音频1）
        image_files:    参考图片 URL 列表（omni_reference 模式，最多 9 张）
        video_files:    参考视频 URL 列表（omni_reference 模式，最多 3 个，总时长 ≤ 15s）
        audio_files:    参考音频 URL 列表（omni_reference 模式，最多 3 个）
        file_paths:     图片 URL 列表（first_last_frames 模式：0张=文生视频，1张=首帧，2张=首尾帧）
        function_mode:  功能模式：omni_reference（全能模式，默认）/ first_last_frames（首尾帧模式）
        ratio:          画面比例：21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16
        duration:       视频时长（秒），范围 4-15 整数
        mode:           速度模式：seedance_2.0_fast（快速，默认）/ seedance_2.0（标准）

    Returns:
        API 响应 JSON
    """
    params = {
        "prompt": prompt,
        "functionMode": function_mode,
        "ratio": ratio,
        "duration": duration,
        "model": mode,
    }

    # 根据功能模式设置素材参数
    if function_mode == "omni_reference":
        if image_files:
            params["image_files"] = image_files
        if video_files:
            params["video_files"] = video_files
        if audio_files:
            params["audio_files"] = audio_files
    elif function_mode == "first_last_frames":
        if file_paths:
            params["filePaths"] = file_paths

    payload = {
        "model": MODEL_ID,
        "params": params,
    }

    print(f"[创建任务] 功能模式: {function_mode}")
    print(f"[创建任务] 提示词: {prompt}")
    if image_files:
        print(f"[创建任务] 参考图片: {image_files}")
    if video_files:
        print(f"[创建任务] 参考视频: {video_files}")
    if audio_files:
        print(f"[创建任务] 参考音频: {audio_files}")
    if file_paths:
        print(f"[创建任务] 首尾帧图片: {file_paths}")

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
            output = result["data"].get("result", {}).get("output", {})
            video_url = output.get("images", [""])[0] if output.get("images") else ""
            print(f"\n[完成] 视频生成成功!")
            print(f"[完成] 视频地址: {video_url}")
            return result

        if status == "failed":
            error_msg = result["data"].get("error", "未知错误")
            raise Exception(f"任务失败: {error_msg}")

        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    raise TimeoutError(f"任务超时: 等待 {MAX_POLL_TIME}s 后仍未完成")


# ============================================================
# 使用示例
# ============================================================
def example_single_image(api_key: str):
    """示例 1: 单图生成视频（全能模式）"""
    print("\n" + "=" * 60)
    print("示例 1: 单图生成视频（全能模式）")
    print("=" * 60)

    result = create_task(
        api_key=api_key,
        prompt="@image_file_1 角色在森林中缓步行走，阳光透过树叶洒下斑驳光影，微风吹动发丝",
        image_files=[
            "https://your-character-image.png",
        ],
        ratio="9:16",
        duration=8,
    )
    task_id = result["data"]["task_id"]
    wait_for_result(api_key, task_id)


def example_image_and_video(api_key: str):
    """示例 2: 角色动作迁移（图片 + 视频，全能模式）"""
    print("\n" + "=" * 60)
    print("示例 2: 角色动作迁移（图片 + 视频）")
    print("=" * 60)

    result = create_task(
        api_key=api_key,
        prompt="@image_file_1 中的人物按照 @video_file_1 的动作和运镜风格进行表演，电影级光影",
        image_files=[
            "https://your-character-image.png",
        ],
        video_files=[
            "https://your-reference-video.mp4",
        ],
        ratio="16:9",
        duration=5,
    )
    task_id = result["data"]["task_id"]
    wait_for_result(api_key, task_id)


def example_audio_lipsync(api_key: str):
    """示例 3: 音频驱动口型（图片 + 音频，全能模式）"""
    print("\n" + "=" * 60)
    print("示例 3: 音频驱动口型（图片 + 音频）")
    print("=" * 60)

    result = create_task(
        api_key=api_key,
        prompt="@image_file_1 角色说话，配合 @audio_file_1 的内容，表情自然生动",
        image_files=[
            "https://your-character-image.png",
        ],
        audio_files=[
            "https://your-audio-file.mp3",
        ],
        ratio="16:9",
        duration=5,
    )
    task_id = result["data"]["task_id"]
    wait_for_result(api_key, task_id)


def example_first_last_frames(api_key: str):
    """示例 4: 首尾帧视频生成（first_last_frames 模式）"""
    print("\n" + "=" * 60)
    print("示例 4: 首尾帧视频生成")
    print("=" * 60)

    result = create_task(
        api_key=api_key,
        prompt="镜头从首帧缓缓过渡到尾帧，画面流畅自然，电影级光影效果",
        file_paths=[
            "https://your-first-frame.png",
            "https://your-last-frame.png",
        ],
        function_mode="first_last_frames",
        ratio="16:9",
        duration=5,
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
        default=os.environ.get("XSKILL_API_KEY", ""),
        help="API Key (也可通过环境变量 XSKILL_API_KEY 设置)",
    )
    parser.add_argument(
        "--example",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help="运行示例编号: 1=单图生成视频, 2=角色动作迁移, 3=音频驱动口型, 4=首尾帧视频",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("错误: 请提供 API Key")
        print("  方式1: python demo.py --api-key sk-your-api-key")
        print("  方式2: export XSKILL_API_KEY=sk-your-api-key && python demo.py")
        print("\n获取 API Key: https://www.xskill.ai/#/v2/api-keys")
        sys.exit(1)

    examples = {
        1: example_single_image,
        2: example_image_and_video,
        3: example_audio_lipsync,
        4: example_first_last_frames,
    }

    try:
        examples[args.example](args.api_key)
    except TimeoutError as e:
        print(f"\n[超时] {e}")
    except Exception as e:
        print(f"\n[错误] {e}")


if __name__ == "__main__":
    main()
