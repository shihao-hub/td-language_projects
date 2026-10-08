package com.shihao.career.starter.module04_spring_basics.action;

import org.springframework.stereotype.Component;

/**
 * 动作一：通知商家接单与出餐
 * 关键点：注意 @Component 指定的名字与数据库配置表中的编码一致
 */
@Component("NOTIFY_MERCHANT")
public class NotifyMerchantAction implements OrderAction {
    @Override
    public String execute(String orderId) {
        return String.format("[商家接单动作已触发] 订单号: %s, 商家已接收订单推送并进入备餐流程", orderId);
    }
}
