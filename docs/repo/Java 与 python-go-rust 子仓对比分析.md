# Java 与 python-go-rust 子仓对比分析

> 调研日期：2026-10-14。方法：本地盘点（脚本扫描三个子仓各项目的 README 头部 + `go.mod` / `pyproject.toml` / `Cargo.toml` / `package.json` 元数据）+ Java 生态官方一手来源核实。仓库内部事实标注为「本地盘点」；外部事实均附官方来源链接。

---

## 一、结论先行（TL;DR）

**Java 在本仓库最适合写什么：**

1. **Spring Boot 企业级 Web 后端**——这是三个现有语言都没有真正覆盖的空位：go 子仓的服务端只有两个轻量自用服务，python 子仓的服务项目全部是学习实验性质；而 Spring Boot 是"企业级长驻后端"的事实标准，内嵌容器、starter 依赖、自动配置、metrics/health checks 开箱即用（[Spring 官方项目页](https://spring.io/projects/spring-boot)）。适合以"学习/实战主流企业框架"为目标起新坑（对标 `django-lab`、`tech_learning_room` 的学框架路线）。
2. **需要 JVM 中间件生态纵深的长驻服务**——Spring 官方栈一页式覆盖 Security、JPA/Redis/Mongo、Kafka/Pulsar/JMS/AMQP、Batch、gRPC、可观测（[Spring Boot 参考手册目录](https://docs.spring.io/spring-boot/reference/packaging/native-image/index.html)、[Spring for Apache Kafka](https://spring.io/projects/spring-kafka)）；这些企业中间件的 Java 客户端生态 Go/Python/Rust 三家均不及。前提是真的出现这类需求，而非为了用而用。
3. **JBang 单文件脚本学 Java 新特性**——源码即程序、`//DEPS` 内嵌依赖声明、本机无 JDK 会自动下载（[JBang 官网](https://www.jbang.dev/)），形态上完全对标本仓 `standalone_scripts` / uv 单脚本，是最低成本的 Java 试水方式。

**Java 不适合写什么（本仓库语境下）：**

1. **Windows 单 exe CLI/TUI**——这是 Go 的最佳位（单二进制、交叉编译、`build.py` + MCP + `--json` + `schema` 标准已成型）；Java 即使用 GraalVM Native Image 补齐了启动与内存（[GraalVM 官方](https://www.graalvm.org/latest/reference-manual/native-image/)），构建链成本仍显著更高，收益为负。
2. **托盘/GUI 桌面壳**——Wails（`glmquotawatch-gui`、`typeai-gui`）与 Fyne 已覆盖且与 Windows 形态契合；JavaFX 成熟但分发需捆绑运行时，无明显增益。
3. **Windows 系统底层 CLI**（NTFS 索引、句柄检测一类）——Rust 手写 FFI、无 GC 更合适（`minieverything`、`whoholds` 已验证此路线）。

一句话：**引入 Java 的唯一充分理由是"企业级 JVM 服务端生态"（Spring Boot + 中间件客户端）；其余形态三语言现有分工均已优于 Java。**

---

## 二、三个子仓现状盘点（本地盘点，2026-10-14）

### 2.1 go_projects（13 个项目）

定位约定（子仓 AGENTS.md）：以 CLI 工具为主，新工具默认配套 MCP + `--json` + `schema` 导出；非 CLI 的服务端/GUI 属例外收录；构建统一 `build.py`，dev/release 隔离，产 exe 默认地鼠图标。

| 项目 | 形态 | 说明 |
|---|---|---|
| agyquota | CLI | Antigravity 模型配额查询 CLI（cobra） |
| clictl | CLI（daemon） | Windows CLI 工具注册器/启动器，JSON 输出 |
| plansql | CLI + MCP | Plan/Spec 状态治理，《CLI 工具开发标准 v2》daemon 架构 |
| pythonlauncher | CLI | 通用 uv 项目启动器小 exe |
| quickask | CLI/TUI | 命令行快速问 AI（由 fyne GUI 版改造而来） |
| sourcecount | CLI + MCP | 源码统计 CLI/MCP 双模式 |
| taskbarguard | CLI/后台守护 | 任务栏图标守卫与自动恢复 |
| typeai | CLI/TUI | 终端 AI 对话（Bubble Tea） |
| zreadmanager | CLI | 后台进程生命周期管理器 |
| glmquotawatch-gui | GUI/托盘 | Wails v3 + 托盘 + Toast 告警仪表盘 |
| typeai-gui | GUI | Wails + xterm.js 桌面终端窗口壳 |
| liteconf | Web 服务 | 轻量配置中心（server + client SDK，例外收录） |
| nginx-ai-proxy | Web 服务 | GLM 反向代理（部署于云服务器） |

小计：**CLI 9 / GUI 2 / Web 服务 2**。

### 2.2 python_projects（13 个项目）

定位约定（父仓 AGENTS.md）：产 exe 默认 Nuitka + 双蛇图标；大量"学习实验"性质项目。

| 项目 | 形态 | 说明 |
|---|---|---|
| archery-mcp | MCP server + CLI | Archery SQL 查询 MCP（stdio server，带子命令为 CLI） |
| douyinnotify | CLI + MCP | 抖音博主更新监控 + 飞书推送 |
| todonotify | CLI | Markdown 待办扫描 + 飞书提醒 |
| zedagentstats | CLI | Zed ACP 智能体会话 Token 统计 |
| zedhub | CLI（daemon）+ HTTP/MCP | 会话统一工具，v2 daemon 标准 Python 试点 |
| django-lab | Web 服务（学习） | Django + DRF 图书馆演示项目 |
| docsearch | Web 服务 | FastAPI 本地语义检索系统 |
| hucci-registration-use-case-layered | Web 服务（学习） | FastAPI 分层架构用例 |
| tech_learning_room | Web 服务（学习/实验） | PostgreSQL/Redis/Celery/Kafka/FastAPI 实验集 |
| sql-pg-sqlalchemy | 学习脚手架 | SQLAlchemy 2.0 + PostgreSQL 学习仓 |
| llm-finetune-lab | 学习实验 | 本地 LoRA/QLoRA 微调实验室 |
| douyin_downloader | 脚本工具 | uv 单脚本下载/提取工具 |
| standalone_scripts | 散脚本集 | 零散单脚本 |

小计：**CLI（含 MCP 双模式）5 / Web 服务 4 / 学习脚手架与实验 2 / 脚本工具 2**。

### 2.3 rust_projects（2 个项目）

定位约定（父仓 AGENTS.md）：stable-x86_64-pc-windows-msvc + rsproxy 镜像。

| 项目 | 形态 | 说明 |
|---|---|---|
| minieverything | CLI | NTFS 全盘文件名索引 + 秒级搜索（clap） |
| whoholds | CLI | Windows 文件句柄占用检测（手写 FFI，clap） |

小计：**CLI 2**，无 GUI、无服务端。

### 2.4 汇总

| 子仓 | 项目数 | CLI 类 | GUI/托盘 | Web 服务 | 学习/脚本 |
|---|---|---|---|---|---|
| go_projects | 13 | 9 | 2 | 2 | 0 |
| python_projects | 13 | 5 | 0 | 4 | 4 |
| rust_projects | 2 | 2 | 0 | 0 | 0 |
| **合计** | **28** | **16** | **2** | **6** | **4** |

格局画像：**本仓主流交付形态是"Windows 桌面/终端的自用成品工具"（CLI 16 + GUI 2 = 64%），服务端只占少数且偏自用轻量或学习性质。**

---

## 三、逐维度对比

### 3.1 打包与分发

| 维度 | Go | Python（本仓） | Rust | Java |
|---|---|---|---|---|
| 默认产物 | 单二进制 exe（交叉编译） | Nuitka 打包 exe（双蛇图标） | cargo 产原生 exe | fat JAR（依赖 JVM）或安装包/原生 exe（需额外工具） |
| 免 JVM 独立分发 | 天然独立 | Nuitka 产独立 exe | 天然独立 | jlink 裁剪运行时 / jpackage 安装包 / GraalVM Native Image |
| 单 exe 体积 | 小（MB 级） | 较大（打包解释器） | 小 | native image 数十 MB 起；jpackage 需捆绑整个运行时 |
| 交叉编译 | 一等公民 | 不支持（本机打包） | 需配置目标工具链 | native image 只能为构建所在的特定 OS/架构产出二进制 |

Java 侧事实（均一手来源）：

- **jpackage**：JDK 自带的打包工具，用于创建自包含（self-contained）、用户可直接安装运行的应用安装包（[Oracle jpackage 工具指南](https://docs.oracle.com/en/java/javase/21/jpackage/)）。适合 GUI 应用/安装器形态，不是单 exe。
- **jlink**：JDK 9+ 自带，用于组装裁剪后的自定义运行时镜像（[Oracle jdk.jlink 模块文档](https://docs.oracle.com/en/java/javase/21/docs/api/jdk.jlink/module-summary.html)）。是 jpackage 与"带运行时分发"的基础。
- **GraalVM Native Image**：将 Java 字节码 AOT 编译为原生可执行文件，内嵌应用类、标准库子集、语言运行时与静态链接的 JDK 原生代码（[GraalVM Native Image 参考手册](https://www.graalvm.org/latest/reference-manual/native-image/)）。官方口径的优势：毫秒级启动、只占 JVM 一小部分的资源、无需 warmup 立即达到峰值性能、可打成轻量容器镜像；官方 HelloWorld 示例实测启动 0.00s、峰值 RSS 7620 KB（[同上](https://www.graalvm.org/latest/reference-manual/native-image/)）。代价：**闭世界假设**——反射、动态代理、JNI、资源加载等动态特性无法被静态分析穷尽，必须额外提供 reachability metadata（JSON 配置）（[同上](https://www.graalvm.org/latest/reference-manual/native-image/)）；且产出物面向特定 OS/架构（[同上](https://www.graalvm.org/latest/reference-manual/native-image/)）。
- **JBang**：让"自包含的纯源码 Java 程序"直接编辑即运行，`//DEPS` 声明依赖自动拉取；Windows/Linux/macOS/Docker/GitHub Actions 通用；本机没有 Java 时自动下载 JDK（[JBang 官网](https://www.jbang.dev/)）。

**小结**：Java 的分发矩阵（JAR + 运行时 / jlink / jpackage / native image / JBang）比 Go 的 `go build` 与 Rust 的 `cargo build` 复杂一个数量级；Native Image 能追平"单 exe + 快启动 + 低内存"，但以构建时间、闭世界约束与每平台单独构建为代价。

### 3.2 CLI 生态

| 维度 | Go | Python（本仓） | Rust | Java |
|---|---|---|---|---|
| 主流框架 | cobra / stdlib flag | click/typer、argparse | clap | picocli（+ JBang 脚本化） |
| 运行时依赖 | 无 | Nuitka 打包后无 | 无 | 需 JVM 或 AOT 成 native |
| 仓库既有标准 | CLI 标准配套 MCP + `--json` + `schema` | v2 daemon 标准（zedhub 试点） | clap 直出 | 无（新起） |
| 典型启动速度 | 毫秒级 | Nuitka exe 快于解释执行 | 毫秒级 | JVM 模式百毫秒~秒级；native 毫秒级 |

Java 侧事实：

- **picocli**（当前 4.7.7）：单文件 CLI 框架，支持 POSIX/GNU/MS-DOS 等参数风格，强类型选项、ANSI 彩色帮助、TAB 补全、可生成 HTML/PDF/man 文档；官方明确支持 AOT 编译为 GraalVM Native Image，获得"极快启动 + 更低内存 + 单可执行文件分发"，且其注解处理器可自动生成 GraalVM 反射/资源/代理配置（[picocli 官方文档](https://picocli.info/)）。
- Java CLI 的真正劣势不在框架（picocli 功能面不输 cobra/clap），而在**默认运行时形态**：给最终用户的是一个需要 JVM 的 JAR，还是走 native image/build 管线。Go/Rust 天然零依赖单文件。

**小结**：本仓 CLI 工具的既有标准（MCP 配套、JSON 输出、build.py 统一构建、dev/release 隔离）全部围绕 Go 生态成型，Java 入场没有增量收益。

### 3.3 GUI 桌面

| 维度 | Go（本仓） | Python（本仓） | Rust（本仓） | Java |
|---|---|---|---|---|
| 现役方案 | Wails（2 个项目）+ Fyne（历史） | 无独立 GUI（脚本工具为主） | 无 | JavaFX |
| 分发形态 | 单 exe（捆绑 webview） | — | — | 需 jpackage/jlink 捆绑运行时 |
| 托盘/Windows 质感 | systray 成熟（glmquotawatch-gui 在用） | — | — | 需第三方库（如 FXTrayIcon 类，非官方） |

Java 侧事实：

- **JavaFX（OpenJFX）**：开源的下一代客户端应用平台，目标覆盖桌面、移动与嵌入式（[openjfx.io 官网](https://openjfx.io/)）；自 Java 11 起不再随 JDK 捆绑，以 Maven 模块或独立 SDK 形态由 Gluon 分发（[openjfx.io](https://openjfx.io/) 首页下载指向 [Gluon JavaFX 下载页](https://gluonhq.com/products/javafx/)）；可视化设计器 Scene Builder 亦由 Gluon 维护（[Gluon Scene Builder](https://gluonhq.com/products/scene-builder)）。
- 本仓 GUI 项目（Wails 托盘仪表盘、桌面终端壳）都是"Windows 桌面轻壳"形态，AGENTS.md 已要求专属矢量图标流水线；JavaFX 技术上完全能做，但分发体积与工具链（JDK + jpackage + Gluon SDK/jmods）对比 Wails 的单 exe 没有优势。

**小结**：GUI 不是 Java 的加分位。除非学习目标就是 JavaFX，否则不值得为此引入。

### 3.4 后端服务：Java 的真正强项

Java 侧事实：

- **Spring Boot 官方定位**："轻松创建可'直接运行'的独立生产级 Spring 应用"；内嵌 Tomcat/Jetty/Undertow（无需部署 WAR）、opinionated starter 依赖、自动配置、开箱的生产级特性（metrics、health checks、外部化配置）（[Spring 官方项目页](https://spring.io/projects/spring-boot)，当前 4.1.1）。
- **企业全家桶纵深**：Spring 官方参考手册一页式覆盖 Security（OAuth2/SAML）、Data（JPA/JDBC/Redis/Mongo/Neo4j…）、Messaging（Kafka/Pulsar/JMS/AMQP/RSocket）、Batch、gRPC、Quartz、Testcontainers、Actuator 可观测等（[Spring Boot 参考手册目录](https://docs.spring.io/spring-boot/reference/packaging/native-image/index.html)）；Spring for Apache Kafka 等中间件集成是官方一级项目（[spring.io/projects/spring-kafka](https://spring.io/projects/spring-kafka)）。
- **现代化补课**：Spring Boot 官方原生支持 GraalVM Native Image——"Native Image 通常比 JVM 版本内存占用更小、启动更快"（[Spring Boot 官方 GraalVM Native Images 章节](https://docs.spring.io/spring-boot/reference/packaging/native-image/index.html)）。

空位评估（对照本地盘点）：

| 空位候选 | 现状 | Java 能否补 |
|---|---|---|
| 企业级长驻 Web 后端（安全/事务/消息/批处理/可观测） | go 仅 2 个零依赖轻服务；python 4 个全是学习实验 | ✅ 这正是 Spring 的主场 |
| 中间件客户端生态（Kafka/Pulsar/ES 等第一方客户端） | 三语言均部分覆盖、客户端质量参差 | ✅ JVM 生态客户端最全（[Spring 集成矩阵](https://docs.spring.io/spring-boot/reference/packaging/native-image/index.html)） |
| 大数据计算（Flink/Spark 等 JVM 原生生态） | 完全空白 | ⭕ 能力上可补，但本仓无此类需求迹象 |

**小结**：这是 Java 唯一"三语言现有格局没有覆盖且 Java 明显最强"的维度；但价值兑现取决于是否真有长驻企业后端的学习/实战需求。

### 3.5 性能基线（启动 / 内存 / 峰值）

| 维度 | Go | Python | Rust | Java（JVM 模式） | Java（Native Image） |
|---|---|---|---|---|---|
| 冷启动 | 毫秒级 | 解释模式慢 / Nuitka 后改善 | 毫秒级 | 显著慢于 native（需 JVM 初始化 + JIT warmup） | 毫秒级（官方口径） |
| 内存基线 | 低 | 中（Nuitka 后仍带运行时） | 极低 | 显著高于 native（官方口径"fraction of the resources"的反面） | 官方 HelloWorld 实测峰值 RSS 7620 KB |
| 峰值吞吐 | 高 | 低 | 极高 | JIT 预热后极高（长驻服务优势） | 无 warmup 立即峰值（官方口径），峰值吞吐通常低于 JIT 模式 |

事实依据（避免引用未验证的具体数字）：

- GraalVM 官方：Native Image "毫秒级启动""只使用 JVM 所需资源的一小部分""立即交付峰值性能、无 warmup"（[GraalVM Native Image 参考手册](https://www.graalvm.org/latest/reference-manual/native-image/)）。
- GraalVM 官方文档示例输出：native 化 HelloWorld 启动 0.00s、Max RSS 7620 KB（[同上](https://www.graalvm.org/latest/reference-manual/native-image/)）。
- Spring Boot 官方：Native Image "通常比 JVM 对应版本内存占用更小、启动更快"（[Spring Boot GraalVM Native Images](https://docs.spring.io/spring-boot/reference/packaging/native-image/index.html)）——侧面印证 JVM 模式基线更高。
- 推论（非引用数字）：**短命进程（CLI、计划任务）JVM 启动/内存税占比高；长驻进程恰好是 JIT 的主场**。这解释了"本仓 CLI 形态不适合 Java、服务形态适合"的性能根源。

### 3.6 工具链与 Windows 构建体验

| 维度 | Go | Python | Rust | Java |
|---|---|---|---|---|
| 运行时/SDK 获取 | 官方单一安装包 | uv 管理解释器 | rustup（已配 rsproxy 镜像） | 需先做"发行版选择"（Temurin/Oracle/OpenJDK…） |
| 构建工具 | go build + build.py | uv（PEP 723 单文件） | cargo | Maven 或 Gradle（二选一）+ 可选 GraalVM |
| 克隆即构建 | 是 | 是（uv sync） | 是 | Gradle Wrapper（gradlew.bat）可免装 Gradle；Maven 亦有 wrapper |
| AOT/native 链 | 不需要 | Nuitka | 内置 | 需 MSVC 14.x（VS Build Tools 2022） |

Java 侧事实：

- **JDK 发行版**：Eclipse Temurin（Adoptium）提供免费、无使用限制、Java SE TCK 认证且 AQAvit 验证的 OpenJDK 二进制（[adoptium.net](https://adoptium.net/)，Temurin 27 已于 2026-10 发布）；Oracle 官方下载页提供 Oracle JDK（[oracle.com/java/technologies/downloads](https://www.oracle.com/java/technologies/downloads/)）；OpenJDK 官方社区版见 [openjdk.org](https://openjdk.org/)。本仓语境推荐 Temurin LTS（免费无限制，官方定位即"企业级就绪"）。
- **Maven**：当前 3.10.0，前置要求 JDK 8+ 并设置 `JAVA_HOME`；Windows 官方支持 Chocolatey/Scoop 安装（[Maven 官方安装文档](https://maven.apache.org/install.html)）。
- **Gradle**：当前 9.8.1，前置要求 JDK 17+；项目内的 Gradle Wrapper（`gradlew.bat`）让协作者无需安装 Gradle；Windows 支持 winget/choco/scoop；`gradle init` 可从零引导项目（[Gradle 官方安装文档](https://docs.gradle.org/current/userguide/installation.html)）。
- **Native Image on Windows**：需要 MSVC 14.x 及以上（官方推荐 `winget install Microsoft.VisualStudio.2022.BuildTools`），自动探测 VS 安装（[GraalVM 官方文档 Windows 一节](https://www.graalvm.org/latest/reference-manual/native-image/)）。**本仓已为 Rust 配置 VS Build Tools 2022，此依赖已就绪**（父仓 AGENTS.md 工具链记录）。

**小结**：Java 工具链的决策面（发行版 × 构建工具 × 可选 AOT）明显大于三语言现有任何一家；但 Windows 体验本身没有硬伤（包管理器 + wrapper 机制 + MSVC 复用）。

---

## 四、引入建议

### 4.1 值得用 Java 起新坑的类型

1. **`spring-lab` 类学习/实战 Web 后端**（优先级最高）：对标 `django-lab` / `tech_learning_room` 的"学主流框架"路线，收获 Spring Boot + Security + Data + Actuator 的企业生态认知（[Spring 官方项目页](https://spring.io/projects/spring-boot)）。这是三语言格局的真实空位。
2. **长驻型自用后端服务**（若出现真实需求）：如需要完整的安全、事务、消息、批处理、可观测能力的常驻服务，Spring 全家桶的开箱完整度高于 Go 零依赖自拼与 Python 学习级实现（[Spring Boot 参考手册](https://docs.spring.io/spring-boot/reference/packaging/native-image/index.html)）。
3. **JVM 中间件对接工具/服务**：需要 Kafka/Pulsar 等企业中间件第一方客户端时（[Spring for Apache Kafka](https://spring.io/projects/spring-kafka)）。
4. **JBang 单文件脚本**：学 Java 新特性的 scratch 实验，源码即程序、依赖内嵌、无 JDK 自动下载（[JBang 官网](https://www.jbang.dev/)），可放 `standalone_scripts` 式形态。

### 4.2 明确不该用 Java 的类型

1. **Windows 单 exe CLI/TUI**：Go 位置最优（单二进制、`build.py` dev/release 体系、CLI 标准 MCP+JSON+schema 全部就位）；Java native image 路线成本高且与闭世界约束冲突风险大（[GraalVM metadata 约束](https://www.graalvm.org/latest/reference-manual/native-image/)）。
2. **托盘/GUI 桌面壳**：Wails/Fyne 已覆盖；JavaFX 分发需捆绑运行时、生态由社区（Gluon）维系（[openjfx.io](https://openjfx.io/)）。
3. **Windows 系统底层 CLI**（句柄/NTFS/驱动级）：Rust 手写 FFI + 无 GC 的形态已被 `minieverything`、`whoholds` 验证。
4. **高频小工具与自动化脚本**：uv 单脚本（PEP 723）轻量得多；JBang 只在"目的就是练 Java"时才合理。

### 4.3 若引入，需配套的子仓约定（建议清单）

- JDK 发行版固定为 **Temurin LTS**（免费无使用限制，[adoptium.net](https://adoptium.net/)），用文件记录大版本（如 21/25 LTS）。
- 构建工具二选一固定（建议 **Gradle + Wrapper**：JDK 17+ 前置、克隆即构建，[Gradle 官方](https://docs.gradle.org/current/userguide/installation.html)；或 Maven，[Maven 官方](https://maven.apache.org/install.html)）。
- 数据目录沿用 `%APPDATA%\language_projects\<项目名>\` 强约束；产 exe 的图标规范需另立（Java 侧无既有流水线）。
- Native Image 不作为默认形态，仅作进阶实验（MSVC 2022 已就绪，[GraalVM Windows 前置](https://www.graalvm.org/latest/reference-manual/native-image/)）。

---

## 五、一手来源清单（去重）

| 来源 | URL |
|---|---|
| GraalVM Native Image 参考手册（AOT、启动/内存口径、Windows MSVC 前置、metadata 约束） | https://www.graalvm.org/latest/reference-manual/native-image/ |
| Oracle jpackage 工具指南（JDK 21） | https://docs.oracle.com/en/java/javase/21/jpackage/ |
| Oracle jdk.jlink 模块文档（JDK 21） | https://docs.oracle.com/en/java/javase/21/docs/api/jdk.jlink/module-summary.html |
| JBang 官网（源码即程序、//DEPS、自动下载 JDK） | https://www.jbang.dev/ |
| picocli 官方文档（4.7.7，native image 支持、注解处理器） | https://picocli.info/ |
| JavaFX / OpenJFX 官网（desktop/mobile/embedded、Gluon 分发） | https://openjfx.io/ |
| Gluon JavaFX 下载（SDK/jmods/Maven Central） | https://gluonhq.com/products/javafx/ |
| Gluon Scene Builder | https://gluonhq.com/products/scene-builder |
| Spring Boot 官方项目页（定位、内嵌容器、starter、4.1.1） | https://spring.io/projects/spring-boot |
| Spring Boot 参考手册·GraalVM Native Images 章节（官方 AOT 支持、内存/启动对比） | https://docs.spring.io/spring-boot/reference/packaging/native-image/index.html |
| Spring for Apache Kafka（中间件集成官方项目） | https://spring.io/projects/spring-kafka |
| Apache Maven 官方安装文档（JDK 前置、Windows 安装） | https://maven.apache.org/install.html |
| Gradle 官方安装文档（JDK 17+、Wrapper、Windows 安装、gradle init） | https://docs.gradle.org/current/userguide/installation.html |
| Eclipse Adoptium / Temurin（免费 OpenJDK 二进制，TCK/AQAvit） | https://adoptium.net/ |
| OpenJDK 官网 | https://openjdk.org/ |
| Oracle JDK 官方下载页 | https://www.oracle.com/java/technologies/downloads/ |

仓库内部事实（项目分类、工具链配置、AGENTS.md 约定）来源：本地仓库盘点（`go_projects/`、`python_projects/`、`rust_projects/` 各项目 README 与包元数据；父仓与子仓 `AGENTS.md`），盘点日期 2026-10-14。
