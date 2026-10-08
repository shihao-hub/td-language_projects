package com.shihao.career.starter.module01_modern_java;

/**
 * <h2>知识点二：密封接口（Sealed Interface）与有限状态枚举进阶</h2>
 *
 * <h3>【为什么初学者必须掌握？】</h3>
 * 传统的状态通常用简单枚举 {@code enum} 表示，但枚举无法携带差异化的上下文数据
 * （例如：失败状态需要携带错误码与排障信息，成功状态需要携带到账流水号）。
 * Java 17 引入的 {@code sealed} 接口允许我们严格限制哪些类可以实现它，
 * 配合现代 {@code switch} 模式匹配，编译器会在编译期强制检查是否处理了所有可能的状态分支，杜绝遗漏！
 *
 * <h3>【对标简历实战场景】</h3>
 * 对应《智能客服》中的多轮意图状态机与《收银中台》中订单生命周期流转。
 */
public sealed interface OrderStatus permits 
        OrderStatus.PendingPayment, 
        OrderStatus.PaymentSuccess, 
        OrderStatus.PaymentFailed, 
        OrderStatus.Refunded {

    /** 待支付状态 */
    record PendingPayment(long expireSeconds) implements OrderStatus {}

    /** 支付成功状态（携带支付网关返回的渠道流水号） */
    record PaymentSuccess(String channelTradeNo, long successTimestamp) implements OrderStatus {}

    /** 支付失败状态（携带具体错误码与渠道报错，用于智能客服或诊断 Agent 介入） */
    record PaymentFailed(String errorCode, String errorMessage) implements OrderStatus {}

    /** 已全额退款状态 */
    record Refunded(String refundTicketId) implements OrderStatus {}
}
