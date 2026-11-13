package com.shihao.career.payment.ledger;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * <h2>金融清结算与复式记账核心模型</h2>
 * 满足借贷平衡原则：有借必有贷，借贷必相等。
 * 覆盖：商户订单实收、平台抽佣、增值税扣缴、骑手配送费清分。
 */
public class SettlementLedgerEngine {

    public enum EntryType {
        DEBIT,  // 借方 (资产增加 / 费用发生)
        CREDIT  // 贷方 (负债增加 / 收入确认)
    }

    public record JournalEntry(
            String accountNo,
            EntryType type,
            BigDecimal amount,
            String memo
    ) {}

    public record SettlementBill(
            String orderId,
            String merchantId,
            BigDecimal totalGrossAmount, // 订单总交易额
            BigDecimal platformCommissionRate, // 平台抽成比率 (如 0.15)
            BigDecimal taxRate, // 增值税比率 (如 0.05)
            BigDecimal deliveryFee, // 骑手运费
            Instant settledAt
    ) {}

    
    public record LedgerTrialBalance(
            String orderId,
            BigDecimal merchantNetAmount,
            BigDecimal platformFeeAmount,
            BigDecimal taxAmount,
            BigDecimal riderDeliveryAmount,
            List<JournalEntry> entries,
            boolean isBalanced
    ) {}

    /**
     * 计算账单并生成复式记账明细
     */
    public LedgerTrialBalance computeAndBalance(SettlementBill bill) {
        BigDecimal gross = bill.totalGrossAmount();
        BigDecimal platformFee = gross.multiply(bill.platformCommissionRate());
        BigDecimal tax = gross.multiply(bill.taxRate());
        BigDecimal delivery = bill.deliveryFee();

        // 商户最终到手 = 交易额 - 平台抽成 - 增值税 - 配送费
        BigDecimal merchantNet = gross.subtract(platformFee).subtract(tax).subtract(delivery);

        // 记账流水：
        // 借：银行应收清算款 (借方增加资产)
        // 贷：应付商户款、应付平台佣金收入、应交税费、应付骑手款
        List<JournalEntry> entries = List.of(
                new JournalEntry("1002_BANK_CLEARING", EntryType.DEBIT, gross, "银行渠道清算到账"),
                new JournalEntry("2001_PAYABLE_MERCHANT", EntryType.CREDIT, merchantNet, "应付商户结算净额"),
                new JournalEntry("6001_PLATFORM_REVENUE", EntryType.CREDIT, platformFee, "平台技术服务抽成"),
                new JournalEntry("2221_TAX_PAYABLE", EntryType.CREDIT, tax, "代扣增值税金"),
                new JournalEntry("2003_PAYABLE_RIDER", EntryType.CREDIT, delivery, "骑手履约配送运费")
        );

        BigDecimal totalDebit = entries.stream()
                .filter(e -> e.type() == EntryType.DEBIT)
                .map(JournalEntry::amount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal totalCredit = entries.stream()
                .filter(e -> e.type() == EntryType.CREDIT)
                .map(JournalEntry::amount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        boolean balanced = totalDebit.compareTo(totalCredit) == 0;

        return new LedgerTrialBalance(
                bill.orderId(),
                merchantNet,
                platformFee,
                tax,
                delivery,
                entries,
                balanced
        );
    }
}
