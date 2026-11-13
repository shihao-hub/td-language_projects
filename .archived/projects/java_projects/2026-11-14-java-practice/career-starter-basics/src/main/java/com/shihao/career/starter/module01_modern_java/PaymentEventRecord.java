package com.shihao.career.starter.module01_modern_java;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * <h2>知识点一：不可变事件流水载体（Java 16+ Record）</h2>
 * 
 * <h3>【为什么初学者必须掌握？】</h3>
 * 在老版本 Java 中，定义一个数据载体（POJO/DTO）需要手写几十行 getter、setter、equals、hashCode、toString，
 * 或者依赖 Lombok 插件。
 * 而在现代 Java（16+，简历项目使用的 Java 17/21）中，引入了 {@code record} 关键字。
 * 
 * <h3>【对标简历实战场景】</h3>
 * 对应《收银中台》中各渠道（OXXO、Pix、SPEI）推送的不可变支付流水事件，
 * 金融对账场景要求“流水一旦产生不可被篡改”，Record 天生具备浅不可变性（final），是领域事件传递的绝佳容器。
 *
 * @param eventId       全局事件唯一 ID
 * @param orderId       业务订单号
 * @param channel       支付渠道（例如 PIX、OXXO、SPEI）
 * @param amount        交易金额
 * @param currency      币种（例如 BRL-巴西雷亚尔, MXN-墨西哥比索）
 * @param occurredAt    事件发生时间戳（UTC 时间）
 */
public record PaymentEventRecord(
        String eventId,
        String orderId,
        String channel,
        BigDecimal amount,
        String currency,
        Instant occurredAt
) {
    /**
     * 紧凑型构造函数校验（Compact Constructor）：
     * 在对象创建的唯一入口做业务合法性断言，杜绝脏数据流入下游。
     */
    public PaymentEventRecord {
        if (orderId == null || orderId.isBlank()) {
            throw new IllegalArgumentException("订单号 [orderId] 不能为空");
        }
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("交易金额 [amount] 必须大于零");
        }
        if (occurredAt == null) {
            occurredAt = Instant.now();
        }
    }
}
