/**
 * Seedance 2.0 API Java 调用示例
 *
 * 使用方法:
 *   1. 编译: javac Demo.java
 *   2. 运行: java Demo sk-your-api-key
 *   3. 指定示例: java Demo sk-your-api-key 2
 *
 * 零依赖 — 仅使用 JDK 内置类，无需额外 jar 包（需 JDK 11+）
 *
 * 获取 API Key: https://www.xskill.ai/#/v2/api-keys
 * 模型文档:   https://www.xskill.ai/#/v2/models?model=st-ai%2Fsuper-seed2
 */

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.stream.Collectors;

public class Demo {

    // ============================================================
    // 配置
    // ============================================================
    private static final String BASE_URL = "https://api.xskill.ai";
    private static final String CREATE_URL = BASE_URL + "/api/v3/tasks/create";
    private static final String QUERY_URL = BASE_URL + "/api/v3/tasks/query";
    private static final String MODEL_ID = "st-ai/super-seed2";

    private static final int POLL_INTERVAL = 5000;   // 轮询间隔（毫秒）
    private static final int MAX_POLL_TIME = 600000;  // 最大等待时间（毫秒）

    private final String apiKey;

    public Demo(String apiKey) {
        this.apiKey = apiKey;
    }

    // ============================================================
    // HTTP 工具方法
    // ============================================================

    /**
     * 发送 POST 请求并返回响应 JSON 字符串
     */
    private String postRequest(String urlStr, String jsonBody) throws IOException {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        try {
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Authorization", "Bearer " + apiKey);
            conn.setDoOutput(true);
            conn.setConnectTimeout(30000);
            conn.setReadTimeout(30000);

            // 写入请求体
            try (OutputStream os = conn.getOutputStream()) {
                os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
            }

            int statusCode = conn.getResponseCode();
            boolean isError = statusCode >= 400;

            // 读取响应
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(
                            isError ? conn.getErrorStream() : conn.getInputStream(),
                            StandardCharsets.UTF_8))) {
                String responseBody = reader.lines().collect(Collectors.joining("\n"));

                if (isError) {
                    throw new IOException("HTTP " + statusCode + ": " + responseBody);
                }
                return responseBody;
            }
        } finally {
            conn.disconnect();
        }
    }

    // ============================================================
    // 简易 JSON 解析（零依赖）
    // ============================================================

    /** 从 JSON 字符串中提取指定 key 的字符串值 */
    private static String jsonGetString(String json, String key) {
        String search = "\"" + key + "\"";
        int idx = json.indexOf(search);
        if (idx == -1) return null;

        int colonIdx = json.indexOf(':', idx + search.length());
        if (colonIdx == -1) return null;

        // 跳过空白
        int start = colonIdx + 1;
        while (start < json.length() && json.charAt(start) == ' ') start++;

        if (start >= json.length()) return null;

        // 字符串值
        if (json.charAt(start) == '"') {
            int end = json.indexOf('"', start + 1);
            return json.substring(start + 1, end);
        }

        // 数字或其他值
        int end = start;
        while (end < json.length() && json.charAt(end) != ',' && json.charAt(end) != '}') {
            end++;
        }
        return json.substring(start, end).trim();
    }

    /** 从 JSON 数组中提取第一个字符串元素 */
    private static String jsonGetFirstArrayElement(String json, String arrayKey) {
        String search = "\"" + arrayKey + "\"";
        int idx = json.indexOf(search);
        if (idx == -1) return null;

        int bracketIdx = json.indexOf('[', idx);
        if (bracketIdx == -1) return null;

        int quoteStart = json.indexOf('"', bracketIdx + 1);
        if (quoteStart == -1) return null;

        int quoteEnd = json.indexOf('"', quoteStart + 1);
        return json.substring(quoteStart + 1, quoteEnd);
    }

    // ============================================================
    // 简易 JSON 构建
    // ============================================================

    /** 构建 JSON 数组字符串 */
    private static String buildJsonArray(String... urls) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < urls.length; i++) {
            if (i > 0) sb.append(",");
            sb.append("\"").append(urls[i]).append("\"");
        }
        sb.append("]");
        return sb.toString();
    }

    /** 构建全能模式（omni_reference）的创建任务 JSON */
    private static String buildOmniPayload(String prompt, String imageFiles,
                                            String videoFiles, String audioFiles,
                                            String ratio, int duration, String mode) {
        StringBuilder params = new StringBuilder();
        params.append("\"prompt\":\"").append(prompt).append("\",");
        params.append("\"functionMode\":\"omni_reference\",");
        params.append("\"ratio\":\"").append(ratio).append("\",");
        params.append("\"duration\":").append(duration).append(",");
        params.append("\"model\":\"").append(mode).append("\"");
        if (imageFiles != null) params.append(",\"image_files\":").append(imageFiles);
        if (videoFiles != null) params.append(",\"video_files\":").append(videoFiles);
        if (audioFiles != null) params.append(",\"audio_files\":").append(audioFiles);

        return "{\"model\":\"" + MODEL_ID + "\",\"params\":{" + params + "}}";
    }

    /** 构建首尾帧模式（first_last_frames）的创建任务 JSON */
    private static String buildFramesPayload(String prompt, String filePaths,
                                              String ratio, int duration, String mode) {
        return "{\"model\":\"" + MODEL_ID + "\",\"params\":{"
                + "\"prompt\":\"" + prompt + "\","
                + "\"functionMode\":\"first_last_frames\","
                + "\"ratio\":\"" + ratio + "\","
                + "\"duration\":" + duration + ","
                + "\"model\":\"" + mode + "\""
                + (filePaths != null ? ",\"filePaths\":" + filePaths : "")
                + "}}";
    }

    // ============================================================
    // 核心方法
    // ============================================================

    /**
     * 创建视频生成任务（全能模式）
     *
     * @param prompt      提示词，支持 @image_file_1/@video_file_1/@audio_file_1 引用
     * @param imageFiles  参考图片 URL 数组（最多 9 张）
     * @param videoFiles  参考视频 URL 数组（最多 3 个，总时长 ≤ 15s）
     * @param audioFiles  参考音频 URL 数组（最多 3 个）
     * @param ratio       画面比例：21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16
     * @param duration    视频时长（秒），4-15
     * @param mode        速度模式：seedance_2.0_fast / seedance_2.0
     * @return task_id
     */
    public String createOmniTask(String prompt, String[] imageFiles, String[] videoFiles,
                                  String[] audioFiles, String ratio, int duration,
                                  String mode) throws IOException {
        String imgArray = imageFiles != null ? buildJsonArray(imageFiles) : null;
        String vidArray = videoFiles != null ? buildJsonArray(videoFiles) : null;
        String audArray = audioFiles != null ? buildJsonArray(audioFiles) : null;
        String payload = buildOmniPayload(prompt, imgArray, vidArray, audArray, ratio, duration, mode);

        System.out.println("[创建任务] 功能模式: omni_reference");
        System.out.println("[创建任务] 提示词: " + prompt);
        if (imageFiles != null) System.out.println("[创建任务] 参考图片: " + String.join(", ", imageFiles));
        if (videoFiles != null) System.out.println("[创建任务] 参考视频: " + String.join(", ", videoFiles));
        if (audioFiles != null) System.out.println("[创建任务] 参考音频: " + String.join(", ", audioFiles));

        String response = postRequest(CREATE_URL, payload);

        String code = jsonGetString(response, "code");
        if (!"200".equals(code)) {
            throw new RuntimeException("创建任务失败: " + response);
        }

        String taskId = jsonGetString(response, "task_id");
        String price = jsonGetString(response, "price");
        System.out.println("[创建任务] 成功! task_id=" + taskId + ", 消耗积分=" + (price != null ? price : "未知"));

        return taskId;
    }

    /**
     * 创建首尾帧视频任务
     *
     * @param prompt     提示词
     * @param filePaths  图片 URL 数组（0张=文生视频，1张=首帧，2张=首尾帧）
     * @param ratio      画面比例
     * @param duration   视频时长（秒），4-15
     * @param mode       速度模式
     * @return task_id
     */
    public String createFramesTask(String prompt, String[] filePaths, String ratio,
                                    int duration, String mode) throws IOException {
        String pathArray = filePaths != null ? buildJsonArray(filePaths) : null;
        String payload = buildFramesPayload(prompt, pathArray, ratio, duration, mode);

        System.out.println("[创建任务] 功能模式: first_last_frames");
        System.out.println("[创建任务] 提示词: " + prompt);
        if (filePaths != null) System.out.println("[创建任务] 首尾帧: " + String.join(", ", filePaths));

        String response = postRequest(CREATE_URL, payload);

        String code = jsonGetString(response, "code");
        if (!"200".equals(code)) {
            throw new RuntimeException("创建任务失败: " + response);
        }

        String taskId = jsonGetString(response, "task_id");
        String price = jsonGetString(response, "price");
        System.out.println("[创建任务] 成功! task_id=" + taskId + ", 消耗积分=" + (price != null ? price : "未知"));

        return taskId;
    }

    /**
     * 查询任务状态
     *
     * @param taskId 任务 ID
     * @return 响应 JSON 字符串
     */
    public String queryTask(String taskId) throws IOException {
        String payload = "{\"task_id\":\"" + taskId + "\"}";
        return postRequest(QUERY_URL, payload);
    }

    /**
     * 轮询等待任务完成
     *
     * @param taskId 任务 ID
     * @return 视频 URL
     */
    public String waitForResult(String taskId) throws IOException, InterruptedException {
        System.out.println("\n[轮询] 开始等待任务完成 (最大 " + (MAX_POLL_TIME / 1000) + "s, 每 " + (POLL_INTERVAL / 1000) + "s 查询一次)...");
        int elapsed = 0;

        while (elapsed < MAX_POLL_TIME) {
            String response = queryTask(taskId);
            String status = jsonGetString(response, "status");
            System.out.println("[轮询] " + (elapsed / 1000) + "s - 状态: " + status);

            if ("completed".equals(status)) {
                String videoUrl = jsonGetFirstArrayElement(response, "images");
                System.out.println("\n[完成] 视频生成成功!");
                System.out.println("[完成] 视频地址: " + videoUrl);
                return videoUrl;
            }

            if ("failed".equals(status)) {
                String error = jsonGetString(response, "error");
                throw new RuntimeException("任务失败: " + (error != null ? error : response));
            }

            Thread.sleep(POLL_INTERVAL);
            elapsed += POLL_INTERVAL;
        }

        throw new RuntimeException("任务超时: 等待 " + (MAX_POLL_TIME / 1000) + "s 后仍未完成");
    }

    // ============================================================
    // 使用示例
    // ============================================================

    /** 示例 1: 单图生成视频（全能模式） */
    public void exampleSingleImage() throws Exception {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("示例 1: 单图生成视频（全能模式）");
        System.out.println("=".repeat(60));

        String taskId = createOmniTask(
                "@image_file_1 角色在森林中缓步行走，阳光透过树叶洒下斑驳光影，微风吹动发丝",
                new String[]{"https://your-character-image.png"},
                null, null,
                "9:16", 8, "seedance_2.0_fast"
        );
        waitForResult(taskId);
    }

    /** 示例 2: 角色动作迁移（图片 + 视频，全能模式） */
    public void exampleImageAndVideo() throws Exception {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("示例 2: 角色动作迁移（图片 + 视频）");
        System.out.println("=".repeat(60));

        String taskId = createOmniTask(
                "@image_file_1 中的人物按照 @video_file_1 的动作和运镜风格进行表演，电影级光影",
                new String[]{"https://your-character-image.png"},
                new String[]{"https://your-reference-video.mp4"},
                null,
                "16:9", 5, "seedance_2.0_fast"
        );
        waitForResult(taskId);
    }

    /** 示例 3: 音频驱动口型（图片 + 音频，全能模式） */
    public void exampleAudioLipsync() throws Exception {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("示例 3: 音频驱动口型（图片 + 音频）");
        System.out.println("=".repeat(60));

        String taskId = createOmniTask(
                "@image_file_1 角色说话，配合 @audio_file_1 的内容，表情自然生动",
                new String[]{"https://your-character-image.png"},
                null,
                new String[]{"https://your-audio-file.mp3"},
                "16:9", 5, "seedance_2.0_fast"
        );
        waitForResult(taskId);
    }

    /** 示例 4: 首尾帧视频生成 */
    public void exampleFirstLastFrames() throws Exception {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("示例 4: 首尾帧视频生成");
        System.out.println("=".repeat(60));

        String taskId = createFramesTask(
                "镜头从首帧缓缓过渡到尾帧，画面流畅自然，电影级光影效果",
                new String[]{
                        "https://your-first-frame.png",
                        "https://your-last-frame.png"
                },
                "16:9", 5, "seedance_2.0_fast"
        );
        waitForResult(taskId);
    }

    // ============================================================
    // 入口
    // ============================================================
    public static void main(String[] args) {
        if (args.length < 1 || args[0].isEmpty()) {
            System.err.println("错误: 请提供 API Key");
            System.err.println("  运行方式: java Demo sk-your-api-key");
            System.err.println("  指定示例: java Demo sk-your-api-key 2");
            System.err.println("\n获取 API Key: https://www.xskill.ai/#/v2/api-keys");
            System.exit(1);
        }

        String apiKey = args[0];
        int exampleNum = args.length >= 2 ? Integer.parseInt(args[1]) : 1;

        Demo demo = new Demo(apiKey);

        try {
            switch (exampleNum) {
                case 1:
                    demo.exampleSingleImage();
                    break;
                case 2:
                    demo.exampleImageAndVideo();
                    break;
                case 3:
                    demo.exampleAudioLipsync();
                    break;
                case 4:
                    demo.exampleFirstLastFrames();
                    break;
                default:
                    System.err.println("错误: 无效的示例编号 " + exampleNum + "，可选 1/2/3/4");
                    System.exit(1);
            }
        } catch (Exception e) {
            System.err.println("\n[错误] " + e.getMessage());
            System.exit(1);
        }
    }
}
