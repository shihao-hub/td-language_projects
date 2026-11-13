package com.shihao.career.starter.module04_spring_basics.action;

import org.springframework.stereotype.Component;

/**
 * 动作二：向骑手运力中心发起派单调度
 */
@Component("DISPATCH_RIDER")
public class DispatchRiderAction implements OrderAction {
    @Override
    public String execute(String orderId) {
        return String.format("[骑手派单动作已触发] 订单号: %s, 正在计算商家周围 3 公里最优配送骑手", orderId);
    }
}
