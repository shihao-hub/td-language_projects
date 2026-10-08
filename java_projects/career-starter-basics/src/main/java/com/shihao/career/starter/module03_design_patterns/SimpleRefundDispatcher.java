package com.shihao.career.starter.module03_design_patterns;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * <h2>策略注册分发器（消灭 if-else 的核心）</h2>
 *
 * <h3>【工作原理】</h3>
 * 在系统启动时，将所有策略实现类按“渠道编码”放入 Map 注册表中。
 * 运行时来了一个退款请求，直接 {@code map.get(channel)} 命中对应逻辑，
 * 时间复杂度从 O(N) 逐条 if-else 判断降低为 O(1) 哈希直达，代码干脆利落。
 */
public class SimpleRefundDispatcher {

    private final Map<String, RefundStrategy> strategyMap = new HashMap<>();

    public SimpleRefundDispatcher(List<RefundStrategy> strategies) {
        for (RefundStrategy s : strategies) {
            strategyMap.put(s.getChannelCode().toUpperCase(), s);
        }
    }

    public String dispatch(String channel, RefundContext context) {
        if (channel == null) {
            throw new IllegalArgumentException("支付渠道不能为空");
        }
        RefundStrategy strategy = strategyMap.get(channel.toUpperCase());
        if (strategy == null) {
            throw new UnsupportedOperationException("未找到支持的退款处理渠道: " + channel);
        }
        return strategy.executeRefund(context);
    }
}
