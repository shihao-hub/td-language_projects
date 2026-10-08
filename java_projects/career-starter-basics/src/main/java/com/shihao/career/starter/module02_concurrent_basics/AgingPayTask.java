package com.shihao.career.starter.module02_concurrent_basics;

/**
 * <h2>并发调度任务载体：支付回调与风控通知</h2>
 *
 * <h3>【对标简历实战场景】</h3>
 * 对应《收银中台》第 4 点：
 * <ul>
 *   <li>P0 级任务：大额风控拦截、盗刷核验，时延要求极高（通常 &lt; 50ms）；</li>
 *   <li>P2 级任务：普通外卖用户订单支付成功通知，容忍秒级延迟。</li>
 * </ul>
 */
public class AgingPayTask {

    private final String taskId;
    private final String taskName;
    
    /**
     * 初始优先级权重数值（数值越大代表优先级越高）
     * 示例：P0 级初始分为 100，P2 级初始分为 10
     */
    private final int initialPriority;

    /**
     * 任务入队时间戳（毫秒）
     */
    private final long enqueuedTimestampMs;

    public AgingPayTask(String taskId, String taskName, int initialPriority, long enqueuedTimestampMs) {
        this.taskId = taskId;
        this.taskName = taskName;
        this.initialPriority = initialPriority;
        this.enqueuedTimestampMs = enqueuedTimestampMs;
    }

    public String getTaskId() {
        return taskId;
    }

    public String getTaskName() {
        return taskName;
    }

    public int getInitialPriority() {
        return initialPriority;
    }

    public long getEnqueuedTimestampMs() {
        return enqueuedTimestampMs;
    }

    @Override
    public String toString() {
        return String.format("[%s] %s (初始分:%d, 入队时间:%d)", taskId, taskName, initialPriority, enqueuedTimestampMs);
    }
}
