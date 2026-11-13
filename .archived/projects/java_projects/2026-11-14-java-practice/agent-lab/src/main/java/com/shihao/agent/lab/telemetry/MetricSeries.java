package com.shihao.agent.lab.telemetry;

import java.util.List;

public record MetricSeries(
        String scenarioId,
        String metric,
        String unit,
        long startEpochSeconds,
        int intervalSeconds,
        List<MetricPoint> points
) {

    public MetricSeries {
        points = List.copyOf(points);
    }

    public int size() {
        return points.size();
    }
}
