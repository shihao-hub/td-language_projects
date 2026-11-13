package com.shihao.agent.lab.telemetry;

import java.util.List;
import java.util.Optional;

/**
 * 数据接缝：工具层只依赖本接口，文件实现与未来的 Prometheus/ES 实现可互换。
 */
public interface TelemetryRepository {

    boolean scenarioExists(String scenarioId);

    List<String> metricNames(String scenarioId);

    Optional<MetricSeries> queryMetric(String scenarioId, String metric);
}
