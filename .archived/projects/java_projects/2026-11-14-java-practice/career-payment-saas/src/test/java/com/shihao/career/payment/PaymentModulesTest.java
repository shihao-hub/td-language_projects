package com.shihao.career.payment;

import com.shihao.career.payment.channel.DynamicPaymentRouter;
import com.shihao.career.payment.ledger.SettlementLedgerEngine;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
public class PaymentModulesTest {

    @Test
    @DisplayName("测试支付通道加权动态路由决策")
    void testDynamicChannelRouting() {
        DynamicPaymentRouter router = new DynamicPaymentRouter();
        router.updateChannelMetric(new DynamicPaymentRouter.ChannelMetric("CHANNEL_A", 0.98, 100, 10));
        router.updateChannelMetric(new DynamicPaymentRouter.ChannelMetric("CHANNEL_B", 0.90, 800, 5));
        router.updateChannelMetric(new DynamicPaymentRouter.ChannelMetric("CHANNEL_BROKEN", 0.40, 2000, 0));

        DynamicPaymentRouter.ChannelMetric best = router.selectBestChannel(List.of("CHANNEL_A", "CHANNEL_B", "CHANNEL_BROKEN"));
        assertEquals("CHANNEL_A", best.channelCode(), "高成功率、低延迟通道应被优先选中");

        // 测试全熔断保护
        assertThrows(IllegalStateException.class, () -> {
            router.selectBestChannel(List.of("CHANNEL_BROKEN"));
        });
    }

    @Test
    @DisplayName("测试金融清结算与复式记账平衡")
    void testSettlementLedgerBalance() {
        SettlementLedgerEngine engine = new SettlementLedgerEngine();
        SettlementLedgerEngine.SettlementBill bill = new SettlementLedgerEngine.SettlementBill(
                "ORD_TEST_999",
                "MCH_001",
                new BigDecimal("100.00"),
                new BigDecimal("0.10"), // 平台 10%
                new BigDecimal("0.05"), // 税 5%
                new BigDecimal("15.00"), // 运费 15
                Instant.now()
        );

        SettlementLedgerEngine.LedgerTrialBalance balance = engine.computeAndBalance(bill);

        // 验证计算：100 - 10 - 5 - 15 = 70 (BigDecimal 数值相等使用 compareTo)
        assertEquals(0, new BigDecimal("70.00").compareTo(balance.merchantNetAmount()));
        assertEquals(0, new BigDecimal("10.00").compareTo(balance.platformFeeAmount()));
        assertEquals(0, new BigDecimal("5.00").compareTo(balance.taxAmount()));
        assertTrue(balance.isBalanced(), "复式记账借贷总额必须严格平衡！");
    }
}
