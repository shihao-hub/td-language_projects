package com.shihao.career.starter.module04_spring_basics.action;

/**
 * <h2>状态机流转后置动作契约接口</h2>
 */
public interface OrderAction {
    /**
     * 执行具体动作
     * @param orderId 关联订单号
     * @return 执行日志或结果描述
     */
    String execute(String orderId);
}
