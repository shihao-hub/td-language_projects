package com.shihao.career.starter.module03_design_patterns;

public class BalanceRefundAction implements RefundStrategy {
    @Override
    public String getChannelCode() {
        return "BALANCE";
    }

    @Override
    public String executeRefund(RefundContext context) {
        return String.format("[余额退款成功] 订单:%s, 退还金额:¥%s 到钱包账户:%s",
                context.orderId(), context.refundAmount(), context.userAccount());
    }
}
