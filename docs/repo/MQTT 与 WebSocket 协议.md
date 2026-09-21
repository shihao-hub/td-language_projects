# MQTT 与 WebSocket 协议

本文回答三个问题：MQTT 和 WebSocket 各自是什么、两者有什么区别、什么场景该用哪个。结论先行：**两者不是竞争关系，而是不同层次的协议，可以叠加使用（MQTT over WebSocket）**。

## 一句话定位

| 协议 | 定位 | 回答的问题 |
|---|---|---|
| MQTT | 应用层**消息协议** | 消息如何发布、订阅、路由、可靠投递 |
| WebSocket | **传输通道**协议 | 浏览器与服务器如何在一条 TCP 连接上双向通信 |

- MQTT 不管连接怎么建立，只管消息语义；WebSocket 只提供全双工字节管道，不管消息是什么、丢不丢。
- 类比：WebSocket 是「公路」，MQTT 是「带签收制度的快递体系」。快递可以走公路（MQTT over WebSocket），公路本身不负责签收。

## MQTT

### 是什么

MQTT（Message Queuing Telemetry Transport）：1999 年 IBM 为石油管道传感器设计的轻量消息协议，2014 年成为 OASIS 标准，现行版本 MQTT 5.0（2019）。专为低带宽、高延迟、不稳定网络、内存受限的设备设计——协议固定头最小仅 2 字节。

### 核心模型：发布/订阅

```
Publisher ──发布──> Broker ──投递──> Subscriber
（生产者）        （中枢，必须存在）   （消费者）
```

- 三角色解耦：发布者和订阅者互不知道对方（空间解耦）、不必同时在线（时间解耦）、不必互相等待（同步解耦）。
- **Topic**：`a/b/c` 式层级主题，支持通配符订阅——`+` 匹配单层（`sensor/+/temp`），`#` 匹配多层（`sensor/#`）。通配符只能用于订阅，不能用于发布。
- **Broker 是必需中枢**：常见实现有 EMQX、Mosquitto、HiveMQ，以及各云厂商 IoT 平台。客户端之间永不直连。

### QoS 三档（MQTT 的核心卖点）

| QoS | 语义 | 机制 | 代价 |
|---|---|---|---|
| 0 | 至多一次（可能丢） | 发完即忘 | 最低 |
| 1 | 至少一次（可能重） | PUBLISH + PUBACK 确认 | 中 |
| 2 | 恰好一次（不丢不重） | 四步握手：PUBLISH → PUBREC → PUBREL → PUBCOMP | 最高 |

关键认知：

- 投递保证分两段独立协商——「发送方 ↔ Broker」与「Broker ↔ 接收方」可各选各的 QoS。
- 实践中最常用 **QoS 1 + 消费端幂等**，兼顾可靠与开销；QoS 2 仅用于双端都无法容忍重复且频率低的指令。

### 会话与生命周期特性

- **Keep Alive 心跳**：客户端声明心跳间隔，无数据时发 PINGREQ；Broker 超过 1.5 倍间隔未收到任何报文即判掉线。
- **Last Will 遗嘱**：连接时预注册一条遗嘱消息，客户端异常掉线时由 Broker 代为发布——设备离线感知的标准做法。
- **Retained 保留消息**：Broker 保存主题的最后一条保留消息，新订阅者连接后立即收到——适合「最新状态」类主题。
- **持久会话**：Clean Session（3.1.1）/ Session Expiry（5.0）让客户端离线期间的消息由 Broker 暂存，重连后补发（离线消息）。
- MQTT 5.0 增强：Topic Alias（压缩重复主题名）、共享订阅（多消费者负载均衡）、原因码等。

### 传输与端口

- 原生跑在 TCP 上：明文 1883，TLS 8883。
- 浏览器场景跑在 WebSocket 上：通常 8083（ws）/ 443（wss）。

### 典型场景

物联网设备遥测与管控、APP 消息推送、车联网、工业/能源数据采集——共同特征是**海量弱网终端 + 需要离线消息与投递保证**。

## WebSocket

### 是什么

WebSocket：RFC 6455（2011），解决 HTTP「请求-响应、服务器无法主动推送」的根本限制。在一条 TCP 长连接上提供**浏览器与服务器之间的全双工通信**。

### 握手：借道 HTTP

```
客户端: GET /chat HTTP/1.1
        Upgrade: websocket
        Connection: Upgrade
        Sec-WebSocket-Key: <随机 base64>

服务端: HTTP/1.1 101 Switching Protocols
        Sec-WebSocket-Accept: <base64(SHA-1(Key + 固定GUID))>
```

- 握手是一次普通 HTTP 请求（可复用 80/443 端口、Cookie、代理配置），服务端同意后返回 101。
- 此后同一条 TCP 连接改用 WebSocket 帧协议，HTTP 语义结束——它**不是** HTTP 长连接，而是升级成了另一种协议。
- `Sec-WebSocket-Protocol` 头可协商子协议（如在 WebSocket 之上跑 STOMP）。

### 帧与连接维护

- 消息以**帧**传输，协议保证消息边界（对比裸 TCP 字节流需自己拆包）；opcode 区分 text / binary / ping / pong / close。
- 客户端 → 服务端的每一帧必须加掩码（防历史代理缓存投毒攻击），服务端 → 客户端不加。
- 心跳：协议层有 ping/pong 控制帧；实践中应用层通常另做业务心跳（如 socket.io 的 heartbeat），以同时检测「连接活着但业务假死」。
- **没有投递保证、没有自动重连**：连接断开期间的消息直接丢失，可靠性完全由上层实现。

### 基础设施注意点

- 中间的 Nginx / 负载均衡 / 网关必须显式支持 `Upgrade` 头转发，否则握手失败。
- 长连接与普通 HTTP 的连接超时、空闲回收、连接数上限配置逻辑不同，容量按「并发连接数 × 每连接内存」估算，而非 QPS。

### 典型场景

Web 聊天、协作文档、行情/监控大屏、在线游戏、AI 流式输出——共同特征是**浏览器参与 + 双方都需要主动发消息**。

## 两者对比

| 维度 | MQTT | WebSocket |
|---|---|---|
| 协议定位 | 应用层消息协议 | 传输通道（帧协议） |
| 通信模型 | 发布/订阅，经 Broker | 点对点：客户端 ↔ 服务器 |
| 可靠投递 | 内建 QoS 0/1/2 | 无，需自行实现 |
| 离线消息 | 支持（持久会话） | 不支持，断线即丢 |
| 设备发现/离线感知 | 遗嘱 + 保留消息，内建 | 需自行实现 |
| 浏览器支持 | 需 over WebSocket | 原生支持 |
| 典型端口 | 1883 / 8883 | 80 / 443（握手走 HTTP） |
| 服务端组件 | 必须部署 Broker | 自研或引入网关 |
| 典型客户端 | 设备、传感器、移动端 | 浏览器、Web 应用 |

## 组合使用：MQTT over WebSocket

浏览器没有原生 TCP 套接字（只有 HTTP/WS），企业内网又常只放行 80/443，所以浏览器侧接入 MQTT 的标准做法就是 **MQTT over WebSocket**：

```
应用语义层：  MQTT（QoS / 主题 / 会话）
通道层：      WebSocket 帧
传输层：      TCP / TLS（443）
```

典型实现：浏览器用 MQTT.js 连 `wss://broker:443/mqtt`（EMQX 默认路径 `/mqtt`），与设备侧的原生 MQTT 客户端共用同一个 Broker 和同一套主题——Web 端和设备端在同一个消息总线上互通。

## 选型建议

- 弱网设备、需要离线消息和投递保证 → **MQTT**
- 纯浏览器业务的实时双向通信、消息语义自己定义 → **WebSocket**（业务复杂时叠加 STOMP / socket.io 等上层协议）
- Web 端与 IoT 设备需要互通 → **MQTT over WebSocket**，统一 Broker
- 只是服务器单向推送且容忍秒级延迟 → SSE 或长轮询，比两者都简单

## 常见误区

- **「WebSocket 可以替代 MQTT」**：层次不同。WebSocket 只给通道，QoS、离线消息、遗嘱这些消息语义它一样都没有。
- **「WebSocket 连上就可靠了」**：断线期间消息全丢，重连和补发都要自己写；恰恰是 MQTT QoS/持久会话解决的那些问题。
- **「MQTT = 消息队列」**：名字里的 Queuing 是历史遗留（源自 IBM MQSeries），它没有队列的持久化消费语义，与 Kafka/AMQP 不是一类东西。
- **「QoS 2 就万无一失」**：QoS 2 只保证协议层不丢不重，开销最大；绝大多数业务用 QoS 1 + 消费端幂等更划算。

## 参考资料

- MQTT Version 5.0 — OASIS Standard
- RFC 6455 — The WebSocket Protocol
- EMQX 文档 — MQTT over WebSocket 与端口约定
