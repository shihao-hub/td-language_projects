package com.shihao.career.starter.module03_design_patterns;

import java.math.BigDecimal;

/**
 * <h2>退款业务上下文（Context）</h2>
 */
public record RefundContext(
        String orderId,
        String refundNo,
        BigDecimal refundAmount,
        String userAccount
) {}
