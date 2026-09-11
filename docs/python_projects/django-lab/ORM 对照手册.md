# Django ORM × SQLAlchemy 2.0 对照手册（django-lab / sqla_lab）

> 同一个图书馆业务、同一个数据库：Django 继续管建表与迁移，SQLAlchemy 只做「映射 + 查询」。
> 每条 Django 写法旁边站着一条等价的 SQLAlchemy 翻译，共库对照、逐条验证。

## 怎么跑

```powershell
cd python_projects/django-lab
uv run manage.py migrate          # 表由 Django 迁移建
uv run manage.py seed_demo        # 演示数据
uv run manage.py orm_compare      # 终端并排对照：11 项场景全部要求两边一致
uv run manage.py orm_compare --sql # 额外打印两边真实执行的每条 SQL
# 浏览器打开 http://127.0.0.1:8000/compare/ —— 页面版对照（写场景只展示代码）
uv run manage.py test             # 33 个测试（含 14 个跨 ORM 一致性测试）
```

## 目录速览

| 文件 | 内容 |
|---|---|
| `sqla_lab/orm.py` | 声明式映射 5+1 张表：枚举 / 生成列 / db_default / 部分唯一索引 / relationship 全对照 |
| `sqla_lab/session.py` | engine/Session 工厂：从 `django.db.connection` 动态解析 URL（测试自动跟随测试库） |
| `sqla_lab/queries.py` | 同步查询对照：filter / Q / icontains / annotate / eager loading / update 语句 |
| `sqla_lab/async_queries.py` | AsyncSession 对照 Django async ORM（`acount` / `async for`） |
| `sqla_lab/scenarios.py` | 场景注册表：命令与页面共用的 10+1 个对照场景 |
| `sqla_lab/tests.py` | 跨 ORM 一致性测试（TransactionTestCase，原因见下文「连接与事务」） |

## 概念映射总表

### 模型定义（orm.py）

| Django | SQLAlchemy 2.0 | 备注 |
|---|---|---|
| `models.Model` | `class Base(DeclarativeBase)` + `Mapped[]` / `mapped_column()` | 声明式映射，类型驱动 |
| `models.CharField(max_length=...)` | `String(length)` | |
| `models.TextField` | `Text` | |
| `models.DecimalField` | `Numeric(precision, scale)` | |
| `models.TextChoices` | `enum.StrEnum` + `Enum(native_enum=False, values_callable=...)` | 读回来是枚举成员而非裸字符串 |
| `GeneratedField`（含税价） | `Computed("(price * 1.09)", persisted=True)` | STORED 生成列，INSERT 排除、DB 计算 |
| `db_default=Now()` | `server_default=func.now()` | INSERT 缺省由数据库填 |
| `ForeignKey(on_delete=DB_CASCADE)` | `ForeignKey(..., ondelete="CASCADE")` | 级联都下沉数据库；SQLAlchemy 的 ORM `cascade` 才是应用级 |
| `related_name="books"` | `relationship(back_populates="author")` | 显式双向；Django 靠魔法注册反向 |
| `ManyToManyField(through=...)` | 关联表 ORM 类 + `secondary` + `viewonly=True` 便捷集合 | 写操作走显式关联类 |
| `Meta.constraints` / `Meta.indexes` | `UniqueConstraint(name=...)` / `Index(...)` | 约束名两边完全一致 |
| 部分唯一约束（`condition=Q(...)`） | `Index(..., unique=True, sqlite_where=..., postgresql_where=...)` | 「同一本书同时只能有一条在借」由同一个索引对两个 ORM 兜底 |
| `Meta.ordering` | **没有对应物** | SQLAlchemy 必须每次显式 `order_by()` |
| `@property`（仅实例） | `hybrid_property`（实例 + 查询两用） | 一个定义顶 Django 的 property + Q/F 两套写法 |

### 查询语法（queries.py / async_queries.py）

| Django | SQLAlchemy 2.0 |
|---|---|
| `qs.filter(status=...)` | `select(...).where(Book.status == ...)` |
| `Q(a) \| Q(b)` / `Q(a) & Q(b)` | `or_(...)` / `and_(...)` |
| `title__icontains=kw` | `Book.title.ilike(f"%{kw}%")` |
| `select_related("author")` | `options(joinedload(Book.author))` |
| `prefetch_related("genres")` | `options(selectinload(Book.genres))` |
| `annotate(c=Count("books"))` | `select(..., func.count(Book.id)).outerjoin(...).group_by(...)` |
| `Model.objects.count()` | `select(func.count()).select_from(Model)` |
| `qs.first()` | `...limit(1)` |
| `qs[:5]` | `.limit(5)` |
| `obj.save(update_fields=[...])` | `session.execute(update(Model).where(...).values(...))` |
| `Model.objects.create(...)` | `session.add(Model(...))` + `flush` / `commit` |
| `transaction.atomic()` | `with Session(...)` + `session.begin()` / `session_scope()` |
| `await qs.acount()` | `(await session.scalar(select(func.count())...)) or 0` |
| `async for x in qs` | `(await session.scalars(stmt)).all()`（流式：`await session.stream()`） |

## 共库的关键决策与坑（按踩坑顺序记录）

1. **表由谁建**：Django 迁移是唯一事实源，SQLAlchemy 只映射不建表（不跑 `create_all`）。
2. **URL 动态解析**：engine 不读静态 env，而是从 `django.db.connection.settings_dict` 取
   `NAME/USER/...` 现算 URL——Django 测试切到 `file:memorydb_default?...`（共享内存库）时，
   SQLAlchemy 透传 URI 并追加 `uri=true` 连进**同一个内存库**；写成静态 URL 会连回 dev 库，
   测试数据全错（本项目第一版就踩过，还把测试数据误写进了 dev 库）。
3. **连接与事务**：两个 ORM 各开各的连接池、各管各的事务。Django `TestCase` 把数据包在
   未提交事务里，SQLAlchemy 独立连接**看不见**——所以跨 ORM 测试必须用
   `TransactionTestCase`（真实提交）。`tests.py` 的 `TransactionVisibilityLessonTests`
   专门演示：未提交的数据要么读旧快照（文件库/PG）、要么直接 `table is locked`
   （共享内存库的表级锁），反正**读不到未提交行**。
4. **async engine 不缓存**：aiosqlite 连接绑定创建它的事件循环，`asyncio.run` 每次一个新
   loop，池里旧连接全是坏的——`async_session_scope()` 随用随建、用完 `dispose()`。
   对照：Django async ORM 是「同步驱动 + 线程池」，没有 loop 归属问题。
5. **聚合查询的默认排序**：Django 6.x 的 `annotate()` + GROUP BY **不再套用** `Meta.ordering`
   （生成 SQL 无 ORDER BY），对照两侧都显式 `order_by` 才可比。
6. **反向关系上的 `isnull` 陷阱**：`exclude(borrows__returned_at__isnull=True)` 里的
   `IS NULL` 会连「从没被借过」（LEFT JOIN 空行）一起匹配掉；精确语义用
   `~Exists(BorrowRecord.objects.filter(book=OuterRef("pk"), ...))`——
   与 SQLAlchemy 的 `~exists().where(...).correlate(...)` 完全同构。
7. **时区坑**：SQLite 的 `CURRENT_DATE` 是 UTC，Django `timezone.localdate()` 用
   `TIME_ZONE`（Asia/Shanghai），UTC 0~8 点两者日期不同——逾期判断绑定 Python 侧日期最稳。
8. **Windows 测试清理**：SA 连接池握着句柄会让测试库文件删不掉，测试类
   `addClassCleanup(dispose_engines)`。
9. **控制台编码**：GBK 终端没有 `↔ ✓ ✗`，命令输出按 `sys.stdout.encoding` 降级
   （`<-> √ ×`）。

## 两个 ORM 的哲学差（学完代码后回看）

| 维度 | Django ORM | SQLAlchemy 2.0 |
|---|---|---|
| 定位 | 框架的一部分，模型即唯一事实 | 独立工具包，显式优于隐式 |
| 惯用法 | QuerySet 链式惰性求值 | `select()` 语句构建 + Session 工作单元 |
| 隐藏的魔法 | 反向关系、默认排序、自动 JOIN | 全部摆上台面，SQL 直读 |
| 属性复用 | property（实例）+ Q/F（查询）两套 | hybrid_property 一套两用 |
| 写路径 | `save()` 逐对象 | Unit of Work：flush 时统一算 diff |
| 迁移 | makemigrations 自动生成 | Alembic（本项目未引入——表归 Django 管） |

## 结论

「共库对照」跑通后得到的不只是两份 API 对照表，还有一条铁律：
**数据库层的约束（部分唯一索引、生成列、级联）对任何 ORM 都一视同仁地兜底**——
这正是 django-lab「并发兜底下沉到数据库」思想的延伸。
