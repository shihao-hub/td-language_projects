# 计划：构建脚本文档示例统一为默认无参形式

## Context

26 号迁移计划已把全仓构建脚本统一为 Python（uv run）。用户确认约定：**默认构建就是 `uv run build.py`（或 `uv run scripts/build.py`），不需要传参数**——所有脚本的参数都有默认值（`--version` 默认 dev、`--release`/`--clean`/`--skip-frontend` 等开关默认关闭），脚本本身已满足该语义，**无需改任何代码**。

但排查发现 4 处文档示例只写了带参形式（`--version 1.0.0`），与其余项目（agyquota、liteconf、quickask、pythonlauncher、sublimefolders、glmquotawatch-gui 均为无参默认形式）不一致，容易误导为"必须传版本号"。本计划把这 4 处示例改为默认无参形式，带参用法作为注释保留。

## 改动清单（4 处，均为文档单行替换）

1. `go_projects/clictl/README.md:89`
   - 改为：`uv run scripts/build.py  # 产出单文件 clictl.exe；--version 1.0.0 可指定版本（默认 dev）`
2. `go_projects/sourcecount/README.md:61`
   - 改为：`uv run scripts/build.py  # --version 1.0.0 可指定版本（默认 dev）`
3. `docs/projects/go_projects/clictl/clictl 使用指南.md:16`（父仓镜像）
   - 同 1 的写法
4. `docs/projects/go_projects/sourcecount/使用指南.md:13`（父仓镜像）
   - 同 2 的写法

脚本代码、其余文档、README 中的 `--release`/`--clean` 等可选参数说明均保持现状（它们本就以"默认无参在前、可选项在后"的形式呈现）。

## 提交与推送

按范围隔离规则分两笔，每笔提交后立即 push：

1. go_projects 子仓（clictl 与 sourcecount 两项目改动，属两个子项目，分两笔）：
   - `clictl:docs: 构建示例统一为默认无参形式`
   - `sourcecount:docs: 构建示例统一为默认无参形式`
2. 父仓镜像文档一笔：
   - `docs: 构建示例统一为默认无参形式`
3. 父仓指针：`git add --force go_projects` → `chore(submodule): 更新 go_projects 子模块指针` → push

## 验证

- grep 四个文件确认 `--version 1.0.0` 不再作为唯一示例出现（仅存于注释中的可选说明）
- 各仓 `git status` 干净、推送成功、父仓指针与子仓 HEAD 一致
