package com.shihao.career.starter.module01_modern_java;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * <h2>知识点三：Java Stream API 核心操作与金融数据汇总</h2>
 *
 * <h3>【为什么初学者必须掌握？】</h3>
 * 刚毕业写 Java 的同学经常习惯写嵌套的 for 循环和 if 判断来处理列表数据，
 * 不仅代码行数多、逻辑分散，而且极易出现空指针或边界漏算。
 * Stream API 提供了声明式的数据流式处理能力（filter, map, collect, groupingBy, reduce）。
 *
 * <h3>【对标简历实战场景】</h3>
 * 对应《收银中台》中每日与银行账单核对、按支付渠道统计手续费、汇兑结算等核心对账逻辑。
 */
public class ReconciliationStreamDemo {

    /**
     * 1. 过滤：按指定币种筛选有效交易
     */
    public List<PaymentEventRecord> filterByCurrency(List<PaymentEventRecord> events, String targetCurrency) {
        return events.stream()
                .filter(event -> event.currency().equalsIgnoreCase(targetCurrency))
                .toList(); // Java 16+ 的精简写法，替代 .collect(Collectors.toList())
    }

    /**
     * 2. 分组统计（groupingBy）：按支付渠道统计各渠道的交易总笔数
     */
    public Map<String, Long> countTransactionsByChannel(List<PaymentEventRecord> events) {
        return events.stream()
                .collect(Collectors.groupingBy(
                        PaymentEventRecord::channel,
                        Collectors.counting()
                ));
    }

    /**
     * 3. 归约汇总（reduce / summing）：统计全量交易的总金额
     */
    public BigDecimal calculateTotalAmount(List<PaymentEventRecord> events) {
        return events.stream()
                .map(PaymentEventRecord::amount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /**
     * 4. 提取唯一直客订单号列表（map + distinct）
     */
    public List<String> extractDistinctOrderIds(List<PaymentEventRecord> events) {
        return events.stream()
                .map(PaymentEventRecord::orderId)
                .distinct()
                .sorted()
                .toList();
    }
}
