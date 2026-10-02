# “拿 YouTube / 社交平台当免费网盘” 深度调研报告

> 对应提问：*“话说上传服务有吗，比如 youtube 哈哈哈，直接拿他们当云盘”*  
> 归档路径：`docs/repo/media-storage-abuse-research.md`  
> 核心结论：**理论可行、PoC 遍地，但工程体验极差（3~8倍体积膨胀、数小时转码等待、每日 API 额度极低），且面临 Google 全家桶账号封禁与平台技术反制的高危风险。**

---

## 一、核心原理与典型开源项目（以 YouTube 为代表）

将视频/多媒体平台滥用为云盘的本质是：**将任意二进制字节流（Blob）编码为合法的多媒体像素或数据包，借助平台不限容量的上传通道存储，下载后通过逆向算法还原为原始文件。**

### 1. 经典代表项目

* **[DvorakDwarf/Infinite-Storage-Glitch (ISG)](https://web.archive.org/web/20230628103818/https://github.com/DvorakDwarf/Infinite-Storage-Glitch)**：
  * 基于 Rust 编写，最早破圈引发全网讨论的 PoC 项目。作者后因道德顾虑和滥用风险主动归档并删库，但社区留存有大量 Fork（如 `CodeWizarz/Storage-Glitch`）。
* **[flonle/youbit](https://github.com/flonle/youbit)**：
  * 基于 Python/Cython 编写，是目前工程完成度最高、抵抗压缩与纠错最完备的开源实现。
* **[AlfredoSequeida/fvid](https://github.com/AlfredoSequeida/fvid)**：
  * 早期的 Python 工具，将文件转换为高频黑白噪点视频。
* **[MichelLeonardo/yt-fs](https://github.com/MichelLeonardo/yt-fs)** / **[PulseBeat02/yt-media-storage](https://github.com/PulseBeat02/yt-media-storage)**：
  * 将 YouTube 封装为文件系统接口或冷存储备份层。

---

## 二、核心挑战：如何对抗 YouTube 暴力有损转码？

YouTube 绝不会提供原始上传文件的原样下载，所有视频入库后都会被推入转码管道，使用 **H.264 (AVC1)、VP9、AV1** 进行激进的有损压缩。有损转码会产生色度丢弃、块效应、高频高斯模糊与量化误差。开源项目主要依靠以下 4 层抗噪机制攻克：

1. **规避色度抽样（Chroma Subsampling 4:2:0）**：
   * 工业级视频编码几乎一律采用 YUV 4:2:0 空间，U/V 色度通道在水平与垂直方向被削减一半。
   * 开源方案放弃 RGB，采用**纯单通道灰度图（Luma / Greyscale）**。全分辨率黑白二值（0 表示纯黑，255 表示纯白）完全运行在无损失的亮度通道上，彻底免疫色度抽样。
2. **空间放大（Macro-Pixels）与 BPP**：
   * **1 BPP**：1 个像素对应 1 bit（$\ge 128$ 为 1，$< 128$ 为 0）。只要转码噪点漂移不超过 127 阶就不会翻转。
   * **宏块聚合**：将 1 个 bit 放大为 $2 \times 2$ 或 $4 \times 4$ 像素矩阵，解码时统计区域均值或多数投票。
3. **前向纠错码（FEC / Reed-Solomon）**：
   * **YouBit** 引入了高速 C 优化的 **Reed-Solomon（RS 纠错算法）**，为原始数据注入冗余校验符号，允许在整帧损毁 5%~20% 的极端情况下实现数学级精确恢复。
4. **动态欺骗码率分配（Null Frames 填充）**：
   * 纯随机噪点信息熵过高会导致编码器剧烈涂抹。YouBit 采用 **1 FPS + 插入空白帧** 策略，欺骗编码器为有效帧分配更高码率。

---

## 三、其它平台的“骚操作”横向对比

| 平台 | 代表项目 / 模式 | 底层技术原理 | 现状与官方反制机制 |
| :--- | :--- | :--- | :--- |
| **Telegram** | **TeleDrive**、**tg-cloud**、**tgdrive** | 通过 MTProto API 切片上传至个人收藏夹或私有频道，非会员单文件 2GB，会员 4GB。 | **高度风控**：大流量脚本会被官方下发 `FLOOD_WAIT`；账号易被降权或封号；TeleDrive 因 API 限流和带宽成本难以为继。 |
| **Discord** | **Discord-Drive**、**DisDrive** | 将大文件分片（如 10MB/25MB）发至私人 Server，本地 SQLite 记录 Message ID 和 CDN 直链。 | **毁灭性打击**：Discord 于 2023 年底推行认证签名 URL，**外部直链 24 小时后强制失效**，外链云盘全面作废。 |
| **GitHub** | **Releases 滥用**、**Git LFS**、**Issues 附件** | 利用 GitHub Releases 单产物 2GB 上限写 Action 自动上传备份；或在 Issue 评论拖拽文件拿直链。 | **封号与删库**：违反《GitHub 可接受使用政策》（AUP），触发风控后仓库会被 DMCA/Abuse 封锁，账号面临连带 Shadowban。 |
| **图床/图片** | **“图种” (Zip-in-JPG)**、**LSB 隐写** | 将 Zip 追加在 JPEG 的 EOI 结束标志（`FF D9`）之后；或在 PNG 最低有效位（LSB）藏匿数据。 | **完全失效**：现代 Web 平台强制通过 MozJPEG/WebP 二次转码并剥除 EXIF，`FF D9` 后的内容直接被截断丢弃，LSB 被量化矩阵彻底清洗。 |

---

## 四、YouTube 方案的技术瓶颈与工程现实

1. **存储密度低下与严重的体积膨胀**：
   * 1080p 单帧纯载荷仅 ~259 KB。加上 RS 纠错码冗余（~15%）及 1 FPS 填充，本地视频大小为原始文件的 **3.9 ~ 8.3 倍**；下载视频约为原始文件的 **3.4 倍**。存 1GB 文件需上传 4~8GB 视频。
2. **致命延迟：以“小时”为单位的处理队列**：
   * 上传完成后 360p 低清流因模糊无法解码，**必须等待服务端 1080p 高清转码完毕**，耗时 15 分钟至 3 小时不等，根本无法即存即取。
3. **API 配额死锁与风控封号**：
   * YouTube Data API v3 每日基准配额为 10,000 units，单次 `videos.insert` 消耗 1,600 units，**单日官方 API 最多只能上传 6 个视频**。
   * 提取 Cookie 模拟上传高熵噪点视频，会直接被 Google 反垃圾 AI 标记为异常，触发验证码或锁定频道。

---

## 五、服务条款（ToS）与封号风险

1. **Google / YouTube ToS 违规**：明确禁止非服务预期的自动化访问与规避技术限制。
2. **毁灭性的“全家桶连坐”**：YouTube 账号直属于 **Google Account**。严重滥用会导致 **Google Account Suspended**——直接导致该账号绑定的 **Gmail、Google Drive 正常资料、Google Photos、Android 设备 Play 服务备份以及 Google Pay 全数被冻结**，申诉成功率微乎其微。

---

## 六、综合结论与正规低成本替代方案

> **结论**：将 YouTube 当网盘只是一次极富黑客精神的 PoC 概念验证。在实际生产和生活中，它兼具极高的膨胀率、超长转码延迟、严苛的配额死锁，以及失去整个 Google 账号的灾难性风险。

### 正规高性价比方案推荐

| 方案 / 平台 | 免费额度 / 计费标准 | 核心优势 | 推荐搭配 |
| :--- | :--- | :--- | :--- |
| **Cloudflare R2** | **10 GB 永久免费**<br>超出部分 \$0.015/GB/月<br>**0 出网流量费（\$0 Egress）** | 兼容标准 AWS S3 API；**全球出网流量完全免费**，彻底告别天价下行账单。 | 配合 **Alist** 或 **Rclone** 挂载为本地磁盘，适合日常网盘与文件分发。 |
| **Backblaze B2** | **10 GB 永久免费**<br>超出部分 \$0.06/GB/月<br>加入带宽联盟可免流量费 | 价格仅为 AWS S3 的 1/4 左右，业内公认最稳定廉价的企业级存储。 | 适合电脑整机离线冷备、异地容灾备份。 |
| **Oracle Cloud (OCI)** | **200 GB 块存储**<br>**10 GB 对象存储**<br>每月 10TB 免费出网流量 | 甲骨文“永久免费”配额，自带 200GB 虚拟磁盘。 | 部署轻量 MinIO、Nextcloud 或 RustDesk 服务。 |
| **Telegram（个人合规模式）** | 完全免费（单文件 2GB / 会员 4GB） | 官方客户端原生体验，全平台秒级同步。 | **仅用于手动在“Saved Messages”存放文档、离线安装包**，严禁使用自动化切片脚本。 |
| **自建私有存储 (NAS / 移动硬盘)** | 一次性硬件成本，无月费 | 局域网千兆/万兆极速读写，数据隐私 100% 自主可控。 | 私密照片、工程项目、4K 影音库主力存储。 |

---
*调研完成日期：2026-09-29*
