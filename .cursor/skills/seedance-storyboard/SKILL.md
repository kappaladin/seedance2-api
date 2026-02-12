---
name: seedance-storyboard
description: 引导用户将想法转换为 Seedance 2.0 专业分镜提示词，使用 Seedream 4.5 生成参考图，并通过速推 MCP 提交视频生成任务、轮询结果。当用户提到"分镜"、"storyboard"、"seedance"、"视频脚本"、"拍个视频"时使用此 skill。
---

# Seedance 2.0 分镜创作与视频生成

从创意到成片的全流程：引导分镜 → 画参考图 → 提交视频 → 获取结果。

## 工作流程

### Step 1: 理解用户想法

收集以下信息（缺失的主动询问）：

- **故事核心**：一句话概括要拍什么
- **时长**：4-15 秒
- **画面比例**：16:9 / 9:16 / 1:1 / 21:9 / 4:3 / 3:4
- **视觉风格**：写实/动画/水墨/科幻/赛博朋克等
- **素材情况**：是否有现成图片/视频/音频，还是需要 AI 生成

### Step 2: 深入挖掘（5 个维度）

针对每个维度引导用户补充细节：

1. **内容** - 主角是谁？做什么？在哪里？
2. **视觉** - 光影、色调、质感、氛围
3. **镜头** - 推/拉/摇/移/跟/环绕/升降
4. **动作** - 主体的具体动作和节奏
5. **声音** - 配乐风格、音效、对白

### Step 3: 构建分镜结构

按时间轴拆分镜头，使用以下公式：

```
【风格】_____风格，_____秒，_____比例，_____氛围

0-X秒：[镜头运动] + [画面内容] + [动作描述]
X-Y秒：[镜头运动] + [画面内容] + [动作描述]
...

【声音】_____配乐 + _____音效 + _____对白
【参考】@图片1 _____，@视频1 _____
```

详细模板和示例见 [reference.md](reference.md)。

### Step 4: 生成参考图（如需要）

若用户没有现成素材，使用 Seedream 4.5 生成角色图、场景图、首帧/尾帧等。

**文生图：**

调用 `submit_task` 工具：
- model_id: `fal-ai/bytedance/seedream/v4.5/text-to-image`
- parameters:
  - prompt: 详细的图片描述（英文效果更佳）
  - image_size: 根据视频比例选择（如视频 16:9 则用 `landscape_16_9`）
  - num_images: 需要的数量（1-6）

**图像编辑（基于现有图片修改）：**

调用 `submit_task` 工具：
- model_id: `fal-ai/bytedance/seedream/v4.5/edit`
- parameters:
  - prompt: 编辑指令（用 Figure 1/2/3 引用图片）
  - image_urls: 输入图片 URL 数组
  - image_size: 输出尺寸

**轮询图片结果：**

调用 `get_task` 工具查询状态，图片约 1-2 分钟完成。
- 首次 30 秒后查询
- 之后每 30 秒查询一次
- 状态为 `completed` 时提取图片 URL

**image_size 对照表：**

| 视频比例 | 推荐 image_size | 说明 |
|---------|----------------|------|
| 16:9 | landscape_16_9 | 横屏 |
| 9:16 | portrait_16_9 | 竖屏 |
| 4:3 | landscape_4_3 | 横屏 |
| 3:4 | portrait_4_3 | 竖屏 |
| 1:1 | square_hd | 方形 |
| 21:9 | landscape_16_9 | 近似超宽屏 |

### Step 5: 生成专业提示词

将分镜结构和参考图整合为最终提示词：

- 用 `@图片1`、`@图片2` 等引用 media_files 中的文件（按顺序）
- 用 `@视频1` 引用视频素材
- 用 `@音频1` 引用音频素材

**引用语法示例：**

```
@图片1 作为首帧，@图片2 作为角色形象参考，参考@视频1的运镜方式
```

### Step 6: 提交视频任务

**处理素材 URL：**
- Seedream 生成的图片：已有 URL，直接使用
- 用户提供的网络图片：直接使用
- 用户提供的本地图片：先调用 `upload_image` 工具上传获取 URL

**提交 Seedance 2.0 任务：**

调用 `submit_task` 工具：
- model_id: `st-ai/super-seed2`
- parameters:
  - prompt: Step 5 生成的完整提示词
  - media_files: 所有素材 URL 的数组（顺序对应 @图片1、@图片2...）
  - aspect_ratio: 画面比例（`16:9` / `9:16` / `1:1` / `21:9` / `4:3` / `3:4`）
  - duration: 时长秒数字符串（`"4"` - `"15"`）
  - model: `seedance_2.0_fast`（默认快速）或 `seedance_2.0`（标准质量）

### Step 7: 轮询等待视频结果

视频生成约需 10 分钟。轮询策略：

1. 提交后告知用户"视频正在生成，预计 10 分钟"
2. 首次 **60 秒**后调用 `get_task` 查询
3. 之后每 **90 秒**查询一次
4. 每次查询后向用户报告状态：
   - `pending` → "排队中..."
   - `processing` → "生成中..."
   - `completed` → 提取视频 URL 并展示给用户
   - `failed` → 告知失败原因，建议调整提示词重试

## 完整流程示例

用户说："帮我做一个宇航员在火星行走的视频"

```
1. 收集信息 → 15秒，16:9，电影级科幻风格，无现成素材

2. 用 Seedream 4.5 生成宇航员图 + 火星场景图
   submit_task("fal-ai/bytedance/seedream/v4.5/text-to-image", {
     prompt: "An astronaut in a white spacesuit walking on Mars...",
     image_size: "landscape_16_9"
   })
   → 轮询 get_task → 获得图片 URL

3. 编写提示词：
   "电影级写实科幻风格，15秒，16:9
    0-3秒：大远景缓慢推近，@图片1 火星峡谷全景，红色沙尘弥漫
    3-8秒：中景跟随，@图片2 宇航员缓慢行走，脚印留在沙地
    8-12秒：特写头盔面罩，反射出壮丽火星地貌
    12-15秒：远景拉远，宇航员渐行渐远
    【声音】低沉风声 + 史诗管弦乐"

4. 提交视频任务
   submit_task("st-ai/super-seed2", {
     prompt: "上述提示词",
     media_files: [火星场景URL, 宇航员URL],
     aspect_ratio: "16:9",
     duration: "15"
   })

5. 轮询 get_task，~10分钟后获得视频 URL
```

## 模型参数速查

### Seedream 4.5 文生图

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 图片描述 |
| image_size | string | 否 | auto_2K / auto_4K / square_hd / portrait_4_3 / portrait_16_9 / landscape_4_3 / landscape_16_9 |
| num_images | int | 否 | 1-6，默认 1 |

### Seedream 4.5 图像编辑

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 编辑指令，用 Figure 1/2/3 引用 |
| image_urls | array | 是 | 输入图片 URL 列表 |
| image_size | string | 否 | 同上 |
| num_images | int | 否 | 1-6，默认 1 |

### Seedance 2.0 视频

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 分镜提示词，用 @图片1/@视频1/@音频1 引用 |
| media_files | array | 是 | 素材 URL 列表（至少 1 个） |
| aspect_ratio | string | 否 | 21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16 |
| duration | string | 否 | "4"-"15"，默认 "5" |
| model | string | 否 | seedance_2.0_fast（默认）/ seedance_2.0 |

## MCP 工具速查

| 操作 | 工具 | 关键参数 |
|------|------|---------|
| 提交任务 | submit_task | model_id, parameters |
| 查询结果 | get_task | task_id |
| 上传图片 | upload_image | image_url 或 image_data |
| 查询余额 | get_balance | 无 |

## Seedance 2.0 限制

- 不支持上传写实真人脸部素材
- 最多 12 个文件：图片 ≤ 9 + 视频 ≤ 3 + 音频 ≤ 3
- 视频/音频参考总时长 ≤ 15 秒
- 含视频参考会消耗更多积分

## 更多资源

详细分镜模板、完整示例和镜头词汇表见 [reference.md](reference.md)。
