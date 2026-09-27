# 7个神级技巧，彻底去除网站的 AI 味儿！

> 作者：程序员鱼皮
> 来源：博客园 https://www.cnblogs.com/yupi/p/19554255
> 视频版：https://bilibili.com/video/BV1QF6EBiErM
> 开源教程仓库：https://github.com/liyupi/ai-guide
> 本文为个人离线存档，版权归原作者所有。

现在 AI 开发网站的能力已经非常强了。但为啥我用 AI 搓出来的网站一股子 AI 味儿？而这些网站看起来干净很多呢？这就是接下来我要分享的。

- 什么是 AI 编程的 AI 味儿？
- 为什么网站会有 AI 味儿？
- 怎么去除网站的 AI 味儿？

## 什么是 AI 味儿？

所谓的 AI 味儿，就是那种一眼就能看出是 AI 生成的网站，界面样式和内容风格都千篇一律。

1）配色死板：蓝紫渐变色用到吐。

2）布局死板：首屏放个大标题，下面三个卡片并排。

3）字体死板：基本上就是 Inter、Roboto 等几种固定的字体。

4）Emoji 泛滥：什么 🐟4️⃣🐶 之类的，满屏幕都是表情图标。

5）内容空洞：基本没有真实图片，文字风格也比较刻板。

用户看这些网站时就一个感觉：我在跟机器人聊天。

## 为什么网站会有 AI 味儿？

核心原因就俩字：**求稳**。

为啥 AI 那么爱用蓝紫渐变色？因为 AI 的训练数据里，很多现代网站采用 Tailwind 样式库，而这个库的默认主色调就是蓝紫色。AI 在学习数亿行代码时，这些颜色出现的频率是最高的，于是 AI 就认为 "现代化网站 ≈ 蓝紫色渐变"。

并且 AI 学会了一个生存法则：**用最常见的 = 最不容易出错**。

所以当你让 AI "开发一个现代化的网站" 时，AI 为了求稳，就会选择使用蓝紫渐变色。

**那怎么破局？** 很简单，从 "请求者" 变成 "指挥官"。不要只说需求：给我做个网站；而是要明确要求：用深灰色背景、手绘图标、不对称布局、拒绝蓝紫色。用强有力的约束条件，逼着 AI 偏离它的舒适区。

## 怎么去除网站的 AI 味儿？

### 方法 1、让 AI 参考真实网站

最简单粗暴的一招，你看到好看的网站，直接让 AI 学。4 种具体做法：

1. 用 Cursor / Claude Code 等 AI 编程工具（或 Firecrawl MCP）让 AI 直接读取网页：请访问 ai.codefather.cn，提取它的配色方案、字体选择和布局结构，然后生成类似风格的网站。
2. 把网页截图提供给支持图片理解的大模型，搭配文字还原更准确。
3. 用截图转代码工具，如 [Screenshot to Code](https://github.com/abi/screenshot-to-code)，把代码喂给 AI。
4. 直接套用现成网站模板 / 开源项目：
   - [HTML5 UP](https://html5up.net/)：免费响应式网站合集，极简风格
   - [WordPress 官方主题库](https://cn.wordpress.org/themes/)：1 万多个免费主题
   - [Start Bootstrap](https://startbootstrap.com/)：Bootstrap 生态免费模板库
   - [Colorlib](https://colorlib.com/wp/free-wordpress-themes/)：设计精美的免费模板

### 方法 2、设计优先开发

不要上来就让 AI 梭哈整个项目。先让 AI 做个纯静态前端 Demo，对设计满意后，再基于 Demo 代码用同样风格开发完整项目。

- [Google Stitch](https://stitch.withgoogle.com/)：输入描述生成专业界面原型，草图拍照也能转代码
- [Figma](https://www.figma.com/) + [Figma MCP](https://github.com/GLips/Figma-Context-MCP)：先设计后生成
- [Onlook](https://www.onlook.ai/)：设计师直接可视化编辑网页代码

### 方法 3、丰富网站图片

AI 生成的网站一般没有图片。四类资源：

1. 插画库 [unDraw](https://undraw.co/)：免费 SVG 插画，可自定义颜色
2. 图标库 [Iconify](https://iconify.design/)：20 多万个免费矢量图标
3. 真实照片 [Pexels](https://www.pexels.com/)：免费高质量图库，有 API
4. 占位图 [Picsum Photos](https://picsum.photos/)：URL 指定尺寸，每次刷新不同真实照片

### 方法 4、提示词约束

Claude 官方 Cookbook 有篇 [Frontend Aesthetics](https://platform.claude.com/cookbook/coding-prompting-for-frontend-aesthetics) 专门讲这个。几个实用技巧：

**1）反向提示**——不只说"要什么"，更说"不要什么"：

```
设计禁止清单：
❌ 紫色/靛蓝色渐变
❌ 纯平背景色（必须有噪点或渐变）
❌ Hero + 三卡片布局
❌ 完美居中对齐
❌ 高深的专业名词和无意义的空话
❌ Emoji 作为功能图标
❌ 线性动画 ease-in-out
```

**2）角色设定**：

```
你是一位资深独立设计师，专注于《反主流》的网页美学。
你鄙视千篇一律的 SaaS 模板，认为软件界面应该有触感和灵魂。
你的创意边界：
- "现代但不要紫色" → 可以试试深灰+橙色
- "极简但要有温度" → 用大留白+手绘插画
- "科技感但不要冰冷" → 用深色+暖色点缀
```

**3）拒绝空洞文案**：

```
网站的文字内容必须做到：
- 具体化："每天节省 2 小时重复劳动"（不要说"提升生产力"）
- 口语化："用起来就像呼吸一样自然"（不要说"卓越的用户体验"）
- 带情绪："再也不用在 10 个群里找文件了"（不要说"高效协作"）
- 甚至可以挑衅："别再假装你会看完那些 PPT 了"
```

**4）语境注入**——先喂情绪，再提设计：

```
先阅读这段话：《黑客与画家》 - 编程语言是用来思考的
现在根据这种冷静、理性的情绪设计博客首页：
- 配色：深灰+冷蓝
- 布局：理性、有序
- 感觉：沉思的、专注的
```

**5）复用提示词**——保存为项目规则文件 [AGENTS.md](https://agents.md/)：

```markdown
# 项目设计规则（AGENTS.md）

## 角色设定
你是一位资深独立设计师，专注于 "反主流" 的网页美学。
你鄙视千篇一律的 SaaS 模板，追求每个像素都有温度。

## ❌ 绝对禁止项

### 配色禁止
- 紫色/靛蓝色/蓝紫渐变（#6366F1、#8B5CF6）
- 纯平背景色（必须有噪点纹理或渐变）
- Tailwind 默认色板

### 布局禁止
- Hero + 三卡片布局
- 完美居中对齐
- 等宽多栏（必须不对称）

### 文案禁止
- 高深的专业名词和无意义的空话
- Lorem Ipsum 占位文本
- 被动语态和长句

### 组件禁止
- Shadcn/Material UI 默认组件（必须深度定制）
- Emoji 作为功能图标
- 线性动画（ease-in-out）

## ✅ 必须遵守项

### 文案风格
- 口语化，像朋友聊天
- 具体化，有数字和场景
- 可以幽默、自嘲、甚至挑衅
- 每句话不超过 15 个字

### 图片系统
- 图标：使用 Iconify 图标库（https://iconify.design）
- 占位图：使用 Picsum Photos（https://picsum.photos）
- 真实图片：使用 Pexels 搜索（https://www.pexels.com）
- 插画：使用 unDraw（https://undraw.co）
```

### 方法 5、Agent Skills

- **Frontend-design**：Anthropic 官方前端设计技能
  https://github.com/anthropics/skills/tree/main/skills/frontend-design
  Claude Code 安装：`/plugin marketplace add anthropics/skills` → `/plugin install example-skills@anthropic-agent-skills`
- **UI UX Pro Max**：https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
  安装：`npm install -g uipro-cli` → 项目内 `uipro init --ai cursor`

### 方法 6、反 AI 味儿组件库

明确告诉 AI 用小众但有特色的组件库：

- [Aceternity UI](https://ui.aceternity.com/)：闪光粒子、极光背景、流星效果
- [Magic UI](https://magicui.design/)：150+ 动画组件、流光边框、文字渐变
- [DaisyUI](https://daisyui.com/)：30+ 主题（cyberpunk、retro、cupcake 等）
- [Brutalist UI](https://brutalistui.site/)：粗野主义，粗边框、硬阴影、高对比
- [Glass UI](https://ui.glass/)：玻璃拟态
- [ikun-ui](https://github.com/ikun-svelte/ikun-ui)：Svelte.js + UnoCSS
- [Radix UI](https://www.radix-ui.com/)：无样式原语组件
- [Mantine](https://mantine.dev/)：100+ 组件

小众库 AI 可能不熟悉用法，建议装 [Context7](https://context7.com/) 插件或直接把官方文档地址发给 AI。

### 方法 7、自主配色

- [Coolors](https://coolors.co/)：按空格随机生成配色，支持多格式导出
- [Adobe Color](https://color.adobe.com/)：Adobe 官方专业配色工具

生成好配色后，把色值告诉 AI 严格执行。

## 实战案例

1. **个人技术博客**：AGENTS.md 提示词规则 + UI UX Pro Max → 更有极客范儿
2. **SaaS 落地页**：AGENTS.md + UI UX Pro Max + 语境注入（《黑客帝国》红蓝药丸）+ Aceternity UI → 代码雨背景
3. **健身 APP 落地页（移动端）**：AGENTS.md + UI UX Pro Max + ikun-ui

## 最后

AI 生成的效果不理想，可能只是没给足够的明确指令。就像厨师，只说"做个好吃的"，他只能做最大众的家常菜；你说"多放辣椒、不要花椒、多放豆瓣酱"，他就能做出你想要的味道。

**记住，AI 是工具，你才是主导者。**
