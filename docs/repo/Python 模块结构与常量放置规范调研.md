# Python 模块结构与常量放置规范调研

> 调研对象：Python 单文件模块（module）的内部结构；重点是模块级常量（尤其"开关/配置项"这类常量）的放置位置。
>
> 调研日期：2026-10-09
>
> 一句话结论：**"常量统一放在文件最顶部"不是 Python 官方规范，也没有任何主流工具强制；它是一条由社区实践、以及"imports 必须靠前"的间接规范措辞共同支撑的人读惯例。** 真正有硬约束的只有运行时语义：常量必须在其第一次被引用之前执行到。

## 0. 信息分级标注约定

本文对每条关键论断标注信息来源层级：

- 【官方】：Python 官方文档、语言参考、教程、PEP；
- 【规范/代码】：权威风格指南与工具规则（Google Python Style Guide、pylint / ruff / pycodestyle / isort / Black 的规则文档）；
- 【实践】：社区实践与教学站点（如 Real Python，明确非官方）；
- 【推断】：本文基于上述材料与工程常识的综合推断，无单一权威出处。

所有规则编号（PEP 编号、pylint message 编号、ruff rule code、pycodestyle 错误码）均已逐条对照官方文档核实。

## 1. 结论先行

1. 【官方】PEP 8 只明确规定一条与常量相关的相对顺序：**imports 必须在 module globals and constants 之前**（"just after any module comments and docstrings, and before module globals and constants"）。PEP 8 对普通常量只规定命名（全大写、下划线分隔），**没有规定任何位置**。
2. 【实践】"常量应放在文件顶部（imports 之后）"的明文推荐来自 Real Python 等社区来源；Google Python Style Guide 只有与 PEP 8 相同的间接措辞（imports 在 constants 之前）与"鼓励模块级常量"的表态。**没有任何官方规范或工具要求常量置顶。**
3. 【规范/代码】所有"元素位置"类工具强制都只覆盖 import 区块：pylint `wrong-import-position / C0413`、`wrong-import-order / C0411`、`ungrouped-imports / C0412`；pycodestyle/flake8 `E402`；ruff `I001 / I002 / E402`；isort 只排序 import。Black 明确声明"严格只做格式化"。**没有任何主流工具检查常量位置。**
4. 【官方】唯一的硬约束来自运行时语义：模块顶层语句自上而下执行；类定义、默认参数值、装饰器表达式都在"定义时"求值，因此它们引用的常量必须先执行到。"就近放置"只要满足先后顺序，完全合法。
5. 【推断/实践】因此"顶置"与"就近"不是合规问题，而是可读性/维护性权衡：开关与配置类常量适合"打开即见"（顶部）；只被单个类/函数耦合的实现细节常量适合就近。常见"标准模块骨架"是社区汇总，其中只有 docstring / `__future__` / dunder / imports 的相对顺序有官方依据。

## 2. 官方规范层

### 2.1 PEP 8 到底规定了什么顺序

【官方】PEP 8 对模块结构的直接规定集中在两处（<https://peps.python.org/pep-0008/>）：

**（1）Imports 一节（相对顺序的间接约束）**：

> "Imports are always put at the top of the file, just after any module comments and docstrings, and before module globals and constants."

即：imports 位于模块注释与 docstring 之后、任何模块级全局量与常量之前。分组顺序为：

1. Standard library imports（标准库）；
2. Related third party imports（第三方）；
3. Local application/library specific imports（本地/本项目）。

组与组之间空一行。注意这句话规范的对象是 **imports 的位置**；它顺带说明常量在 imports 之后，但**并未要求常量必须紧贴 imports 或必须放在"文件顶部"**。

**（2）Module Level Dunder Names 一节（dunder 位置）**：

> "Module level 'dunders' (i.e. names with two leading and two trailing underscores) such as `__all__`, `__author__`, `__version__`, etc. should be placed after the module docstring but before any import statements *except* `from __future__` imports. Python mandates that future-imports must appear in the module before any other code except docstrings."

PEP 8 给出的示例顺序为：

```python
"""This is the example module.

This module does stuff.
"""

from __future__ import barry_as_FLUFL

__all__ = ['a', 'b', 'c']
__version__ = '0.1'
__author__ = 'Cardinal Biggles'

import os
import sys
```

即合法顺序是 **docstring → `__future__` → 模块级 dunder → 其他 imports**。其中 dunder 位置用 "should"（建议），而 `__future__` 的位置是语言级强约束（见 2.5）。

**（3）Constants 一节（只有命名，没有位置）**：

> "Constants are usually defined on a module level and written in all capital letters with underscores separating words. Examples include `MAX_OVERFLOW` and `TOTAL`."

这是 PEP 8 关于常量的全部内容：命名风格 + "通常定义在模块级"（`usually`），没有任何位置要求。

**（4）PEP 8 未规定的内容**：PEP 8 正文没有对 `if __name__ == '__main__'` 的位置作任何规定（该惯例的官方出处见 2.4）。

### 2.2 PEP 257（docstring）

【官方】PEP 257（<https://peps.python.org/pep-0257/>）：

- docstring 的定义："a string literal that occurs as the first statement in a module, function, class, or method definition"——**模块 docstring 必须是模块的第一个语句**才成为 `__doc__`；
- "All modules should normally have docstrings"，模块 docstring 通常列出模块导出的类、异常与函数；
- 脚本（stand-alone program）的 docstring 应能作为 usage message 使用；
- 性质声明："The PEP contains conventions, not laws or syntax."

### 2.3 PEP 591（typing.Final）

【官方】PEP 591（<https://peps.python.org/pep-0591/>）引入 `typing.Final` 与 `@final`，其动机之一明确写着：

> "Preventing unintended modification of module and class level constants and documenting them as constants in a checkable way."

关键语义：

- 每个模块/类作用域最多一条 final 声明、恰好一次赋值，由 **type checker** 检查；
- 它**不改变位置语义，也不做运行时强制**（PEP 591 明确说明 typing 不做 runtime enforcement）；
- PEP 591 自己的示例就把类级常量写在类体内（`class Base: DEFAULT_ID: Final = 0`），说明官方层面完全接受"常量放在类体内"这种非顶部写法。

### 2.4 `if __name__ == '__main__'` 的官方说法

【官方】Python 文档《`__main__` — Top-level code environment》（<https://docs.python.org/3/library/__main__.html>）：

- 模块在顶层执行时 `__name__` 为 `'__main__'`，由此得到惯用法 `if __name__ == '__main__': ...`；
- "Putting as few statements as possible in the block below `if __name__ == '__main__'` can improve code clarity and correctness. Most often, a function named `main` encapsulates the program's primary behavior."；
- 推荐入口写法 `sys.exit(main())`，并把 `main()` 定义放在 guard 之前。

【官方】教程 6.1.1（<https://docs.python.org/3/tutorial/modules.html>）用 `fibo.py` 示范了 guard 放模块末尾、让文件同时可作脚本与模块。注意：这些文档给出的是**用法与习惯**，没有"guard 必须位于文件最后一行"的语法级规定。

### 2.5 运行时硬约束：为什么"必须先用先定义"

【官方】这是全篇唯一带强制性的层级：

- 执行模型（<https://docs.python.org/3/reference/executionmodel.html>）："A Python program is constructed from code blocks. A block is a piece of Python program text that is executed as a unit. The following are blocks: a module, a function body, and a class definition."；且 "A class definition is an executable statement that may use and define names."
- 教程 Classes 9.3（<https://docs.python.org/3/tutorial/classes.html>）："Class definitions, like function definitions (`def` statements) must be executed before they have any effect."
- 语言参考 Function definitions（<https://docs.python.org/3/reference/compound_stmts.html>）："**Default parameter values are evaluated from left to right when the function definition is executed.**"；"**Decorator expressions are evaluated when the function is defined**, in the scope that contains the function definition."；类装饰器适用同样的求值规则。
- `from __future__` 是语法级硬约束（<https://docs.python.org/3/reference/simple_stmts.html#future-statements>）："A future statement must appear near the top of the module. The only lines that can appear before a future statement are: the module docstring (if any), comments, blank lines, and other future statements."

**推论（【官方】语义 + 【推断】结论）**：任何在类体、默认参数、装饰器中引用的模块级常量，都必须在这三处"定义时求值"之前执行到，否则抛 `NameError`。因此"就近放置"在语义上完全可行——解析器不要求常量在顶部，只要求它在**首次被求值的时刻已经绑定**。

一个重要的版本例外（【官方】）：Python 3.14 起注解（annotation scopes）默认惰性求值（<https://docs.python.org/3/reference/executionmodel.html#lazy-evaluation>，基于 PEP 649/749），"注解引用的名字必须先定义"的旧经验被放宽；但默认参数与装饰器的求值时机**没有**改变。

### 2.6 `from __future__` 与 docstring 的强约束汇总

| 元素 | 约束性质 | 出处 |
|---|---|---|
| 模块 docstring | 必须是模块的第一条语句才成为 `__doc__` | PEP 257 |
| `from __future__` | 语法硬约束：前面只允许 docstring、注释、空行、其他 future | 语言参考 simple_stmts |
| imports | PEP 8 规范（`always`），但教程明言 "customary but not required" | PEP 8 / 教程 Modules |
| 模块级 dunder | PEP 8 建议（`should`），无语法强制 | PEP 8 |
| 普通常量 | 只有命名约定，无位置规定 | PEP 8 |

【官方】教程 Modules 同时提醒："It is customary but not required to place all `import` statements at the beginning of a module"（<https://docs.python.org/3/tutorial/modules.html>）——即 import 置顶是习惯（custom），不是语法。

## 3. 权威风格指南层

### 3.1 Google Python Style Guide

【规范/代码】Google Python Style Guide（<https://google.github.io/styleguide/pyguide.html>）：

- **2.5 Mutable Global State**："Module-level constants are permitted and encouraged. For example: `_MAX_HOLY_HANDGRENADE_COUNT = 3` for an internal use constant... Constants must be named using all caps with underscores."——鼓励模块级常量，并给出 `_` 前缀表示模块内部使用；
- **3.13 Imports formatting**："Imports are always put at the top of the file, just after any module comments and docstrings and **before module globals and constants**."（与 PEP 8 同句）分组从最通用到最专用：future → 标准库 → 第三方 → 仓库子包；
- **3.7 Shebang Line**："Most `.py` files do not need to start with a `#!` line. Start the main file of a program with `#!/usr/bin/env python3`..."——shebang 只对直接可执行文件有意义（Windows 仓库通常省略）；
- **3.8.2 Modules**："Files should start with a docstring describing the contents and usage of the module."；
- **3.17 Main**："its main functionality should be in a `main()` function, and your code should always check `if __name__ == '__main__'` before executing your main program"；并提醒 "All code at the top level will be executed when the module is imported."

### 3.2 The Hitchhiker's Guide to Python（需澄清的一个常见误引）

【实践】该指南《Structuring Your Project》页面（<https://docs.python-guide.org/writing/structure/>）**并不规定单文件内部元素的顺序**。通读该页：它讲的是仓库/目录布局（README、LICENSE、setup.py、模块目录、tests 目录、Makefile 的摆放）、模块与 import 机制、包（`__init__.py`）机制、OOP 与纯函数等。

它唯一与"执行顺序"相关的一句话是模块机制说明："When `modu.py` is found, the Python interpreter will execute the module in an isolated scope. Any top-level statement in `modu.py` will be executed, including other imports if any."（这佐证了顶层语句会按序执行，但不构成模块内部的排序规范。）

因此：**若某处声称"Hitchhiker's Guide 推荐了标准模块顺序（shebang → docstring → ...）"，属误引**；该顺序是社区汇总（见第 5 节），不是该指南的条款。

### 3.3 Real Python 的 Python Constants 文章（社区实践佐证，非官方）

【实践】Real Python《Python Constants: Improve Your Code's Maintainability》（<https://realpython.com/python-constants/>，社区教学站点，非标准机构）明确写道：

- "The recommended practice is to define constants at the top of any `.py` file **right after any import statements**. This way, people reading your code will immediately know the constants' purpose and expected treatment."；
- 组织策略一章给出四种做法：**与相关代码同模块（放模块顶部，仅本模块使用时加 `_` 前缀）**、**专用 `constants.py` 模块（跨模块共享时）**、**配置文件**、**环境变量**（后者还提醒敏感信息的暴露风险）；
- 文中同样强调 Python 没有真正的常量语法，全大写只是命名约定（并引用 PEP 8 Constants 一节）。

Real Python 的表述是"recommended practice"，不是"mandatory"——这与本文判断一致：**常量置顶是社区推荐，不是规范强制。**

## 4. 工具强制层：机器强制 vs 人读惯例

【规范/代码】以下是各工具规则文档的原文核对结果。可以看到：**所有"位置强制"无一例外只覆盖 import 区块。**

| 工具 | 规则编号 | 文档原文（含义） | 是否管常量位置 |
|---|---|---|---|
| pylint | `wrong-import-position / C0413` | "Used when code and imports are mixed." | 否 |
| pylint | `wrong-import-order / C0411` | "Used when PEP8 import order is not respected (standard imports first, then third-party libraries, then local imports)." | 否 |
| pylint | `ungrouped-imports / C0412` | "Used when imports are not grouped by packages." | 否 |
| pycodestyle（flake8 内核） | `E402` | "module level import not at top of file"（错误码表） | 否 |
| ruff | `unsorted-imports / I001` | "De-duplicates, groups, and sorts imports based on the provided isort settings."（派生自 isort） | 否 |
| ruff | `missing-required-import / I002` | "Adds any required imports, as specified by the user, to the top of the file."（派生自 isort） | 否 |
| ruff | `module-import-not-at-top-of-file / E402` | "Checks for imports that are not at the top of the file."，并原文引用 PEP 8 那句 "imports are always put at the top of the file... before module globals and constants"；对 `sys.path` / `os.environ` 的中间修改例外 | 否 |
| isort | （工具定位） | "isort is a Python utility / library to sort imports alphabetically and automatically separate into sections and by type." | 否 |
| Black | （工具定位） | "Black is strictly about formatting, nothing else."；格式化后校验 AST（有限例外），不会为了风格重排模块级语句 | 否 |

来源：pylint C0413 / C0411 / C0412（<https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/wrong-import-position.html>、<https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/wrong-import-order.html>、<https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/ungrouped-imports.html>）；pycodestyle 错误码表（<https://pycodestyle.pycqa.org/en/latest/intro.html>）；ruff I001 / I002 / E402（<https://docs.astral.sh/ruff/rules/unsorted-imports/>、<https://docs.astral.sh/ruff/rules/missing-required-import/>、<https://docs.astral.sh/ruff/rules/module-import-not-at-top-of-file/>）；isort（<https://isort.readthedocs.io/en/latest/>）；Black FAQ（<https://black.readthedocs.io/en/stable/faq.html>）。

几点补充说明：

- **pylint C0413 的真实含义容易被误记**。它不是"import 不在文件顶部"，而是"代码与 imports 混在一起"（例如先写一句赋值再写 import）。"import 必须在顶部"的检查实际由 pycodestyle `E402` / ruff `E402` 承担。
- **"常量放 imports 之后"其实是机器强制的镜像效应**：由于 `E402`/`C0413` 要求 import 区块之前不能有代码，而普通常量赋值也算"代码"，所以任何"imports + 常量"的组合中，常量天然被推到 import 之后；这被很多人误读成"常量必须放在文件顶部区域"。但它约束的是 **import 的相对位置**。
- **Black 与常量位置的关系**：Black 定位为 formatter（"strictly about formatting, nothing else"），只做空白、换行、引号等统一化，并以 AST 等价校验兜底；它不会把分散的常量挪到顶部去。
- 关于"哪些工具不检查"的说明：以上是对主流工具（pylint / pycodestyle / flake8 / ruff / isort / Black）规则文档的逐条核对。这是文档层面的**否定性调查**：未发现任何"常量位置"规则。理论上第三方 flake8 插件可以添加任意自定义检查，故不对"所有可能的工具"作绝对断言。

## 5. 反方与替代实践

### 5.1 支持"常量置顶"的理由

【实践】【推断】综合社区惯例，顶置（imports 之后、其余定义之前）的常见理由：

- 读者打开文件先看到全部可调参数（开关、阈值、路径模板），"改配置只需看开头"；
- 修改值只有一个入口，避免散落多处；
- PEP 8/Google 关于 imports 的措辞已被广泛读作"常量应在 imports 紧随之后"；
- Real Python 明文推荐（见 3.3），且很多项目与教材沿用。

### 5.2 支持"就近放置"的理由

【推断】没有找到任何官方或权威指南倡导"普适的常量就近放置"；它是一个工程权衡，常见理由：

- 内聚/局部性：常量与唯一使用它的逻辑放在一起，读者不必在文件首尾之间来回跳；
- diff 局部化：修改某功能时改动集中在一处，减少冲突；
- 避免模块命名空间污染，降低被无关代码误用/顺手修改的概率；
- 类私有常量天然属于类体（PEP 591 官方示例 `BORDER_WIDTH: Final = 2.5` 就在类体内，见 2.3）；
- 仅一个函数使用的实现细节常量，放函数内部可精确锁定作用域。

需要强调：就近放置**必须满足运行时顺序**（见 2.5）；若常量被类体、默认参数、装饰器引用，则必须先定义再引用。

### 5.3 组织常量的替代工具

- **Enum**：【官方】标准库 `enum` 文档（<https://docs.python.org/3/library/enum.html>）：枚举是"a set of symbolic names (members) bound to unique values"，"enumeration members ... are functionally constants"；`IntEnum`/`StrEnum` 明确为"existing constants 的替代"场景设计。适合"有限取值集合"类常量（状态、模式）。
- **typing.Final**：【官方】PEP 591，给常量加"不可重新赋值"的类型检查标注，可与模块级、类级常量并存（位置无关）。
- **命名空间类 / SimpleNamespace**：【实践】把相关常量收进一个类或对象，获得 `Color.RED` 式的命名空间；代价是多一层访问与可能的实例化。
- **专用 constants 模块**：【实践】Real Python 建议跨模块共享的常量集中到 `constants.py`；注意 AGENTS.md 的文档/代码布局约束：本项目语境下"哪些常量算跨模块共享"要按实际使用决定，不要过度集中。
- **配置文件 / 环境变量**：【实践】适合随部署环境变化的值（而不是真正常量）；Real Python 提醒环境变量可能泄漏到日志/子进程，敏感值应使用专门的 secrets 管理。

### 5.4 大模块的常见处理

【推断】当常量多到影响阅读时：

1. 优先按职责拆模块（Hitchhiker's Guide 的模块化思路，见 3.2）；
2. 共享面大的常量抽到独立 constants 模块；
3. 模块内按功能分组，组间用注释分隔/空行（PEP 8 允许"Extra blank lines may be used (sparingly) to separate groups"——原指函数，类推到常量分组是常见做法，属【推断】）；
4. 用 Enum 合并同类取值（5.3）。

## 6. 常见模块骨架（社区汇总，非官方标准）

【推断/实践】下面这份顺序是社区广泛流传的汇总。**它不是任何 PEP 或官方文档的条款**；其中只有 docstring、`__future__`、dunder、imports 的相对位置有官方依据（标注如下），其余都是惯例：

```text
shebang（可选，仅直接可执行文件）          ← 【规范/代码】Google 3.7
PEP 723 内联脚本元数据块（uv 单文件脚本）  ← 本仓库约定（AGENTS.md）
module docstring                          ← 【官方】PEP 257 第一条语句
from __future__ imports                   ← 【官方】语言参考硬约束
__all__ / 模块级 dunder                    ← 【官方】PEP 8（should）
imports（stdlib → 第三方 → 本地，组间空行）← 【官方】PEP 8 / Google 3.13
模块常量 / 开关（顶置区域）                ← 【实践】Real Python 推荐，无强制
类型别名 / 异常类                          ← 惯例（无官方位置规定）
类定义                                    ← 【官方】须在用前执行
函数定义                                  ← 【官方】须在用前执行
main()                                    ← 【规范/代码】Google 3.17
if __name__ == '__main__': 入口 guard      ← 【官方】用法见 __main__ 文档
```

对本仓库 `.scripts/`（PEP 723 + uv 单文件脚本）适用时，`# /// script` 注释块放在最前；注释不属于语句序列，不影响"docstring 是第一个语句"的语义。

## 7. 本仓库落地建议：`.scripts/install-mcp.py` 的开关常量

### 7.1 现状与目标

【推断】当前 `install-mcp.py`（992 行）中标称"脚本顶部"的两层开关实际分布为：

- `PRESET_ENABLED`：约第 286 行（imports 与少量函数定义之后，文件约 29% 处）；
- `AGENT_ENABLED`：约第 726 行（AgentHandler 类等实现之后，文件约 73% 处）。

两者相隔约 440 行，而文件 docstring 又自称"脚本顶部有两层对称的常量总开关"，存在"说法与位置不一致"的问题。两者都是**纯 bool 字面量 dict、不依赖任何类/函数**，因此没有理由分散在两处：

**建议：把 `PRESET_ENABLED` 与 `AGENT_ENABLED` 相邻上移到模块 docstring 与 imports 之后的最顶部区域（"打开即见"），保持两层对称与注释完备。** 这一位置的选择依据是：

- 【实践】Real Python 推荐的"constants right after imports"；
- 【官方】PEP 8/Google 的 imports 位置约束（常量不可能放到 import 之前区域而不触发 `E402`/`C0413`）；
- 本脚本的使用方式（用户手动改开关后运行）决定"可发现性"最重要。

### 7.2 推荐模块骨架（示意，不要求立即重构）

```python
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""install-mcp.py：通用多 MCP 配置给多 Agent 的强化分发与管理工具

（保留现有说明：两层开关语义、全量收敛、常用指令等）
"""

import argparse
import os
from pathlib import Path
from typing import Dict, Optional

# ============================================================================
# 第一层总开关：PRESET_ENABLED —— 每个预设 MCP 装不装
# True  = 缺省收敛时同步/修复到各启用 Agent；False = 缺省收敛时卸载
# ============================================================================
PRESET_ENABLED: Dict[str, bool] = {
    "aoci": True,
    "chrome-devtools": True,
    "everything": False,  # 每个 Agent 会话各起一份常驻进程，较占内存
}

# ============================================================================
# 第二层总开关：AGENT_ENABLED —— 每家 Agent 参不参与（省内存利器）
# True  = 正常参与预设收敛；False = 不部署任何内置预设并清理残留
# （--agent 显式点名可临时覆盖本开关）
# ============================================================================
AGENT_ENABLED: Dict[str, bool] = {
    "claude": True,
    "opencode": True,
    "codex": True,
    "pi": True,
    "antigravity": True,
    "antigravity-ide": True,
    "dsh": True,
}

# ---- 以下为普通模块常量与内部数据（可按功能分组，组间空行）----

# ---- 与实现强耦合的注册表：有依赖，不能上移（示意）----
# TARGET_AGENTS 依赖 AgentHandler 等类定义，必须在相应类之后构建；
# 这类"依赖具体类型的常量"不要机械地上移。

# ---- 类与函数定义 ----

def main() -> int:
    ...

if __name__ == "__main__":
    raise SystemExit(main())
```

### 7.3 "就近放置"在此脚本中的适用边界

【推断】就近放置只在"常量与使用处强耦合"时才更优，典型情形：

- 类私有常量：写在类体内，如 `class Window: BORDER_WIDTH: Final = 2.5`（PEP 591 示例的形态）；
- 仅一个函数使用的实现细节（如表驱动的映射），放在该函数定义之前或函数内部；
- **依赖其他模块级对象的常量**：如 `TARGET_AGENTS` 引用了 `AgentHandler` 子类实例，运行时必须在那些类定义之后构建——这类"常量"的位置由运行时顺序决定，**不应**为了"全部置顶"而破坏依赖关系。

## 8. 无法核实或存在争议的点

1. **"常量统一置顶"无权威出处**：本次逐条核对 PEP 8/257/591、Python 文档/教程/语言参考、Google、pylint/ruff/pycodestyle/isort/Black 后，未发现任何一条"普通常量必须放在文件顶部"的规定。该说法只能被归类为社区惯例。
2. **Hitchhiker's Guide 的误引**：用户问题中的"Hitchhiker's Guide 推荐标准模块顺序"未在该指南《Structuring Your Project》页面找到；该页讲的是仓库/目录结构与模块机制。若确有出处，应在其他页面或第三方总结中，本次未核实到。
3. **PEP 8 dunder 位置与现实的偏差**：PEP 8 建议 `__all__` 等放在 imports 之前（"should"），且 `__future__` 硬约束还必须在 dunder 之前；但现实中大量现代代码把 `__all__` 放在 imports 之后，工具也不检查——两种写法并存。
4. **Real Python 的层级**：其"置顶推荐"是社区教学站点的实践建议，非规范；引用时须注明非官方（见 3.3）。
5. **"没有工具检查常量位置"的证明性质**：这是对主流工具规则文档的否定性调查，不能穷尽所有第三方插件/自研检查。
6. **"就近放置收益"（内聚、diff 局部化）** 属工程常识，未找到权威实证来源；本文将其标注为【推断/实践】。
7. **Python 3.14 注解惰性求值的时点变化**：注解不再在定义时立即求值（PEP 649/749），使"注解引用值必须先定义"的旧约束放宽；默认参数与装饰器的求值时机不变。跨版本阅读老代码时不要把两者混淆。

## 参考资料

1. PEP 8 – Style Guide for Python Code：<https://peps.python.org/pep-0008/>
2. PEP 257 – Docstring Conventions：<https://peps.python.org/pep-0257/>
3. PEP 591 – Adding a final qualifier to typing：<https://peps.python.org/pep-0591/>
4. `__main__` — Top-level code environment：<https://docs.python.org/3/library/__main__.html>
5. The Python Tutorial – Modules：<https://docs.python.org/3/tutorial/modules.html>
6. The Python Tutorial – Classes：<https://docs.python.org/3/tutorial/classes.html>
7. The Python Language Reference – Execution model：<https://docs.python.org/3/reference/executionmodel.html>
8. The Python Language Reference – Compound statements（Function / Class definitions）：<https://docs.python.org/3/reference/compound_stmts.html>
9. The Python Language Reference – Simple statements（Future statements）：<https://docs.python.org/3/reference/simple_stmts.html#future-statements>
10. Google Python Style Guide：<https://google.github.io/styleguide/pyguide.html>
11. The Hitchhiker's Guide to Python – Structuring Your Project：<https://docs.python-guide.org/writing/structure/>
12. Real Python – Python Constants: Improve Your Code's Maintainability：<https://realpython.com/python-constants/>
13. pylint – wrong-import-position / C0413：<https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/wrong-import-position.html>
14. pylint – wrong-import-order / C0411：<https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/wrong-import-order.html>
15. pylint – ungrouped-imports / C0412：<https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/ungrouped-imports.html>
16. pycodestyle – Introduction / Error codes：<https://pycodestyle.pycqa.org/en/latest/intro.html>
17. ruff – unsorted-imports (I001)：<https://docs.astral.sh/ruff/rules/unsorted-imports/>
18. ruff – missing-required-import (I002)：<https://docs.astral.sh/ruff/rules/missing-required-import/>
19. ruff – module-import-not-at-top-of-file (E402)：<https://docs.astral.sh/ruff/rules/module-import-not-at-top-of-file/>
20. isort documentation：<https://isort.readthedocs.io/en/latest/>
21. Black – Frequently Asked Questions：<https://black.readthedocs.io/en/stable/faq.html>
22. `enum` — Support for enumerations：<https://docs.python.org/3/library/enum.html>
