package com.shihao.career.starter.module04_spring_basics.action;

import org.springframework.stereotype.Component;

/**
 * 动作三：自动向支付渠道发起原路退款
 */
@Component("AUTO_REFUND")
public class AutoRefundAction implements OrderAction {
    @Override
    public String execute(String orderId) {
        return String.format("[自动退款动作已触发] 订单号: %s, 商家超时未接单，系统已发起全额退款冲正", orderId);
    }
}
