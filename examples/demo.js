/**
 * Seedance 2.0 API Node.js 调用示例
 *
 * 使用方法:
 *   1. 需要 Node.js 18+（内置 fetch）
 *   2. 运行示例: SUTUI_API_KEY=sk-your-api-key node demo.js
 *   3. 指定示例: SUTUI_API_KEY=sk-your-api-key node demo.js 2
 *
 * 获取 API Key: https://www.xskill.ai/#/v2/api-keys
 * 模型文档:   https://www.xskill.ai/#/v2/models?model=st-ai%2Fsuper-seed2
 */

// ============================================================
// 配置
// ============================================================
const BASE_URL = "https://api.xskill.ai";
const CREATE_URL = `${BASE_URL}/api/v3/tasks/create`;
const QUERY_URL = `${BASE_URL}/api/v3/tasks/query`;
const MODEL_ID = "st-ai/super-seed2";

const API_KEY = process.env.SUTUI_API_KEY || "sk-your-api-key";
const POLL_INTERVAL = 5000;   // 轮询间隔（毫秒）
const MAX_POLL_TIME = 600000; // 最大等待时间（毫秒）

// ============================================================
// 核心方法
// ============================================================

/**
 * 发送 POST 请求
 * @param {string} url    请求地址
 * @param {object} body   请求体
 * @returns {Promise<object>} 响应 JSON
 */
async function postRequest(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${API_KEY}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  return response.json();
}

/**
 * 创建视频生成任务
 * @param {object} options
 * @param {string} options.prompt       提示词，支持 @图片1、@视频1 等引用语法
 * @param {string[]} options.mediaFiles 媒体文件 URL 列表
 * @param {string} [options.aspectRatio="16:9"] 画面比例
 * @param {string} [options.duration="5"]       视频时长（秒），4-15
 * @param {string} [options.mode="seedance_2.0_fast"] 速度模式：seedance_2.0_fast / seedance_2.0
 * @returns {Promise<object>} API 响应
 */
async function createTask({ prompt, mediaFiles, aspectRatio = "16:9", duration = "5", mode = "seedance_2.0_fast" }) {
  const payload = {
    model: MODEL_ID,
    params: {
      prompt,
      media_files: mediaFiles,
      aspect_ratio: aspectRatio,
      duration,
      model: mode,
    },
    channel: null,
  };

  console.log(`[创建任务] 提示词: ${prompt}`);
  console.log(`[创建任务] 媒体文件: ${mediaFiles.join(", ")}`);

  const result = await postRequest(CREATE_URL, payload);

  if (result.code !== 200) {
    throw new Error(`创建任务失败: ${JSON.stringify(result)}`);
  }

  const { task_id, price } = result.data;
  console.log(`[创建任务] 成功! task_id=${task_id}, 消耗积分=${price ?? "未知"}`);
  return result;
}

/**
 * 查询任务状态
 * @param {string} taskId 任务 ID
 * @returns {Promise<object>} API 响应
 */
async function queryTask(taskId) {
  return postRequest(QUERY_URL, { task_id: taskId });
}

/**
 * 轮询等待任务完成
 * @param {string} taskId 任务 ID
 * @returns {Promise<object>} 最终查询结果
 */
async function waitForResult(taskId) {
  console.log(`\n[轮询] 开始等待任务完成 (最大 ${MAX_POLL_TIME / 1000}s, 每 ${POLL_INTERVAL / 1000}s 查询一次)...`);
  let elapsed = 0;

  while (elapsed < MAX_POLL_TIME) {
    const result = await queryTask(taskId);
    const status = result.data.status;
    console.log(`[轮询] ${elapsed / 1000}s - 状态: ${status}`);

    if (status === "completed") {
      const videoUrl = result.data.output?.video_url || "";
      console.log(`\n[完成] 视频生成成功!`);
      console.log(`[完成] 视频地址: ${videoUrl}`);
      return result;
    }

    if (status === "failed") {
      const errorMsg = result.data.output?.error || "未知错误";
      throw new Error(`任务失败: ${errorMsg}`);
    }

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL));
    elapsed += POLL_INTERVAL;
  }

  throw new Error(`任务超时: 等待 ${MAX_POLL_TIME / 1000}s 后仍未完成`);
}

// ============================================================
// 使用示例
// ============================================================

/** 示例 1: 单图生成视频 */
async function exampleSingleImage() {
  console.log("\n" + "=".repeat(60));
  console.log("示例 1: 单图生成视频");
  console.log("=".repeat(60));

  const result = await createTask({
    prompt: "@图片1 角色在森林中缓步行走，阳光透过树叶洒下斑驳光影，微风吹动发丝",
    mediaFiles: ["https://your-character-image.png"],
    aspectRatio: "9:16",
    duration: "8",
  });

  await waitForResult(result.data.task_id);
}

/** 示例 2: 角色动作迁移（图片 + 视频） */
async function exampleImageAndVideo() {
  console.log("\n" + "=".repeat(60));
  console.log("示例 2: 角色动作迁移（图片 + 视频）");
  console.log("=".repeat(60));

  const result = await createTask({
    prompt: "@图片1 让角色参考 @视频1 的动作和运镜风格进行表演，电影级光影",
    mediaFiles: [
      "https://your-character-image.png",
      "https://your-reference-video.mp4",
    ],
    aspectRatio: "16:9",
    duration: "5",
  });

  await waitForResult(result.data.task_id);
}

/** 示例 3: 音频驱动口型（图片 + 音频） */
async function exampleAudioLipsync() {
  console.log("\n" + "=".repeat(60));
  console.log("示例 3: 音频驱动口型（图片 + 音频）");
  console.log("=".repeat(60));

  const result = await createTask({
    prompt: "@图片1 角色说话，配合 @音频1 的内容，表情自然生动",
    mediaFiles: [
      "https://your-character-image.png",
      "https://your-audio-file.mp3",
    ],
    aspectRatio: "16:9",
    duration: "5",
  });

  await waitForResult(result.data.task_id);
}

// ============================================================
// 入口
// ============================================================
async function main() {
  if (API_KEY === "sk-your-api-key") {
    console.error("错误: 请提供 API Key");
    console.error("  运行方式: SUTUI_API_KEY=sk-your-api-key node demo.js");
    console.error("\n获取 API Key: https://www.xskill.ai/#/v2/api-keys");
    process.exit(1);
  }

  const exampleNum = parseInt(process.argv[2] || "1", 10);
  const examples = {
    1: exampleSingleImage,
    2: exampleImageAndVideo,
    3: exampleAudioLipsync,
  };

  const runExample = examples[exampleNum];
  if (!runExample) {
    console.error(`错误: 无效的示例编号 ${exampleNum}，可选 1/2/3`);
    process.exit(1);
  }

  try {
    await runExample();
  } catch (error) {
    console.error(`\n[错误] ${error.message}`);
    process.exit(1);
  }
}

main();
