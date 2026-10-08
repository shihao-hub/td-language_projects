package com.shihao.career.starter.module02_concurrent_basics;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.PriorityQueue;

/**
 * <h2>知识点四：优先队列（PriorityQueue）与动态老化调度算法（Aging Algorithm）</h2>
 *
 * <h3>【为什么初学者必须掌握？】</h3>
 * 1. 很多刚写 Java 的同学在处理多任务消费时，只会用最普通的 {@code LinkedList} 或 FIFO 队列，不知道还有“按权重自动堆排序”的优先队列；<br>
 * 2. 即使知道了优先队列，也容易踩入“静态优先级死锁/饥饿”的大坑：大促高峰期高优先级任务（P0）源源不断涌入，
 * 导致低优先级任务（P2）在队尾永远轮不到执行，被活活“饿死”，引发海量客诉！
 *
 * <h3>【对标简历核心技术亮点】</h3>
 * 对应《收银中台》第 4 点：重写 PriorityBlockingQueue 的比较器 Comparator，
 * 融入任务等待时长系数：
 * <pre>
 *   有效动态优先级 = 初始优先级 + (当前时间 - 入队时间) / 增益因子
 * </pre>
 * 当普通任务等待超过阈值时，有效权重随时间“自然老化升权”，最终反超新入队的 P0 任务强制插队执行，
 * 彻底消除低优任务饥饿假死！
 */
public class DynamicAgingScheduler {

    /**
     * 老化增益步长（毫秒）：每等待多少毫秒，优先级权重大幅度累加
     * 在本基础教学演示中，设定为 1000 毫秒（1秒）增加 50 分，便于测试观察
     */
    private static final long AGING_STEP_MS = 1000L;
    private static final double WEIGHT_PER_STEP = 50.0;

    /**
     * 计算某任务在指定时间点 {@code nowMs} 的“有效动态优先级”
     */
    public double calculateEffectivePriority(AgingPayTask task, long nowMs) {
        long waitTimeMs = Math.max(0, nowMs - task.getEnqueuedTimestampMs());
        double agingBonus = (waitTimeMs / (double) AGING_STEP_MS) * WEIGHT_PER_STEP;
        return task.getInitialPriority() + agingBonus;
    }

    /**
     * 核心比较器构建：
     * 构建一个大顶堆 Comparator，有效动态优先级更高的任务排在堆顶最先出队
     */
    public Comparator<AgingPayTask> createAgingComparator(long currentEvaluationTimeMs) {
        return (t1, t2) -> {
            double p1 = calculateEffectivePriority(t1, currentEvaluationTimeMs);
            double p2 = calculateEffectivePriority(t2, currentEvaluationTimeMs);
            // 降序排序（大顶堆：分高者排前）
            return Double.compare(p2, p1);
        };
    }

    /**
     * 模拟调度执行：
     * 给定一批任务列表和当前评估时间点，返回调度器依次弹出的执行顺序
     */
    public List<AgingPayTask> scheduleTasks(List<AgingPayTask> tasks, long currentEvaluationTimeMs) {
        PriorityQueue<AgingPayTask> pq = new PriorityQueue<>(createAgingComparator(currentEvaluationTimeMs));
        pq.addAll(tasks);

        List<AgingPayTask> executionOrder = new ArrayList<>();
        while (!pq.isEmpty()) {
            executionOrder.add(pq.poll());
        }
        return executionOrder;
    }
}
