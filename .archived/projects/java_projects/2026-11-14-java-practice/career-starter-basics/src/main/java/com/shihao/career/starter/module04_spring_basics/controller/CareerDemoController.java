package com.shihao.career.starter.module04_spring_basics.controller;

import com.shihao.career.starter.module01_modern_java.PaymentEventRecord;
import com.shihao.career.starter.module01_modern_java.ReconciliationStreamDemo;
import com.shihao.career.starter.module02_concurrent_basics.AgingPayTask;
import com.shihao.career.starter.module02_concurrent_basics.DynamicAgingScheduler;
import com.shihao.career.starter.module04_spring_basics.DynamicStateMachineEngine;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * <h2>对外暴露的轻量 REST 控制器</h2>
 * 方便学习者启动应用后，直接在浏览器或 Postman/curl 中直观观察核心业务运行结果。
 */
@RestController
@RequestMapping("/api/demo")
public class CareerDemoController {

    private final DynamicStateMachineEngine stateMachineEngine;

    public CareerDemoController(DynamicStateMachineEngine stateMachineEngine) {
        this.stateMachineEngine = stateMachineEngine;
    }

    /**
     * 健康检查与学习路线概览
     */
    @GetMapping("/health")
    public Map<String, Object> healthCheck() {
        return Map.of(
                "status", "UP",
                "project", "01-career-starter-basics",
                "description", "大厂 Java 后端与 Agent 工程师起步基础：从初学者到滴滴实战架构复刻",
                "modules", List.of(
                        "1. Java 16+ Record 不可变流水载体 & Sealed 密封接口",
                        "2. Stream API 金融交易过滤、分组与汇总统计",
                        "3. PriorityQueue 优先队列与 Aging 动态老化防饥饿调度算法",
                        "4. 策略模式解耦与 Spring ApplicationContext 动态 Bean 配置化状态机"
                )
        );
    }

    /**
     * 体验 Spring 动态状态机流转：
     * 访问示例：/api/demo/state-machine/trigger?orderId=DIDI_MEX_888&currentStatus=WAIT_ACCEPT&event=PAY_SUCCESS
     */
    @GetMapping("/state-machine/trigger")
    public DynamicStateMachineEngine.TransitionResult triggerStateMachine(
            @RequestParam(defaultValue = "DIDI_FOOD_1001") String orderId,
            @RequestParam(defaultValue = "WAIT_ACCEPT") String currentStatus,
            @RequestParam(defaultValue = "PAY_SUCCESS") String event
    ) {
        return stateMachineEngine.fireEvent(orderId, currentStatus, event);
    }

    /**
     * 体验 Aging 动态老化防饥饿调度算法：
     * 观察 P2 级普通任务在等待若干秒后，如何通过老化分反超刚进来的 P0 级任务！
     */
    @GetMapping("/aging-queue/simulate")
    public Map<String, Object> simulateAgingQueue() {
        DynamicAgingScheduler scheduler = new DynamicAgingScheduler();
        long now = System.currentTimeMillis();

        // 创建两个任务：
        // 任务 A：P2 普通用户支付通知（初始优先级 10 分，但入队时间是 5 秒前，已等待 5000 毫秒）
        AgingPayTask p2OldTask = new AgingPayTask("TASK_P2_USER_NOTIFY", "普通外卖支付通知", 10, now - 5000);

        // 任务 B：P0 大额风控拦截（初始优先级 100 分，刚刚入队 0 毫秒）
        AgingPayTask p0NewTask = new AgingPayTask("TASK_P0_RISK_INTERCEPT", "大额异常转账风控", 100, now);

        // 在当前时刻评估执行顺序
        List<AgingPayTask> scheduleResult = scheduler.scheduleTasks(List.of(p2OldTask, p0NewTask), now);

        double p2EffectiveScore = scheduler.calculateEffectivePriority(p2OldTask, now);
        double p0EffectiveScore = scheduler.calculateEffectivePriority(p0NewTask, now);

        return Map.of(
                "explanation", "P2 任务等待了 5 秒，获得 5 * 50 = 250 分老化加权，总分 260，成功反超初始 100 分的 P0 任务优先出队！",
                "p2TaskScore", p2EffectiveScore,
                "p0TaskScore", p0EffectiveScore,
                "actualExecutionOrder", scheduleResult.stream().map(AgingPayTask::getTaskName).toList()
        );
    }

    /**
     * 体验 Stream API 对账流水汇总
     */
    @GetMapping("/stream-reconciliation")
    public Map<String, Object> testStreamReconciliation() {
        ReconciliationStreamDemo demo = new ReconciliationStreamDemo();

        List<PaymentEventRecord> mockEvents = List.of(
                new PaymentEventRecord("E01", "ORD_001", "PIX", new BigDecimal("120.50"), "BRL", Instant.now()),
                new PaymentEventRecord("E02", "ORD_002", "PIX", new BigDecimal("80.00"), "BRL", Instant.now()),
                new PaymentEventRecord("E03", "ORD_003", "OXXO", new BigDecimal("350.00"), "MXN", Instant.now()),
                new PaymentEventRecord("E04", "ORD_004", "SPEI", new BigDecimal("500.00"), "MXN", Instant.now())
        );

        return Map.of(
                "totalBrlEvents", demo.filterByCurrency(mockEvents, "BRL").size(),
                "channelCounts", demo.countTransactionsByChannel(mockEvents),
                "totalAmount", demo.calculateTotalAmount(mockEvents),
                "distinctOrders", demo.extractDistinctOrderIds(mockEvents)
        );
    }
}
