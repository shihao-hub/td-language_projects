package com.shihao.career.starter.module03_design_patterns;

public class BankCardRefundAction implements RefundStrategy {
    @Override
    public String getChannelCode() {
        return "BANK_CARD";
    }

    @Override
    public String executeRefund(RefundContext context) {
        return String.format("[银行卡原路退款已提交] 订单:%s, 申请退还:¥%s, 预计1-3个工作日入账",
                context.orderId(), context.refundAmount());
    }
}
