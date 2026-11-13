package com.shihao.career.payment.channel;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * <h2>支付通道动态路由决策引擎</h2>
 * 针对出海收单网络抖动与熔断，根据近期（窗口期）成功率与平均耗时动态算分加权选路。
 */
public class DynamicPaymentRouter {

    public record ChannelMetric(
            String channelCode,
            double successRate,
            long avgLatencyMs,
            int baseWeight
    ) {}

    private final Map<String, ChannelMetric> channelMetrics = new ConcurrentHashMap<>();

    public void updateChannelMetric(ChannelMetric metric) {
        channelMetrics.put(metric.channelCode(), metric);
    }

    /**
     * 计算综合评分：
     * score = successRate * 70 + (max(0, 1000 - latency) / 1000) * 30 + baseWeight
     */
    public double calculateRouteScore(ChannelMetric metric) {
        double latencyScore = Math.max(0.0, (1000.0 - metric.avgLatencyMs()) / 1000.0) * 30.0;
        double rateScore = metric.successRate() * 70.0;
        return rateScore + latencyScore + metric.baseWeight();
    }

    /**
     * 自动从多个通道中选出最高综合得分的最优通道
     */
    public ChannelMetric selectBestChannel(List<String> candidateChannels) {
        return candidateChannels.stream()
                .map(channelMetrics::get)
                .filter(m -> m != null && m.successRate() > 0.5) // 熔断低于 50% 的故障通道
                .max(Comparator.comparingDouble(this::calculateRouteScore))
                .orElseThrow(() -> new IllegalStateException("无可用健康支付通道！全部熔断或未配置"));
    }
}
