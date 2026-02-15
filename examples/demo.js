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
 * @param {string} options.prompt          提示词，支持 @image_file_1/@video_file_1/@audio_file_1 引用语法
 * @param {string[]} [options.imageFiles]  参考图片 URL 列表（omni_reference 模式，最多 9 张）
 * @param {string[]} [options.videoFiles]  参考视频 URL 列表（omni_reference 模式，最多 3 个）
 * @param {string[]} [options.audioFiles]  参考音频 URL 列表（omni_reference 模式，最多 3 个）
 * @param {string[]} [options.filePaths]   图片 URL 列表（first_last_frames 模式：0张=文生视频，1张=首帧，2张=首尾帧）
 * @param {string} [options.functionMode="omni_reference"]  功能模式：omni_reference / first_last_frames
 * @param {string} [options.ratio="16:9"]  画面比例：21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16
 * @param {number} [options.duration=5]    视频时长（秒），4-15
 * @param {string} [options.mode="seedance_2.0_fast"] 速度模式：seedance_2.0_fast / seedance_2.0
 * @returns {Promise<object>} API 响应
 */
async function createTask({
  prompt,
  imageFiles,
  videoFiles,
  audioFiles,
  filePaths,
  functionMode = "omni_reference",
  ratio = "16:9",
  duration = 5,
  mode = "seedance_2.0_fast",
}) {
  const params = {
    prompt,
    functionMode,
    ratio,
    duration,
    model: mode,
  };

  // 根据功能模式设置素材参数
  if (functionMode === "omni_reference") {
    if (imageFiles?.length) params.image_files = imageFiles;
    if (videoFiles?.length) params.video_files = videoFiles;
    if (audioFiles?.length) params.audio_files = audioFiles;
  } else if (functionMode === "first_last_frames") {
    if (filePaths?.length) params.filePaths = filePaths;
  }

  const payload = {
    model: MODEL_ID,
    params,
  };

  console.log(`[创建任务] 功能模式: ${functionMode}`);
  console.log(`[创建任务] 提示词: ${prompt}`);
  if (imageFiles?.length) console.log(`[创建任务] 参考图片: ${imageFiles.join(", ")}`);
  if (videoFiles?.length) console.log(`[创建任务] 参考视频: ${videoFiles.join(", ")}`);
  if (audioFiles?.length) console.log(`[创建任务] 参考音频: ${audioFiles.join(", ")}`);
  if (filePaths?.length) console.log(`[创建任务] 首尾帧图片: ${filePaths.join(", ")}`);

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
      const videoUrl = result.data?.result?.output?.images?.[0] || "";
      console.log(`\n[完成] 视频生成成功!`);
      console.log(`[完成] 视频地址: ${videoUrl}`);
      return result;
    }

    if (status === "failed") {
      const errorMsg = result.data?.error || "未知错误";
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

/** 示例 1: 单图生成视频（全能模式） */
async function exampleSingleImage() {
  console.log("\n" + "=".repeat(60));
  console.log("示例 1: 单图生成视频（全能模式）");
  console.log("=".repeat(60));

  const result = await createTask({
    prompt: "@image_file_1 角色在森林中缓步行走，阳光透过树叶洒下斑驳光影，微风吹动发丝",
    imageFiles: ["https://your-character-image.png"],
    ratio: "9:16",
    duration: 8,
  });

  await waitForResult(result.data.task_id);
}

/** 示例 2: 角色动作迁移（图片 + 视频，全能模式） */
async function exampleImageAndVideo() {
  console.log("\n" + "=".repeat(60));
  console.log("示例 2: 角色动作迁移（图片 + 视频）");
  console.log("=".repeat(60));

  const result = await createTask({
    prompt: "@image_file_1 中的人物按照 @video_file_1 的动作和运镜风格进行表演，电影级光影",
    imageFiles: ["https://your-character-image.png"],
    videoFiles: ["https://your-reference-video.mp4"],
    ratio: "16:9",
    duration: 5,
  });

  await waitForResult(result.data.task_id);
}

/** 示例 3: 音频驱动口型（图片 + 音频，全能模式） */
async function exampleAudioLipsync() {
  console.log("\n" + "=".repeat(60));
  console.log("示例 3: 音频驱动口型（图片 + 音频）");
  console.log("=".repeat(60));

  const result = await createTask({
    prompt: "@image_file_1 角色说话，配合 @audio_file_1 的内容，表情自然生动",
    imageFiles: ["https://your-character-image.png"],
    audioFiles: ["https://your-audio-file.mp3"],
    ratio: "16:9",
    duration: 5,
  });

  await waitForResult(result.data.task_id);
}

/** 示例 4: 首尾帧视频生成（first_last_frames 模式） */
async function exampleFirstLastFrames() {
  console.log("\n" + "=".repeat(60));
  console.log("示例 4: 首尾帧视频生成");
  console.log("=".repeat(60));

  const result = await createTask({
    prompt: "镜头从首帧缓缓过渡到尾帧，画面流畅自然，电影级光影效果",
    filePaths: [
      "https://your-first-frame.png",
      "https://your-last-frame.png",
    ],
    functionMode: "first_last_frames",
    ratio: "16:9",
    duration: 5,
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
    4: exampleFirstLastFrames,
  };

  const runExample = examples[exampleNum];
  if (!runExample) {
    console.error(`错误: 无效的示例编号 ${exampleNum}，可选 1/2/3/4`);
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
