# fastapi_layered_api —— Router → Service → Repository 分层与事务边界

> 代码：`apps/fastapi_layered_api` ｜ 依赖：PostgreSQL ｜ 栈：FastAPI + SQLAlchemy 2.0 async

## 一、这组实验解决什么问题

为什么后端代码要分三层？不是为了形式，而是为了**让每类变更只爆炸在一个文件里**：接口协议变更只动 Router、业务规则变更只动 Service、SQL 优化只动 Repository。本实验搭一个最小的收藏夹 CRUD 服务，用五个演示覆盖分层的全部关键点：契约校验、依赖注入、统一响应、业务冲突翻译、跨仓储事务回滚。

## 二、核心原理

### 2.1 三层的职责与禁区

| 层 | 职责 | 禁区 |
|---|---|---|
| Router | 解析请求、调用 Service、包装 `CommonResult`、异常翻译 | 写 SQL、写业务规则 |
| Service | 业务规则、跨模块编排、**事务成败的决定者** | 直接拼 SQL（下沉到 Repo） |
| Repository | SQL 的唯一归宿、数据映射 | `commit()`（只 `flush`） |

关键分工是**事务边界**：Repository 只 flush（SQL 已发但事务未定，能拿自增 id），Service 统一 commit/rollback——「一个请求一个事务」由此成立，跨仓储写入天然原子（与 [sqlalchemy-session-lifecycle](SQLAlchemy Session 生命周期.md) 场景 4 呼应）。

### 2.2 依赖注入：请求级 Session 生命周期

```python
async def get_session() -> AsyncSession:
    async with Session() as session:      # 请求开始：开 Session
        yield session                     # 注入给 Service
                                         # 请求结束：自动 close（归还连接）

def get_collection_service(session = Depends(get_session)):
    return CollectionService(session)     # Service 拿着同一个 session 编排多个 Repo
```

一个请求内所有 Repository 共享同一个 Session = 同一个事务。测试时用 `dependency_overrides` 换成内存实现即可，不需要 mock 到处飞。

### 2.3 Pydantic：契约前置

请求模型（`Field(min_length=1)`）在进入 Service **之前**完成校验，非法请求以 422 拒之门外——业务层永远不用写「参数非空」检查。响应模型同时是文档与序列化白名单（防止 ORM 内部字段泄漏）。

### 2.4 统一响应信封

`CommonResult[T]`：`{code, message, data, success}`。所有异常处理器输出同一形状——前端的错误处理只写一份。业务异常（ConflictError）在 Router 翻译成 409，未捕获异常统一 500 信封（不泄漏堆栈）。

## 三、演示内容（demo 模式自动跑）

| 演示 | 观察点 |
|---|---|
| 创建收藏夹（含 3 条目） | Router → Service → Repo 全链路；items=3 |
| 空 name | 422——校验在进 Service 前完成 |
| 同名再建 | 409 + 统一信封（ConflictError 被翻译） |
| 列表/详情/删除 | 分页参数、404 处理 |
| rollback-demo | collection + items 写入后注入失败 → **两表零残留**（跨仓储事务原子性） |

## 四、运行方式

```powershell
docker compose up -d postgres
uv run python -m apps.fastapi_layered_api                 # 自动起服务 + 跑演示
uv run python -m apps.fastapi_layered_api --serve --port 8710
# 然后 curl http://127.0.0.1:8710/docs 玩 Swagger
```

## 五、面试高频问答

- **Q：为什么分三层？扁平写不行吗？** A：变更隔离（协议/规则/SQL 各自爆炸各文件）+ 测试分层（Service 用 mock Repo，Repository 用 testcontainers）+ 审查聚焦（看 SQL 只看一处）。行数少时扁平更快——分层是规模决策不是道德决策。
- **Q：事务边界放哪层？** A：决定权在 Service（或 UoW），Repository 只 flush。放 Repository 里跨仓储写就失去原子性；放 Router 里 Service 无法独立测试。
- **Q：DI 相比全局单例的好处？** A：请求级生命周期（Session 不跨请求泄漏）、测试可替换、隐式依赖显式化。
- **Q：业务错误返回 200 + code 还是 4xx？** A：团队约定问题，关键是**统一**：本实验用 HTTP 状态码（409/404/422）+ 信封；生产项目常见「全部 200 + 业务 code」（网关/监控对 HTTP 语义有约束时）。两种都要能说出取舍。
- **Q：Router 里能查库吗？** A：能跑但不该：SQL 会绕过 Repository 的审计/复用/优化机制，「看代码不知道有哪些 SQL」是维护灾难的开始。

## 六、生产对照（creativault）

生产仓库把这套约定固化为规则文件：Router 五项职责封顶、`SELECT *` 禁令、Repository 必须挂查询计时装饰器、分页统一 `fastapi_pagination`。教学版保留骨架（显式列 SELECT、flush/commit 分离、统一信封、DI 工厂），省略通用泛型基类与多数据源路由。
