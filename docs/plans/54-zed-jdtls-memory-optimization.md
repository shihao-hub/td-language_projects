Plan for: "优化 Zed 中 Java LSP (JDTLS) 内存占用配置"

**问题陈述**：Zed 启动 Java LSP 时默认分配 `-Xms1G`，导致 JDTLS 启动即直接吃掉近 1GB 内存，给系统带来明显内存压力。
**需求**：用户针对学习项目场景，确认采用 512M 极简档：在 `.zed/settings.json` 中配置 JDTLS 的 `min_memory: "128m"` 和 `max_memory: "512m"`，将启动初始堆大幅降低至 128MB，并将内存峰值严格封顶在 512MB。
**背景**：
1. Zed 官方 Java 扩展（`zed-extensions/java`）内部启动 `jdtls` 时，默认使用 `min_memory: "1G"`（映射为 `-Xms1G`），JVM 启动时即向 OS 提交 1GB 堆内存。
2. 实测当前运行中的 `jdtls` 进程（PID 51944）的工作集直接为 `1020,817,408` 字节（~973.5 MB）。
3. 学习项目依赖与类较少，JDTLS 稳定运行仅需 200MB~350MB，封顶 512MB 既能保证性能又节省内存。
**方案**：在 `.zed/settings.json` 的 `lsp.jdtls.settings` 节点下增加 `"min_memory": "128m"` 和 `"max_memory": "512m"`，保存后生效。

**任务分解**：
- [x] Task 1: 更新 .zed/settings.json 中的 jdtls 内存参数
  - 文件：`.zed/settings.json`
  - 实现：在 `lsp.jdtls.settings` 中添加 `"min_memory": "128m"` 与 `"max_memory": "512m"`，保留现有的注释及其他配置
  - 验证：读取 `.zed/settings.json` 确认 JSON 格式合法且字段已正确落盘
  - Demo：在 Zed 中重启 Java 语言服务器或打开 Java 文件时，JVM 启动内存降至 128MB，峰值封顶在 512MB

---
**最后更新：** 2026-10-10
**作者：** AI & User
**版本：** v2

