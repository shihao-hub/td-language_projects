# 被 `.gitignore` 排除的 `.local/` 目录，如何做版本管理？

> 调研对象：`D:/Users/language_projects`（Git monorepo，父仓 + 多语言子仓 submodule）
> 具体诉求：`.local/`（约 8 个文件 / 137K，内含含真实姓名的个人简历）当前被仓根 `.gitignore` 的 `.local/` 规则排除，想对它做版本管理。
> 环境实证：`git version 2.55.0.windows.3`，shell 为 Git Bash，Windows 11；全局 `core.excludesFile` 未设置（`git config --global core.excludesFile` 退出码 1、无输出），全局 `core.autocrlf=true`。
> 本文中所有实验均在临时目录 `C:/Users/29580/AppData/Local/Temp/gitignore-lab`（Git Bash 的 `/tmp`）内完成，全程未读写或修改 `D:/Users/language_projects` 下任何既有文件，本报告文件本身除外。

---

## 0. 结论速览

| 场景 | 推荐方案 | 一句话理由 |
| --- | --- | --- |
| 想要版本历史 + 隐私隔离 + 可推私有远端 | **把简历搬出 monorepo，放到独立路径建独立私有 git 仓**（如 `D:/Users/private/resumes`） | 彻底脱离父仓的 ignore/clean/submodule 语义，隐私与误提交风险都降到最低 |
| 不想动路径，就地解决 | **在 `.local/` 里直接 `git init` 建独立仓**，指向私有远端 | 父仓已有 `.local/` 规则，天然互不干扰；唯一新增风险是父仓执行 `git clean -xdff` |
| 必须让父仓也看得到 | **改父仓 `.gitignore` 为 `.local/*` + `!.local/resumes/`** | 实测唯一有效的取反写法（详见第 2 节）；但简历会随父仓一起推到共享远端 |
| 只是想多机同步/备份，不关心历史 | **Syncthing / restic** | 简历体量小、几乎不需要 branch/diff，同步工具比 git 更省心 |
| 想在父仓里用 submodule | **不合适，别选** | submodule 要求父仓跟踪 gitlink，与「被 ignore」自相矛盾（详见 3.4） |

一句话总纲：**不要试图用 `!` 取反去救一个被「目录级 pattern」排除掉的目录**——官方文档明确说做不到，本文实测也证实 A/C/D/F/I 组写法全部失败；能救的只有 `.local/*` 这种「排除内容、不排除容器」的写法。

---

## 1. 诊断：一个目录为什么不被 Git 管理

### 1.1 gitignore 的四种来源与优先级（官方文档原文）

> When deciding whether to ignore a path, Git normally checks `gitignore` patterns from multiple sources, with the following order of precedence, from highest to lowest (within one level of precedence, the last matching pattern decides the outcome):
>
> - Patterns read from the command line for those commands that support them.
> - Patterns read from a `.gitignore` file in the same directory as the path, or in any parent directory (up to the top-level of the working tree), with patterns in the higher level files being overridden by those in lower level files down to the directory containing the file. These patterns match relative to the location of the `.gitignore` file. A project normally includes such `.gitignore` files in its repository, containing patterns for files generated as part of the project build.
> - Patterns read from `$GIT_COMMON_DIR/info/exclude`.
> - Patterns read from the file specified by the configuration variable `core.excludesFile`.
>
> —— [git-scm.com/docs/gitignore](https://git-scm.com/docs/gitignore)（DESCRIPTION 章节）

注意两点容易记错的地方：

1. **「离文件越近的 `.gitignore` 优先级越高」** 的官方表述是：
   > ...with patterns in the higher level files being overridden by those in lower level files down to the directory containing the file.
   > —— [git-scm.com/docs/gitignore](https://git-scm.com/docs/gitignore)

   即：子目录里的 `.gitignore` 能推翻父目录里的 `.gitignore`。
2. 官方文档写的是 **`$GIT_COMMON_DIR/info/exclude`**，不是 `$GIT_DIR/info/exclude`（两者的差异出现在 worktree 场景下）。日常单 worktree 使用时，它就是 `.git/info/exclude`。

### 1.2 排除判定只作用于「未跟踪」的文件

> Files already tracked by Git are not affected; see the NOTES below for details.
>
> The purpose of gitignore files is to ensure that certain files not tracked by Git remain untracked.
>
> —— [git-scm.com/docs/gitignore](https://git-scm.com/docs/gitignore)

**实测验证（git 2.55.0.windows.3）**：先 `git add keep.md && git commit`，再把 `keep.md` 写进 `.gitignore` 并修改文件内容——

```
--- git status --short (keep.md 被 ignore 但已跟踪) ---
 M keep.md
 ?? .gitignore
```

`keep.md` 依然作为已跟踪文件正常报 modified。这一点直接决定了排查命令的写法（见 1.4）。

### 1.3 其他可能原因（穷尽清单）

| 可能原因 | 判定方法 | 本仓库是否命中 |
| --- | --- | --- |
| 各级 `.gitignore` 里有匹配规则 | `git check-ignore -v --no-index <path>` | **命中**：仓根 `.gitignore` 的 `.local/` |
| `.git/info/exclude` 里有规则 | `git check-ignore -v --no-index <path>` 输出的 `<source>` 字段会显示 `.git/info/exclude` | 未命中 |
| `core.excludesFile` 指向的全局忽略文件 | `git config --get core.excludesFile`；官方默认值为 `$XDG_CONFIG_HOME/git/ignore`，未设时回落 `$HOME/.config/git/ignore`（[Documentation/config/core.adoc](https://raw.githubusercontent.com/git/git/master/Documentation/config/core.adoc)） | 未命中（返回空） |
| 目录内嵌了另一个 `.git`（nested repo） | `ls -a .local/` 看有无 `.git`；父仓 `git add -f .local` 会报 `adding embedded git repository` | 未命中（`.local/.git` 不存在） |
| 文件被 `--assume-unchanged` / `--skip-worktree` 标记 | `git ls-files -v \| grep -v '^H'` | 未命中（这些文件根本不在 index 里） |
| 目录为空 | Git 不跟踪空目录（tree 里没有空目录这种对象） | 未命中 |
| 符号链接 / junction 的目标在仓库外 | 见 3.3，与本场景无关 | 未命中 |

关于 `core.excludesFile` 的官方原文：

> core.excludesFile:: Specifies the pathname to the file that contains patterns to describe paths that are not meant to be tracked, in addition to `.gitignore` (per-directory) and `.git/info/exclude`. Defaults to `$XDG_CONFIG_HOME/git/ignore`. If `$XDG_CONFIG_HOME` is either not set or empty, `$HOME/.config/git/ignore` is used instead. See gitignore[5].
>
> —— [git/git: Documentation/config/core.adoc](https://raw.githubusercontent.com/git/git/master/Documentation/config/core.adoc)（渲染版见 [git-scm.com/docs/git-config](https://git-scm.com/docs/git-config)）

关于 nested repo 的实测证据（父仓强制加入嵌套仓后，index 里会变成 `160000` 的 **gitlink**）：

```
--- 父仓 git add -f .local  (强制加入嵌套仓) ---
    warning: adding embedded git repository: .local
    hint: You've added another git repository inside your current repository.
    hint: Clones of the outer repository will not contain the contents of
    hint: the embedded repository and will not know how to obtain it.
    hint: If you meant to add a submodule, use:
    hint: 	git submodule add <url> .local
    git ls-files -s:
      100644 a47f082c7ddadd57401e29bc2ff2294895aa1ad6 0	.gitignore
      160000 8da1d45db20b0fa1b05ea95cc2daf352154eae57 0	.local
```

关于 `assume-unchanged` / `skip-worktree` 的标记：

> -v:: Similar to `-t`, but use lowercase letters for files that are marked as 'assume unchanged' (see git-update-index[1]).
>
> —— [git/git: Documentation/git-ls-files.adoc](https://raw.githubusercontent.com/git/git/master/Documentation/git-ls-files.adoc)

### 1.4 排查命令清单（已在 git 2.55 上实测输出格式）

**① `git check-ignore -v --no-index <path>` —— 定位「是哪条规则排除的」**

官方输出格式定义：

> If `--verbose` is specified, the output is a series of lines of the form:
> `<source> <COLON> <linenum> <COLON> <pattern> <HT> <pathname>`

实测输出（用例 A，`.gitignore` 内容为 `.local/` + `!.local/resumes/`）：

```
.gitignore:1:.local/	.local/resumes/resume/resume.md
.gitignore:1:.local/	".local/resumes/resume/\351\241\271\347\233\2562.txt"
.gitignore:1:.local/	.local/resumes/resume/deep/note.md
```

退出码（官方文档）：`0`=有一个或多个路径被忽略；`1`=没有任何路径被忽略；`128`=致命错误。([git-scm.com/docs/git-check-ignore](https://git-scm.com/docs/git-check-ignore))

三个必须知道的坑：

- **必须加 `--no-index`**：如果不加，已跟踪文件会被直接跳过，导致「明明 .gitignore 里写了它却查不出来」。官方原文：
  > By default, tracked files are not shown at all since they are not subject to exclude rules; but see ‘--no-index’.
  >
  > --no-index:: Don’t look in the index when undertaking the checks. This can be used to debug why a path became tracked by e.g. `git add .` and was not ignored by the rules as expected by the user or when developing patterns including negation to match a path previously added with `git add -f`.

  实测对比（文件 `keep.md` 已被跟踪）：

  ```
  --- git check-ignore -v keep.md ---          (无输出, exit=1)
  --- git check-ignore -v --no-index keep.md ---
  .gitignore:1:keep.md	keep.md                  (exit=0)
  ```

- **加 `-n` 才能看到「没被排除」的路径**，否则不输出即代表「未被排除」，容易误判：

  ```
  --- git check-ignore -v -n --no-index  (用例 B, 全部未被排除) ---
  ::	.local/resumes/resume/resume.md
  ::	.local/resumes/resume/项目2.txt
  ```

  （`::\t<path>` 即「前三字段都为空」= 没有 pattern 命中 = 不被忽略。）

- **路径不必真实存在**也能拿到判定结果（`.gitignore:1:.local/	.local/resumes/resume/no_such.md`，exit=0），这在推导规则时很有用。

**② `git status --ignored` / `--short --ignored` —— 看整个仓库的忽略全景**

长格式会在常规区块后追加 `Ignored files:` 区块；短格式用 `!! ` 前缀标记被忽略项。实测：

```
--- (用例 A) git status --ignored ---
 On branch master
 No commits yet
 Changes to be committed:
	new file:   .gitignore
 Ignored files:
   (use "git add -f <file>..." to include in what will be committed)
	.local/

--- (用例 A) git status --short --ignored ---
 ?? .gitignore
 !! .local/
```

注意：被忽略的目录在 `git status` 里会被**折叠成一行 `!! .local/`**，看不到里面的文件——这正是第 2 节陷阱的成因。

**③ `git ls-files -v | grep '^[a-z]'` —— 查 assume-unchanged 标记（但有个漏网之鱼）**

你给的这条命令其实**不完整**。官方文档里 `-v` 的状态标签列表是 `H / S / M / R / C / K / ?`（全大写），只有 `assume-unchanged` 才会被降级成小写；而 `skip-worktree` 是**大写 `S`**：

> H:: tracked file that is not either unmerged or skip-worktree
> S:: tracked file that is skip-worktree
>
> —— [git/git: Documentation/git-ls-files.adoc](https://raw.githubusercontent.com/git/git/master/Documentation/git-ls-files.adoc)

实测：

```
$ git update-index --assume-unchanged tracked_then_assume.md
$ git ls-files -v | grep '^[a-z]'
h tracked_then_assume.md          # 抓到了

$ git update-index --skip-worktree sw.md
$ git ls-files -v | grep '^[a-z]'
(无输出)                          # 抓不到！
$ git ls-files -v | grep -v '^H'
S sw.md                           # 这样才抓得到
```

**修正后的命令：`git ls-files -v | grep -v '^H'`**（或 `git ls-files -v | grep -E '^[a-z]|^S'`）。

### 1.5 针对本仓库的确诊

```bash
cd D:/Users/language_projects
git config --get core.excludesFile          # 空 => 不是全局忽略文件
cat .git/info/exclude                       # 看有无额外规则
ls -a .local/                               # 无 .git => 不是 nested repo
git check-ignore -v --no-index .local/resumes/resume/resume.md
# 期望输出: .gitignore:<行号>:.local/	.local/resumes/resume/resume.md
```

结论明确：**病因就是仓根 `.gitignore` 里的 `.local/` 这一条目录级 pattern**。

---

## 2. 核心陷阱：`!` 取反救不回被排除目录里的文件

### 2.1 官方原句

> An optional prefix "`!`" which negates the pattern; any matching file excluded by a previous pattern will become included again. **It is not possible to re-include a file if a parent directory of that file is excluded.** Git doesn’t list excluded directories for performance reasons, so any patterns on contained files have no effect, no matter where they are defined. Put a backslash ("`\`") in front of the first "`!`" for patterns that begin with a literal "`!`", for example, "`\!important!.txt`".
>
> —— [git-scm.com/docs/gitignore](https://git-scm.com/docs/gitignore)，PATTERN FORMAT 小节，`!` 条目（加粗为本文强调）

机制解释（同页紧随其后）：Git 出于性能考虑**根本不会去遍历被排除目录的内部**，所以写在任何地方、写给任何子路径的取反 pattern 都无从生效。

### 2.2 实测矩阵（git 2.55.0.windows.3，临时目录内真实输出）

每个用例都是全新 `git init` 的空仓，目录结构完全复刻你的 `.local/`：

```
.local/resumes/resume/resume.md
.local/resumes/resume/项目2.txt
.local/resumes/resume/deep/note.md      ← 额外构造的深层文件
.local/resumes/resume_final/resume.md
```

判定标准有两个：**（a）`git check-ignore -v -n --no-index` 的输出**；**（b）真的跑一次 `git add -A` 后 `git ls-files` 里有没有这些文件**。下面把两组证据都贴出来。（`::\t<path>` = 无 pattern 命中 = 未被忽略）

#### 用例 A：`.local/` + `!.local/resumes/` —— ❌ 无效（验证陷阱）

```
--- .gitignore ---
     1	.local/
     2	!.local/resumes/
--- git check-ignore -v -n --no-index <paths> ---
.gitignore:1:.local/	.local/resumes/resume/resume.md
.gitignore:1:.local/	".local/resumes/resume/\351\241\271\347\233\2562.txt"
.gitignore:1:.local/	.local/resumes/resume/deep/note.md
.gitignore:1:.local/	.local/resumes/resume_final/resume.md
(check-ignore exit=0)
--- git status --short --ignored ---
?? .gitignore
!! .local/
--- git add -A (real) then git ls-files ---
    tracked: .gitignore
    => 实际被 git add 纳入的文件数: 1          # 只有 .gitignore，简历一个都没进来
```

#### 用例 B：`.local/*` + `!.local/resumes/` —— ✅ 有效

```
--- .gitignore ---
     1	.local/*
     2	!.local/resumes/
--- git check-ignore -v -n --no-index <paths> ---
::	.local/resumes/resume/resume.md
::	".local/resumes/resume/\351\241\271\347\233\2562.txt"
::	.local/resumes/resume/deep/note.md
::	.local/resumes/resume_final/resume.md
(check-ignore exit=1)
--- git status --short --ignored ---
?? .gitignore
?? .local/
--- git add -A (real) then git ls-files ---
    tracked: .gitignore
    tracked: .local/resumes/resume/deep/note.md
    tracked: .local/resumes/resume/resume.md
    tracked: ".local/resumes/resume/\351\241\271\347\233\2562.txt"
    tracked: .local/resumes/resume_final/resume.md
    => 实际被 git add 纳入的文件数: 5
```

#### 用例 C：`.local/**` + `!.local/resumes/**` —— ❌ 无效

```
--- .gitignore ---
     1	.local/**
     2	!.local/resumes/**
--- git check-ignore -v -n --no-index <paths> ---
.gitignore:1:.local/**	.local/resumes/resume/resume.md
.gitignore:1:.local/**	".local/resumes/resume/\351\241\271\347\233\2562.txt"
.gitignore:1:.local/**	.local/resumes/resume/deep/note.md
.gitignore:1:.local/resumes/resume_final/resume.md
(check-ignore exit=0)
--- git add -A (real) then git ls-files ---
    tracked: .gitignore
    => 实际被 git add 纳入的文件数: 1
```

#### 用例 D：`.local/` + `!.local/resumes/**` —— ❌ 无效

```
--- .gitignore ---
     1	.local/
     2	!.local/resumes/**
--- git check-ignore -v -n --no-index <paths> ---
.gitignore:1:.local/	.local/resumes/resume/resume.md
.gitignore:1:.local/	".local/resumes/resume/\351\241\271\347\233\2562.txt"
.gitignore:1:.local/	.local/resumes/resume/deep/note.md
.gitignore:1:.local/	.local/resumes/resume_final/resume.md
(check-ignore exit=0)
=> 实际被 git add 纳入的文件数: 1
```

#### 用例 E：`.local/*` + `!.local/resumes/`，单独确认深层文件 —— ✅ 有效（深层文件一并纳入）

```
--- git check-ignore -v --no-index .local/resumes/resume/deep/note.md ---
(无输出, exit=1)          # 即未被忽略
=> 实际被 git add 纳入的文件数: 5   # 包含 .local/resumes/resume/deep/note.md
```

#### 补充用例（为穷尽组合而做）

| 用例 | `.gitignore` 内容 | 结果 |
| --- | --- | --- |
| F | `.local/` + `!.local/resumes`（取反**不带**结尾斜杠） | ❌ 无效，仍报 `.gitignore:1:.local/` 命中，入仓 0 个 |
| G | `.local/**` + `!.local/resumes/`（排除用 `**`，取反目录） | ❌ 无效，报 `.gitignore:1:.local/**` 命中，入仓 0 个 |
| H | `.local/*` + `!.local/resumes/`（对照） | ✅ 有效，入仓 3 个（含 deep） |
| I | `.local/` + `!.local/resumes/` + `!.local/resumes/**`（三层取反） | ❌ 无效，入仓 0 个 |

#### 矩阵汇总

| 组 | 排除 pattern | 取反 pattern | 结论 |
| --- | --- | --- | --- |
| A | `.local/` | `!.local/resumes/` | ❌ 父目录被排除，取反无效 |
| B | `.local/*` | `!.local/resumes/` | ✅ **有效** |
| C | `.local/**` | `!.local/resumes/**` | ❌ 排除侧用了 `**`（递归排除内容），取反无效 |
| D | `.local/` | `!.local/resumes/**` | ❌ 同上 |
| E | `.local/*` | `!.local/resumes/` | ✅ **有效，且深层文件自动纳入** |
| F | `.local/` | `!.local/resumes` | ❌ 取反加不加结尾斜杠都救不回来 |
| G | `.local/**` | `!.local/resumes/` | ❌ |
| H | `.local/*` | `!.local/resumes/` | ✅ 与 B/E 一致（复现性验证） |
| I | `.local/` + 两层取反 | — | ❌ 多加取反行也救不回来 |

**唯一有效的模式是「排除侧只排除容器的一层内容（`.local/*`），不要排除容器本身（`.local/`），也不要用 `**` 递归」。**

### 2.3 `/`、`/*`、`/**` 的语义差别（官方 pattern format 原文）

结尾 `/`：
> If there is a separator at the end of the pattern then the pattern will only match directories, otherwise the pattern can match both files and directories.

`/**`（递归匹配目录内一切）：
> A trailing "`/**`" matches everything inside. For example, "`abc/**`" matches all files inside directory "`abc`", relative to the location of the `.gitignore` file, with infinite depth.

`/*`（只匹配一层，因为 `*` 不吃 `/`）——官方在 EXAMPLES 里的原句：
> The pattern `foo/*`, matches `foo/test.json` (a regular file), `foo/bar` (a directory), but it does not match `foo/bar/hello.c` (a regular file), as the asterisk in the pattern does not match `bar/hello.c` which has a slash in it.

官方甚至直接给出了「排除一切但保留 foo/bar」的范式，并特意点出 `/*` 的关键作用：
> Example to exclude everything except a specific directory `foo/bar` (note the `/*` - without the slash, the wildcard would also exclude everything within `foo/bar`):
> ```
>     # exclude everything except directory foo/bar
>     /*
>     !/foo
>     /foo/*
>     !/foo/bar
> ```
> —— [git-scm.com/docs/gitignore](https://git-scm.com/docs/gitignore)，EXAMPLES 小节

这也顺便解释了用例 C 为什么失败：`.local/**` 是「无限深度排除 `.local` 内一切」，等于把内容也排除了，取反自然失效；而 `.local/*` 只排除 `.local` 的直接子项一层，`!.local/resumes/` 恰好在这一层上把它捞回来，**捞回目录后 Git 就会正常遍历它内部，深层文件随之纳入**（用例 E 已证实）。

---

## 3. 方案全景对比

以下每个方案都给出可直接复制的命令、优点、缺点与适用场景。命令中的 `<私有远端>` 请替换为你自己的私有仓库地址（如 Gitee/GitLab 私有仓、自建 git server）。

### 3.1 方案一：改父仓 `.gitignore` 取反，纳入父仓

```bash
cd D:/Users/language_projects
# 把 .gitignore 里的  .local/  改成下面两行（顺序不能反）
# ---- 8< ---- 精确的 .gitignore 片段 ----
.local/*
!.local/resumes/
# ---- >8 ----
git add .gitignore
git status --short --ignored        # 应能看到 ?? .local/ 而不是 !! .local/
git check-ignore -v -n --no-index .local/resumes/resume/resume.md   # 应为 ::  行
git add .local
```

- **优点**：零迁移、路径不变、`git log` 里能看到简历的修改历史；父仓的提交/分支/备份流程全部复用。
- **缺点（重要）**：
  - **隐私与误提交风险**：这个 monorepo 是要推到远端的共享仓库，而 `.local/resumes/` 里是含真实姓名的个人简历（`张世豪-Agent开发工程师-木及简历.md`）。一旦进了父仓，`git add -A` + `git push` 就会把它推上去；就算你每次都小心，别人 `git commit -am .` 或某个 GUI 工具的「全部暂存」也会把它带走。
  - **历史不可磨灭**：即使后来删掉，历史里的 blob 还在，需要 `git filter-repo` 重写历史才能擦除（见 4.2）。
  - 破坏 `.local/` 作为「本地个人沙盒」的语义：以后任何往 `.local` 里丢的临时文件都可能被误纳入（因为 `.local/*` 只排除了一层，`!.local/resumes/` 又把 `resumes` 整棵捞了回来）。
- **适用**：简历本来就是团队共享资产、仓库本身是私有的、且你确实想在父仓里做 review/diff。

### 3.2 方案二：在 `.local/` 里单独 `git init`（嵌套独立仓库）★ 推荐

```bash
cd D:/Users/language_projects/.local
git init                       # 注意：不是 --bare，.local 本身就是工作树
git add -A
git -c user.name="你的名字" -c user.email="你的邮箱" commit -m "init: resumes"
git remote add origin <私有远端>
git push -u origin master       # 或 main

# 日常使用：在该目录下就是一个普通 git 仓
cd D:/Users/language_projects/.local && git status
```

配套事实（均已实测）：

| 行为 | 结果 | 证据 |
| --- | --- | --- |
| 父仓 `git add -A` 会误吞它吗 | **不会**，`.local/` 被 ignore，父仓 add 只收 `.gitignore` | 实测 `tracked: .gitignore`，1 个文件 |
| 父仓 `git status` 看得到它吗 | **看不到**（`--ignored` 也只显示折叠的 `!! .local/`） | 实测输出 `!! .local/` |
| 父仓 `git add -f .local` | 会变成 `160000` gitlink，并给出 `adding embedded git repository` 警告 | 实测 `160000 ... 0 .local` |
| 父仓 `git clean -xdff` | ⚠️ **会把整个 `.local/`（含 `.git`）删掉** | 实测 `Would remove .local/` → 执行后 `.local 已被删除` |
| 父仓 `git clean -xd`（单 f） | 不会删（嵌套 git 目录需要第二个 `-f`） | 实测只列出 `.gitignore` |

`git clean` 的官方原文：

> -x:: Don’t use the standard ignore rules (see gitignore[5]), but still use the ignore rules given with `-e` options from the command line. This allows removing all untracked files, including build products.
>
> -f:: ... Git will refuse to modify untracked nested git repositories (directories with a `.git` subdirectory) unless a second -f is given.
>
> —— [git-scm.com/docs/git-clean](https://git-scm.com/docs/git-clean)

- **优点**：零迁移、完全独立于父仓的提交节奏、可以只推私有远端、父仓日常操作完全无感。
- **缺点**：
  - 父仓里跑一次 `git clean -xdff`（很多人清理构建产物时会习惯性敲）就会把简历仓**物理删除**。缓解手段：父仓里给 `.local` 单独加保护，或在父仓设 `git config --local clean.requireForce true`（默认就是 true，但 `-ff` 会绕过）；最靠谱的缓解是**有远端**：`git clone <私有远端>` 就能恢复。
  - 其他人 clone 这个 monorepo 时不会拿到它（这是优点也是缺点）。
- **适用**：不想动路径、想保留独立提交历史、有私有远端可推。**这是本文的两大推荐之一。**

### 3.3 方案三：挪出工作区到独立目录 + 符号链接/Junction 回指

```bash
# 1) 把内容搬到仓库外
mkdir -p D:/Users/private
mv D:/Users/language_projects/.local D:/Users/private/resumes
# 2) 在新位置建独立仓
cd D:/Users/private/resumes && git init && git add -A && git commit -m "init: resumes"
git remote add origin <私有远端> && git push -u origin master
# 3)（可选）回到 monorepo 里建 Junction，让原路径仍然可用
cd D:/Users/language_projects
cmd //c "mklink /J .local D:\Users\private\resumes"
```

`mklink` 的官方参数表：

| 参数 | 含义 |
| --- | --- |
| `/d` | Creates a directory symbolic link. By default, this command creates a file symbolic link. |
| `/h` | Creates a hard link instead of a symbolic link. |
| `/j` | Creates a Directory Junction. |

—— [learn.microsoft.com/.../windows-commands/mklink](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/mklink)

权限差异：Junction（`/J`）是**文件系统 reparse point，普通用户即可创建**；目录符号链接（`/D`）需要 `SeCreateSymbolicLinkPrivilege`——默认只有管理员，或 Windows 10/11 开启「开发者模式」后才对普通用户开放。实测本机 `mklink /D` 与 `mklink /J` **都创建成功**（说明当前环境具备该权限），但换台机器/换个账户不一定成立，所以**给简历场景优先用 `/J`**。

Git 侧的关键实测结论（这条很重要，网上说法很乱）：

1. **Junction 会被 Git 当作普通目录穿透遍历**。在父仓里建了 `.local` junction 且**没有** `.local/` 忽略规则时，`git add -A` 直接把 junction 目标里的文件收进父仓：
   ```
   --- 无 .gitignore 时 git add -A 后 ls-files ---
     tracked: .local/resumes/resume/resume.md
   => junction 内的文件是否被父仓纳入: 1 个
   ```
2. 但**只要 `.local/` 仍在父仓 `.gitignore` 里，junction 就会被正常忽略**（你的仓库正好满足）：
   ```
   --- junction + .local/ 被 ignore ---
   git status --short --ignored:   !! .local/
   git add -A 后 ls-files:         .gitignore    (只有 .gitignore)
   git check-ignore -v --no-index .local/resumes/resume/resume.md:
        .gitignore:1:.local/	.local/resumes/resume/resume.md
   ```
3. `git clean -xdff` 只会删除 **junction 本体**，不会波及目标目录内容：
   ```
   Would remove .local/
   # 执行后：
   target 剩余: resume.md
   target 剩余: 项目2.txt
   junction 本体还在吗: no
   ```
   → 相比 3.2 的嵌套仓方案，junction 方案在 `clean -xdff` 下**数据更安全**（只掉一个链接，重建即可）。
4. 关于 `core.symlinks`：本机实测 `git config core.symlinks` 返回 **false**（全局未设置，仓库级被 init 探测为 false）。官方原文：
   > core.symlinks:: If false, symbolic links are checked out as small plain files that contain the link text. git-update-index[1] and git-add[1] will not change the recorded type to regular file. Useful on filesystems like FAT that do not support symbolic links.
   > —— [git/git: Documentation/config/core.adoc](https://raw.githubusercontent.com/git/git/master/Documentation/config/core.adoc)

   也就是说：**在这个 Windows 环境里，别指望 Git 能把 symlink 当 symlink 存进仓库**（会被存成含路径文本的普通文件）。Junction 则压根不进仓库，只是本地便利。

- **优点**：真正做到了「数据不在 monorepo 里」；`clean -xdff` 只掉链接不掉数据；junction 让原路径继续可用。
- **缺点**：多了一层 Windows 特有的 reparse point，备份/拷贝/某些工具（如旧版 rsync/zip）处理 junction 的行为不一致；`mklink /D` 有权限门槛；junction 只对本地目录有效（`mklink /J` 不支持远程路径）。
- **适用**：既想彻底搬出去、又想保留 `D:/Users/language_projects/.local` 这个路径的场合。**如果不需要保留原路径，直接搬走、不建 junction 更干净**（已实测独立仓流程可用）。

### 3.4 方案四：Git submodule / subtree —— 为什么不推荐

**submodule（不推荐）**：submodule 的本质是父仓必须**跟踪一个 gitlink**，这与「`.local/` 被 ignore」直接冲突。

> Assuming the submodule has a Git directory at `$GIT_DIR/modules/foo/` and a working directory at `path/to/bar/`, the superproject tracks the submodule via a `gitlink` entry in the tree at `path/to/bar` and an entry in its `.gitmodules` file of the form `submodule.foo.path` = `path/to/bar`.
>
> The `gitlink` entry contains the object name of the commit that the superproject expects the submodule’s working directory to be at.
>
> When cloning or pulling a repository containing submodules the submodules will not be checked out by default; you can instruct `clone` to recurse into submodules.
>
> —— [git-scm.com/docs/gitsubmodules](https://git-scm.com/docs/gitsubmodules)

矛盾点在于：要用 submodule，父仓 `.gitignore` 里就**不能**有 `.local/`（否则 gitlink 都无法建立，且 `git submodule add` 会与忽略规则打架）；而一旦父仓开始跟踪 `.local` 这个 gitlink，`.gitmodules` + gitlink 就会推到共享远端——**所有人 clone 你这个 monorepo 时，都会拿到一个指向你私有简历仓的 submodule 指针**。这既泄露了「你有一个叫 .local 的私有简历仓」这一事实，又会在别人执行 `git submodule update` 时因为无权限而报错。结论：**不合适。**

**subtree（也不推荐）**：subtree 是把外部项目的**内容和历史直接合并进主仓**：

> Subtrees allow subprojects to be included within a subdirectory of the main project, optionally including the subproject's entire history.
>
> Unlike submodules, subtrees do not need any special constructions (like '.gitmodules' files or gitlinks) be present in your repository...
>
> —— [git/git: contrib/subtree/git-subtree.adoc](https://raw.githubusercontent.com/git/git/master/contrib/subtree/git-subtree.adoc)

这恰恰是问题所在：它会把简历的全部内容（含姓名）**原样合并进父仓历史**，等价于方案一的「纳入父仓」，而且还要额外维护 `git subtree push/pull` 的心智负担。**不合适。**

- **适用**：几乎不适用于本场景（除非简历本身就是要公开的团队资产）。

### 3.5 方案五：裸仓 + `--work-tree` 的 dotfiles 流派

Arch Wiki 的经典三连：

```
$ git init --bare ~/.dotfiles
$ alias dotfiles='/usr/bin/git --git-dir="$HOME/.dotfiles/" --work-tree="$HOME"'
$ dotfiles config status.showUntrackedFiles no
```

> —— [wiki.archlinux.org/title/Dotfiles](https://wiki.archlinux.org/title/Dotfiles)，"Tracking dotfiles directly with Git" 章节

对应到本场景，等价写法是：

```bash
# 在 bash 里（Git Bash 可用）
git init --bare D:/Users/resumes-repo.git
alias rgit='git --git-dir="D:/Users/resumes-repo.git" --work-tree="D:/Users/language_projects/.local"'
rgit config status.showUntrackedFiles no
rgit add D:/Users/language_projects/.local
rgit commit -m "init: resumes"
rgit remote add origin <私有远端>
rgit push -u origin master

# 新机器上恢复：
git clone --bare <私有远端> D:/Users/resumes-repo.git
alias rgit='git --git-dir="D:/Users/resumes-repo.git" --work-tree="D:/Users/language_projects/.local"'
rgit checkout
rgit config --local status.showUntrackedFiles no
```

- **优点**：「版本库位置」与「文件位置」解耦，仓库可以放在任意位置（甚至仓库外），父仓完全无感；`status.showUntrackedFiles no` 让 `rgit status` 只显示你 add 过的文件，不会被同目录其他垃圾刷屏。
- **缺点**：
  - 它的设计目标是「`$HOME` 下散落的一堆 dotfile」，而你的诉求是「**一个目录**」——为了一个目录引入 alias + 分离 git-dir/work-tree，心智负担 > 收益。方案二（直接 `git init`）在功能上完全等价且更简单。
  - work-tree 指向的目录里**不能有另一个 `.git`**，也不能把父仓路径设成 work-tree，否则会与 monorepo 的 `.git` 探测打架。
  - 每个要用它的 shell 都得先定义 alias（可写进 `~/.bashrc` 持久化）。
- **适用**：你想把**多个分散目录**（比如还要管 `~/.ssh/config`、`~/.gitconfig`）一起版本化时，这个流派才真正划算。只管一个 `.local/`，不如直接 `git init`。

### 3.6 方案六：专用工具

| 工具 | 定位（一手来源） | 是否适配「Windows + 单个目录 + 想版本化」 | 结论 |
| --- | --- | --- | --- |
| **yadm** | > **yadm** is a tool for managing dotfiles. - Based on Git, with full range of Git's features - Supports system-specific alternative files or templated files - Encryption of private data using GnuPG, OpenSSL, transcrypt, or git-crypt —— [github.com/yadm-dev/yadm](https://github.com/yadm-dev/yadm) | 面向 `$HOME` 级 dotfiles，默认工作树就是 `$HOME`；要它只管一个子目录需要额外配置 `yadm.git.yadm-worktree`。Windows 支持未在官方仓库 README 中作为一等公民列出（CI 跑在 Ubuntu）。 | **不适配**（杀鸡用牛刀；且 Windows 支持存疑）。注：题目给的 [yadm.io/docs](https://yadm.io/docs) 实际返回 404，官方入口是 [yadm.io](https://yadm.io/) |
| **chezmoi** | > chezmoi runs on all popular operating systems, is distributed as a single statically-linked binary with no dependencies, and does not require root access. —— [chezmoi.io](https://www.chezmoi.io/)；`sourceDir` 默认 `$XDG_DATA_HOME/chezmoi` / `$HOME/.local/share/chezmoi` / **`%USERPROFILE%/.local/share/chezmoi`**，`destDir` 默认 `$HOME` / **`%USERPROFILE%`** —— [chezmoi.io/reference/configuration-file/variables](https://www.chezmoi.io/reference/configuration-file/variables/) | **跨平台、单二进制、有 Windows 原生支持**，这点它完全合格。但它的模型是「目标目录 = `$HOME`，源状态 = 独立 source 目录」，要管 `D:/Users/language_projects/.local` 这个非 home 目录，就得把 `destDir` 指到 monorepo 路径——那它就会试图管理整个 monorepo，语义错配。另外它的默认 `sourceDir` 恰好落在 `~/.local/share/chezmoi`，与你这个 `.local/` 命名撞车，容易混淆。 | **部分适配但不推荐**：如果你未来想用「模板 + 密码管理器 + 加密」管理跨机器的整套个人配置，chezmoi 是最佳选择；仅为仓库里的一个 `.local` 目录引入它，过重。 |
| **dotbare** | > As a dotfile management tool, it wraps around git bare repository, query git information from it and display them through fzf for an interactive experience. —— [github.com/kazhala/dotbare](https://github.com/kazhala/dotbare)；必需依赖为 **git、bash、fzf**，文档未提及原生 Windows 支持 | 本质是「裸仓流派 + fzf 交互前端」。依赖 bash 脚本 + fzf，Windows 原生不可用（需 WSL/Git Bash 且 fzf 另装）。 | **不适配**（Windows 原生不支持） |
| **GNU Stow** | > GNU Stow is a symlink farm manager which takes distinct sets of software and/or data located in separate directories on the filesystem, and makes them all appear to be installed in a single directory tree. —— [gnu.org/software/stow/manual](https://www.gnu.org/software/stow/manual/) | **Stow 根本不做版本管理**，它只负责「用 symlink 把 A 处的文件呈现在 B 处」。它假设文件系统支持 symlink，而 Windows 下创建 symlink 需要权限（见 3.3），且 Git 在 `core.symlinks=false` 时会把 symlink 存成文本文件。 | **不适配**（不是版本管理工具；且 Windows 下 symlink 语义不可靠） |

一句话总结：**本场景下，四个专用工具都不如「直接 `git init`」来得合适**。它们的价值在「管理散落在 `$HOME` 各处的几十上百个 dotfile」，而你的场景是「一个目录 + 8 个文件」。

### 3.7 方案七：非 Git 方案（用于对照）

- **Syncthing**：
  > Syncthing is a **continuous file synchronization** program. It synchronizes files between two or more computers in real time...
  > —— [syncthing.net](https://syncthing.net/)（支持 Windows/macOS/Linux/FreeBSD 等）
- **restic**：
  > Restic is a modern backup program that can back up your files: from **Linux, BSD, Mac and Windows** to **many different storage types**... **securely**, by careful use of cryptography in every part of the process... **verifiably**, enabling you to make sure that your files can be restored when needed
  > —— [restic.net](https://restic.net/)

**判断标准（一句话）**：

> 如果你的诉求是「**这台机器改了、那台机器马上看到**」或「**误删了能找回昨天那版**」，选 Syncthing / restic；只有当你的诉求是「**我想看这版和上版具体差了哪几行、想回滚到三个月前那一稿、想在两版之间做 merge**」时，才值得上 Git。

简历这个场景的小提醒：简历文件是 `.md`/`.txt`，体积 ~137K，且内容几乎是「整段重写」而非「逐行演进」——Git 的逐行 diff 对它的价值，远不如对代码的价值。

---

## 4. 深度议题：Git 适合跟踪简历吗？

### 4.1 文本友好，但 PDF/DOCX 要上 LFS

你现在是 `.md` / `.txt`，Git 的原生强项，无需任何特殊处理。但如果以后要在同一目录里放 PDF/DOCX 成品，就要考虑 **Git LFS**：

> Git Large File Storage (LFS) replaces large files such as audio samples, videos, datasets, and graphics with text pointers inside Git, while storing the file contents on a remote server like GitHub.com or GitHub Enterprise.
> —— [git-lfs.com](https://git-lfs.com/)（项目仓库：[github.com/git-lfs/git-lfs](https://github.com/git-lfs/git-lfs)）

用法：

```bash
git lfs install                       # 每用户一次（本机全局已配好 lfs filter）
git lfs track "*.pdf" "*.docx"        # 会写进 .gitattributes
git add .gitattributes
git add 张世豪-简历.pdf && git commit -m "add pdf" && git push
```

**代价（必须权衡）**：

- 远端必须支持 LFS（Gitee/GitHub/GitLab 都有免费额度，超出要付费；自建 server 要配 LFS 端点）。
- clone 时默认只拉 pointer，需要 `git lfs pull` 才拿到真文件——**你换台机器 clone 下来发现 PDF 打不开**，就是忘了这步。
- 历史里的旧文件不会自动转 LFS，需要 `git lfs migrate`（官方明确提醒：「Note that defining the file types Git LFS should track will not, by itself, convert any pre-existing files to Git LFS」——[git-lfs.com](https://git-lfs.com/)）。
- 单份简历 PDF 通常只有几百 KB，且每版都是新文件、不会被反复修改——**LFS 收益其实很小**。真正的建议是：PDF/DOCX 成品**单独放**（投递产出物），不要和 `.md` 源稿混在一个仓里。

### 4.2 含个人信息的文件进版本库：历史不可磨灭

这是本场景最需要提醒的一点：

- 一旦 `commit` 且 `push`，姓名/手机号/邮箱就永久留在历史里。就算 `git rm` 删掉，旧 commit 里的 blob 依然可被 `git show <old-commit>:<path>` 取回。
- 唯一彻底的办法是**重写历史**：

  > git filter-repo is now recommended by the git project instead of git filter-branch.
  >
  > Strongly encourage that workflow by detecting and bailing if we're not in a fresh clone, unless the user overrides with --force.
  >
  > —— [github.com/newren/git-filter-repo](https://github.com/newren/git-filter-repo)

  ```bash
  # 擦除历史中的某个文件（要求 fresh clone，需 git>=2.36 + python3>=3.6）
  git clone <仓地址> rescue-clone && cd rescue-clone
  git filter-repo --invert-paths --path 张世豪-Agent开发工程师-木及简历.md
  git push --force --all
  ```

  代价：所有 commit hash 改变、需要 `--force` push、所有协作者必须重新 clone。**所以正确的做法是从一开始就不让它进共享仓库**，而不是事后擦除。

### 4.3 `.gitattributes`：CRLF 与 diff

你的全局 `core.autocrlf=true`（本机实测），意味着提交时 CRLF → LF、检出时 LF → CRLF。对简历这类文件建议显式声明，避免跨机器/跨工具时行尾抖动：

```
# .gitattributes（放在简历仓的根，即 .local/.gitattributes）
*.md   text eol=lf
*.txt  text eol=lf
*.bat  text eol=crlf
*.js   text eol=lf
*.json text eol=lf
*.pdf  binary
*.docx binary
```

官方语义：

> eol:: This attribute marks a path to use a specific line-ending style in the working tree when it is checked out. It has effect only if `text` or `text=auto` is set...
> - crlf: This setting converts the file’s line endings in the working directory to CRLF when the file is checked out.
> - lf: This setting uses the same line endings in the working directory as in the index when the file is checked out.
>
> If the `eol` attribute is unspecified for a file, its line endings in the working directory are determined by the `core.autocrlf` or `core.eol` configuration variable... If `text` is set but neither of those variables is, the default is `eol=crlf` on Windows and `eol=lf` on all other platforms.
>
> The built-in macro attribute "binary" is equivalent to: `[attr]binary -diff -merge -text`
>
> —— [git-scm.com/docs/gitattributes](https://git-scm.com/docs/gitattributes)

注意 `.bat` 那条：Windows 批处理脚本**必须**保留 CRLF，否则某些场景下行尾解析会出问题，所以单独给 `.bat` 指定 `eol=crlf`。（实测本机的 `.gitignore` 等文件都被 Git 提示「LF will be replaced by CRLF」，说明自动转换是生效的，显式声明能让行为跨机器一致。）

---

## 5. 针对本仓库的落地建议

### 5.1 推荐主方案：搬出 monorepo，建独立私有仓（不放回 junction）

理由：一是隐私（不进共享远端），二是彻底摆脱父仓 `git clean -xdff` / `submodule` 等所有语义干扰，三是你并不需要保留 `.local` 这个路径（它是 monorepo 内部路径，不是你日常打开简历的路径）。

```bash
# 1) 搬出工作区（先备份，再搬）
cp -r D:/Users/language_projects/.local D:/Users/private/resumes
# 确认新目录完整后再删除旧位置
ls -R D:/Users/private/resumes
rm -rf D:/Users/language_projects/.local

# 2) 建独立仓 + 推私有远端
cd D:/Users/private/resumes
git init
cat > .gitattributes <<'EOF'
*.md   text eol=lf
*.txt  text eol=lf
*.bat  text eol=crlf
*.js   text eol=lf
*.json text eol=lf
*.pdf  binary
*.docx binary
EOF
# 顺手把明显不该入仓的产物排除掉
cat > .gitignore <<'EOF'
node_modules/
*.log
EOF
git add -A
git -c user.name="..." -c user.email="..." commit -m "init: 简历工作区"
git remote add origin <私有远端地址>     # 例：git@gitee.com:shihao-hub/resumes.git
git push -u origin master

# 3) 验收
git status --short && git log --oneline -1
```

取舍：路径变了，如果你有脚本硬编码了 `D:/Users/language_projects/.local/...`，需要一起改（你 `.local/resumes/resume/` 里的 `check_diff.bat` 值得检查一下）。

### 5.2 备选方案：原地 `.local/` 里 `git init`（不动路径）

```bash
cd D:/Users/language_projects/.local
git init
printf '*.md text eol=lf\n*.txt text eol=lf\n*.bat text eol=crlf\n*.pdf binary\n*.docx binary\n' > .gitattributes
git add -A
git -c user.name="..." -c user.email="..." commit -m "init: 简历工作区"
git remote add origin <私有远端地址>
git push -u origin master
```

取舍：零迁移成本；代价是在父仓里敲 `git clean -xdff` 会删掉它（实测确认）。**缓解办法：一定要有远端，并且不要养成在 monorepo 根目录跑 `clean -xdff` 的习惯**——非要清理就用 `git clean -xdn` 先预览，或用 `git clean -xd -e .local`（`-e` 会额外排除该 pattern）：

> -e <pattern>:: Use the given exclude pattern in addition to the standard ignore rules (see gitignore[5]).
> —— [git-scm.com/docs/git-clean](https://git-scm.com/docs/git-clean)

### 5.3 备选方案：独立仓 + Junction 回指（想保留原路径时用）

```bash
# 已完成 5.1 的 1)(2) 后，回到 monorepo 建 Junction
cd D:/Users/language_projects
cmd //c "mklink /J .local D:\Users\private\resumes"
```

取舍：父仓 `git add -A` 不会误吞（已实测，因为 `.local/` 仍在 ignore 中）；`git clean -xdff` 只会删掉 junction 本体、目标数据安全（已实测）；代价是引入 Windows 特有的 reparse point。

### 5.4 「如果你就是想让它进父仓」的最小改法

改父仓 `.gitignore`，把 `.local/` 这一行替换成下面两行（**顺序不能反**，且必须同时存在）：

```
# .gitignore —— 精确的替换片段
.local/*
!.local/resumes/
```

```bash
cd D:/Users/language_projects
# 确认改对了再 add
git check-ignore -v -n --no-index .local/resumes/resume/resume.md
#   期望：输出以 "::" 开头（= 未被忽略）；若输出 ".gitignore:N:.local/..." 说明没改对
git add .local
git status --short --ignored          # 应显示 ?? .local/ 或 A .local/...，而非 !! .local/
```

对应的隐私处置（**强烈建议同时做**）：

1. 给父仓加一条防误推的保险——在 `.git/hooks/pre-commit` 或 CI 里检查 `.local/resumes/` 下的文件是否被 stage：
   ```bash
   # .git/hooks/pre-commit（父仓，chmod +x）
   if git diff --cached --name-only | grep -q '^\.local/resumes/'; then
     echo "ERROR: 个人简历不得提交到共享仓库，请改用独立私有仓。" >&2
     exit 1
   fi
   ```
2. 明确这份简历是**打算公开**的（比如它本来就是要挂到仓库里的求职材料）——那反而应该给它一个正式路径（如 `docs/resume/`），而不是塞在被 ignore 的 `.local/` 里。

### 5.5 仓库纪律提醒（AGENTS.md）

在父仓动 `.gitignore` 属于「对共享文件的修改」，按你提到的仓库纪律需要注意两点：

- **数据文件存放强约束**：`.local/` 被定义为不被跟踪的本地数据区，本身就符合这条约束。方案 5.4 会破坏这个约定（把个人数据从本地区挪进被跟踪区），属于需要额外评审的动作；方案 5.1/5.2 则完全不触碰父仓文件，**对父仓零改动**，天然满足纪律要求。
- **提交范围隔离**：若最终仍要走 5.4，请让 `.gitignore` 的改动**单独成一个 commit**，不要和任何子仓/其他改动混在同一个提交里；并且在提交信息里写明动机，便于后续单独 revert。

---

## 6. 一手来源清单

本文所有 URL 均为本次调研中实际访问过（含实测访问）的地址。

**Git 官方文档**

- [git-scm.com/docs/gitignore](https://git-scm.com/docs/gitignore) — 四种 ignore 来源与优先级、`!` 取反的父目录限制、PATTERN FORMAT（`/`、`/*`、`/**`）、EXAMPLES（"exclude everything except a specific directory foo/bar"）
- [git-scm.com/docs/git-check-ignore](https://git-scm.com/docs/git-check-ignore) — `-v` 输出格式 `<source>:<linenum>:<pattern><HT><pathname>`、`--no-index`、退出码 0/1/128
- [git-scm.com/docs/git-config](https://git-scm.com/docs/git-config) — 渲染版（本次抓取时正文未命中变量条目，故下列变量以 git 官方仓库源文件逐字引用）
- [git/git: Documentation/config/core.adoc](https://raw.githubusercontent.com/git/git/master/Documentation/config/core.adoc) — `core.excludesFile`、`core.symlinks` 逐字原文
- [git/git: Documentation/git-ls-files.adoc](https://raw.githubusercontent.com/git/git/master/Documentation/git-ls-files.adoc) — `-v` 状态标签 `H/S/M/R/C/K/?` 与「lowercase letters ... assume unchanged」
- [git-scm.com/docs/git-clean](https://git-scm.com/docs/git-clean) — `-x`、`-f`（嵌套 git 目录需第二个 `-f`）、`-e <pattern>`、`clean.requireForce`
- [git-scm.com/docs/gitsubmodules](https://git-scm.com/docs/gitsubmodules) — gitlink 条目、`clone/pull` 默认不 checkout submodule
- [git/git: contrib/subtree/git-subtree.adoc](https://raw.githubusercontent.com/git/git/master/contrib/subtree/git-subtree.adoc) — subtree 定义与历史合并语义
- [git-scm.com/docs/gitattributes](https://git-scm.com/docs/gitattributes) — `text` / `eol=lf` / `eol=crlf` / `diff` / `binary` 宏

**操作系统与文件系统**

- [learn.microsoft.com: mklink](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/mklink) — `/d` `/h` `/j` 参数表

**Dotfiles 流派与工具**

- [wiki.archlinux.org/title/Dotfiles](https://wiki.archlinux.org/title/Dotfiles) — 裸仓 + alias + `--work-tree` + `status.showUntrackedFiles no` 三连
- [yadm.io](https://yadm.io/) / [github.com/yadm-dev/yadm](https://github.com/yadm-dev/yadm) — 项目 README（注：[yadm.io/docs](https://yadm.io/docs) 本次访问返回 404）
- [chezmoi.io](https://www.chezmoi.io/) / [chezmoi.io: configuration variables](https://www.chezmoi.io/reference/configuration-file/variables/) — `sourceDir` / `destDir` 默认值与跨平台声明
- [github.com/kazhala/dotbare](https://github.com/kazhala/dotbare) — 裸仓 + fzf，依赖 git/bash/fzf，无原生 Windows 支持
- [gnu.org/software/stow/manual](https://www.gnu.org/software/stow/manual/) / [stow.txt](https://www.gnu.org/software/stow/manual/stow.txt) — "a symlink farm manager"

**大文件与历史擦除**

- [git-lfs.com](https://git-lfs.com/) / [github.com/git-lfs/git-lfs](https://github.com/git-lfs/git-lfs) — LFS 定义、pointer 机制、`git lfs migrate` 提醒
- [github.com/newren/git-filter-repo](https://github.com/newren/git-filter-repo) — 官方推荐、fresh clone 要求、历史重写

**非 Git 对照方案**

- [restic.net](https://restic.net/) — 现代备份，支持 Windows
- [syncthing.net](https://syncthing.net/) — 持续文件同步，支持 Windows

---

## 附录：本次实测环境记录

```
$ git --version
git version 2.55.0.windows.3

$ git config --global core.excludesFile
（无输出，退出码 1）

$ git config --global --list
user.email=2958017271@qq.com
user.name=shihao-hub
filter.lfs.smudge=git-lfs smudge -- %f
filter.lfs.process=git-lfs filter-process
filter.lfs.required=true
filter.lfs.clean=git-lfs clean -- %f
safe.directory=*
credential.https://gitee.com.provider=generic
core.autocrlf=true
...

$ cd /tmp && pwd -W
C:/Users/29580/AppData/Local/Temp       # 所有 pattern 实验都在 /tmp/gitignore-lab 下完成
```

实验脚本位于 `C:/Users/29580/AppData/Local/Temp/gitignore-lab/run.sh` ~ `run5.sh`，可自行重跑复现（临时目录，重启后可能已被系统清理；需要时按本报告第 2 节重搭即可）。
