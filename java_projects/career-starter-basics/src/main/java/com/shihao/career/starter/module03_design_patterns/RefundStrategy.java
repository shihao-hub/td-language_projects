package com.shihao.career.starter.module03_design_patterns;

/**
 * <h2>知识点五：策略模式（Strategy Pattern）契约接口</h2>
 *
 * <h3>【为什么初学者必须掌握？】</h3>
 * 刚毕业的同学最容易写出的“坏味道”代码是：
 * <pre>
 *   if ("BALANCE".equals(type)) {
 *       // 50 行退余额代码
 *   } else if ("BANK_CARD".equals(type)) {
 *       // 60 行退银行卡代码
 *   } else if ("OXXO_CASH".equals(type)) { ... }
 * </pre>
 * 这样写会导致类变得几十上百行，任何一个渠道退款改动都会破坏其他渠道，违反“单一职责”与“开闭原则”。
 * 策略模式将具体的执行动作抽象成独立实现类，实现业务彻底解耦。
 *
 * <h3>【对标简历实战场景】</h3>
 * 对应《收银中台》第 3 点：不同支付方式差异极大的退款退差流转。
 */
public interface RefundStrategy {

    /** 策略标识编码（如 BALANCE, BANK_CARD） */
    String getChannelCode();

    /** 执行具体退款操作 */
    String executeRefund(RefundContext context);
}
