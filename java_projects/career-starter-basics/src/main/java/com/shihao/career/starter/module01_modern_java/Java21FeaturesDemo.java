package com.shihao.career.starter.module01_modern_java;

import java.math.BigDecimal;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.List;

/**
 * <h2>知识点四：Java 21 现代化语法升级（Record 模式解构 + 有序集合 Sequenced Collections）</h2>
 *
 * <h3>【为什么初学者必须掌握？】</h3>
 * 1. <b>Record Patterns（JEP 440）</b>：在 switch 或 instanceof 中，直接将 Record 内部的属性拆解出来，
 * 无需先强转再调用 getter，代码精炼且类型安全；<br>
 * 2. <b>有序集合（JEP 431）</b>：Java 21 统一了 List、Deque、SortedSet 的首尾访问规范，
 * 终于有了统一的 {@code getFirst()}、{@code getLast()} 与 {@code reversed()} 反转视图，再也不用别扭地写 {@code get(size() - 1)}。
 */
public class Java21FeaturesDemo {

    /**
     * Java 21 Record 模式解构与类型匹配：
     * 针对订单状态与支付流水，直接解构内部成员变量！
    */
    public String resolveEventWithPatternMatching(PaymentEventRecord record) {
        // Java 21 Record Pattern：直接解构为 (eventId, orderId, channel, amount, currency, time)
        if (record instanceof PaymentEventRecord(var id, var orderId, var channel, var amount, var curr, var time)) {
            return String.format("解构成功 -> 订单号:%s, 渠道:%s, 金额:%s %s", orderId, channel, amount, curr);
        }
        return "未知事件";
    }

    /**
     * Java 21 Sequenced Collections（有序集合统一首尾访问）：
     * 在对账流水和重试日志中，快速抓取最新一条（尾部）和最早一条（首部）交易
     */
    public String inspectSequencedAuditLog(List<String> auditLogs) {
        if (auditLogs.isEmpty()) {
            return "日志为空";
        }
        // Java 21 直接提供 getFirst() 与 getLast()
        String earliest = auditLogs.getFirst();
        String latest = auditLogs.getLast();

        // 还可以直接生成反转视图（O(1) 逆序操作，无需 Collections.reverse 修改原集合）
        List<String> reversed = auditLogs.reversed();

        return String.format("最早动作: [%s], 最新动作: [%s], 逆序首项: [%s]", earliest, latest, reversed.getFirst());
    }
}
