package com.shihao.career.starter;

import com.shihao.career.starter.module01_modern_java.Java21FeaturesDemo;
import com.shihao.career.starter.module01_modern_java.OrderStatus;
import com.shihao.career.starter.module01_modern_java.PaymentEventRecord;
import com.shihao.career.starter.module01_modern_java.ReconciliationStreamDemo;
import com.shihao.career.starter.module02_concurrent_basics.AgingPayTask;
import com.shihao.career.starter.module02_concurrent_basics.DynamicAgingScheduler;
import com.shihao.career.starter.module02_concurrent_basics.VirtualThreadsDemo;
import com.shihao.career.starter.module03_design_patterns.BalanceRefundAction;
import com.shihao.career.starter.module03_design_patterns.BankCardRefundAction;
import com.shihao.career.starter.module03_design_patterns.RefundContext;
import com.shihao.career.starter.module03_design_patterns.SimpleRefundDispatcher;
import com.shihao.career.starter.module04_spring_basics.DynamicStateMachineEngine;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
public class StarterAllModulesTest {

    @Autowired
    private DynamicStateMachineEngine stateMachineEngine;

    @Test
    @DisplayName("测试 Java 21：Record 不可变性与模式解构")
    void testRecordAndJava21PatternMatching() {
        PaymentEventRecord record = new PaymentEventRecord(
                "EVT_001", "ORD_888", "PIX", new BigDecimal("199.99"), "BRL", Instant.now()
        );

        assertEquals("ORD_888", record.orderId());
        assertEquals(new BigDecimal("199.99"), record.amount());

        // Java 21 Record Pattern 解构测试
        Java21FeaturesDemo j21Demo = new Java21FeaturesDemo();
        String deconstructResult = j21Demo.resolveEventWithPatternMatching(record);
        assertTrue(deconstructResult.contains("ORD_888"));
        assertTrue(deconstructResult.contains("PIX"));
    }

    @Test
    @DisplayName("测试 Java 21：有序集合 Sequenced Collections (getFirst / getLast / reversed)")
    void testSequencedCollections() {
        Java21FeaturesDemo j21Demo = new Java21FeaturesDemo();
        List<String> logs = List.of("1. 用户发起支付", "2. 渠道扣款成功", "3. 账本复式记账完成");

        String result = j21Demo.inspectSequencedAuditLog(logs);
        assertTrue(result.contains("最早动作: [1. 用户发起支付]"));
        assertTrue(result.contains("最新动作: [3. 账本复式记账完成]"));
        assertTrue(result.contains("逆序首项: [3. 账本复式记账完成]"));
    }

    @Test
    @DisplayName("测试 Java 21：虚拟线程（Virtual Threads）高并发与轻量调度")
    void testVirtualThreads() throws InterruptedException {
        VirtualThreadsDemo vtDemo = new VirtualThreadsDemo();

        // 1. 单条虚拟线程测试
        String singleResult = vtDemo.runSingleVirtualThread("PROBE_CHANNEL_PIX");
        assertTrue(singleResult.contains("isVirtual = true"));

        // 2. 批量 50 个高并发轻量虚拟线程测试
        int finished = vtDemo.executeConcurrentTasksWithVirtualThreads(50);
        assertEquals(50, finished, "所有高并发虚拟线程应当无阻塞全部执行完毕");
    }

    @Test
    @DisplayName("测试模块一：密封类与模式匹配流转")
    void testSealedOrderStatus() {
        OrderStatus status = new OrderStatus.PaymentFailed("CHANNEL_TIMEOUT", "拉美本地网银响应超时");

        String resolution = switch (status) {
            case OrderStatus.PendingPayment pending -> "等待支付中，剩余秒数: " + pending.expireSeconds();
            case OrderStatus.PaymentSuccess success -> "支付成功，渠道流水: " + success.channelTradeNo();
            case OrderStatus.PaymentFailed failed -> "支付失败报警: " + failed.errorMessage();
            case OrderStatus.Refunded refunded -> "已退款: " + refunded.refundTicketId();
        };

        assertTrue(resolution.contains("支付失败报警"));
    }

    @Test
    @DisplayName("测试模块一：Stream API 金融交易过滤与统计")
    void testStreamReconciliation() {
        ReconciliationStreamDemo demo = new ReconciliationStreamDemo();

        List<PaymentEventRecord> events = List.of(
                new PaymentEventRecord("E1", "ORD_01", "PIX", new BigDecimal("100"), "BRL", Instant.now()),
                new PaymentEventRecord("E2", "ORD_02", "PIX", new BigDecimal("200"), "BRL", Instant.now()),
                new PaymentEventRecord("E3", "ORD_03", "OXXO", new BigDecimal("300"), "MXN", Instant.now())
        );

        List<PaymentEventRecord> brlEvents = demo.filterByCurrency(events, "BRL");
        assertEquals(2, brlEvents.size());

        BigDecimal total = demo.calculateTotalAmount(events);
        assertEquals(new BigDecimal("600"), total);

        Map<String, Long> channelCount = demo.countTransactionsByChannel(events);
        assertEquals(2L, channelCount.get("PIX"));
        assertEquals(1L, channelCount.get("OXXO"));
    }

    @Test
    @DisplayName("测试模块二：Dynamic Aging 动态老化算法解决低优先级任务饥饿")
    void testDynamicAgingScheduler() {
        DynamicAgingScheduler scheduler = new DynamicAgingScheduler();
        long now = 1000000L;

        // 任务 A：P2 普通任务，初始分 10，已等待 10 秒（10000ms）
        AgingPayTask p2OldTask = new AgingPayTask("P2_TASK", "普通出餐通知", 10, now - 10000L);

        // 任务 B：P0 紧急任务，初始分 100，刚刚入队（等待 0ms）
        AgingPayTask p0NewTask = new AgingPayTask("P0_TASK", "大额风控拦截", 100, now);

        double p2Score = scheduler.calculateEffectivePriority(p2OldTask, now);
        double p0Score = scheduler.calculateEffectivePriority(p0NewTask, now);

        assertTrue(p2Score > p0Score, "P2 任务在经历充分等待后，有效优先级应成功反超 P0 任务");

        List<AgingPayTask> scheduleResult = scheduler.scheduleTasks(List.of(p0NewTask, p2OldTask), now);
        assertEquals("P2_TASK", scheduleResult.get(0).getTaskId(), "队列首位弹出的应当是获得老化提权的 P2 任务！");
    }

    @Test
    @DisplayName("测试模块三：策略模式消解 if-else")
    void testStrategyPattern() {
        SimpleRefundDispatcher dispatcher = new SimpleRefundDispatcher(List.of(
                new BalanceRefundAction(),
                new BankCardRefundAction()
        ));

        RefundContext ctx = new RefundContext("ORD_999", "REF_001", new BigDecimal("50.00"), "user_abc@didi.com");

        String balanceResult = dispatcher.dispatch("BALANCE", ctx);
        assertTrue(balanceResult.contains("钱包账户:user_abc@didi.com"));

        String bankResult = dispatcher.dispatch("BANK_CARD", ctx);
        assertTrue(bankResult.contains("银行卡原路退款已提交"));
    }

    @Test
    @DisplayName("测试模块四：Spring IoC 容器与动态 Bean 状态机流转")
    void testSpringDynamicStateMachine() {
        DynamicStateMachineEngine.TransitionResult r1 = stateMachineEngine.fireEvent(
                "DIDI_MEX_101", "WAIT_ACCEPT", "PAY_SUCCESS"
        );
        assertEquals("PREPARING", r1.toStatus());
        assertEquals("NOTIFY_MERCHANT", r1.executedActionBean());
        assertTrue(r1.executionDetail().contains("商家已接收订单推送"));

        DynamicStateMachineEngine.TransitionResult r2 = stateMachineEngine.fireEvent(
                "DIDI_MEX_101", "PREPARING", "MEAL_READY"
        );
        assertEquals("DELIVERING", r2.toStatus());
        assertEquals("DISPATCH_RIDER", r2.executedActionBean());
        assertTrue(r2.executionDetail().contains("计算商家周围 3 公里最优配送骑手"));

        assertThrows(IllegalStateException.class, () -> {
            stateMachineEngine.fireEvent("DIDI_MEX_101", "DELIVERING", "PAY_SUCCESS");
        });
    }
}
