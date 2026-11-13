package com.shihao.career.payment.controller;

import com.shihao.career.payment.channel.DynamicPaymentRouter;
import com.shihao.career.payment.ledger.SettlementLedgerEngine;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/payment")
public class PaymentDemoController {

    private final DynamicPaymentRouter router = new DynamicPaymentRouter();
    private final SettlementLedgerEngine ledger = new SettlementLedgerEngine();

    public PaymentDemoController() {
        // 初始化两个拉美本地支付通道数据
        router.updateChannelMetric(new DynamicPaymentRouter.ChannelMetric("PIX_BRAZIL", 0.99, 120, 10));
        router.updateChannelMetric(new DynamicPaymentRouter.ChannelMetric("SPEI_MEXICO", 0.95, 350, 5));
        router.updateChannelMetric(new DynamicPaymentRouter.ChannelMetric("OXXO_CASH", 0.75, 800, 0));
    }

    @GetMapping("/route-best")
    public DynamicPaymentRouter.ChannelMetric routeBestChannel() {
        return router.selectBestChannel(List.of("PIX_BRAZIL", "SPEI_MEXICO", "OXXO_CASH"));
    }

    @GetMapping("/settle-order")
    public SettlementLedgerEngine.LedgerTrialBalance settleOrder(
            @RequestParam(defaultValue = "ORD_MEX_202610") String orderId,
            @RequestParam(defaultValue = "200.00") BigDecimal amount
    ) {
        SettlementLedgerEngine.SettlementBill bill = new SettlementLedgerEngine.SettlementBill(
                orderId,
                "MCH_TACOS_888",
                amount,
                new BigDecimal("0.15"), // 15% 抽成
                new BigDecimal("0.05"), // 5% 税
                new BigDecimal("20.00"), // 20 运费
                Instant.now()
        );
        return ledger.computeAndBalance(bill);
    }
}
