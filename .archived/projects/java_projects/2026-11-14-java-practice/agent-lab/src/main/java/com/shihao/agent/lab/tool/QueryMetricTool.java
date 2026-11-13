package com.shihao.agent.lab.tool;

import com.fasterxml.jackson.databind.JsonNode;
import com.shihao.agent.lab.agent.Tool;
import com.shihao.agent.lab.agent.ToolResult;
import com.shihao.agent.lab.telemetry.MetricPoint;
import com.shihao.agent.lab.telemetry.MetricSeries;
import com.shihao.agent.lab.telemetry.TelemetryRepository;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Optional;
import java.util.StringJoiner;

/**
 * 指标查询工具：只负责取数与聚合，不做任何根因判断。
 */
public class QueryMetricTool implements Tool {

    private static final DateTimeFormatter TIME_FORMAT =
            DateTimeFormatter.ofPattern("HH:mm:ss'Z'").withZone(ZoneOffset.UTC);

    private final TelemetryRepository repository;

    public QueryMetricTool(TelemetryRepository repository) {
        this.repository = repository;
    }

    @Override
    public String name() {
        return "query_metric";
    }

    @Override
    public String description() {
        return "查询指定场景的时间序列指标，返回窗口内的最小值/均值/最大值/最新值与采样点";
    }

    @Override
    public String inputSchema() {
        return "{\"scenarioId\":\"场景ID\",\"metric\":\"指标名\",\"window\":\"可选，如 5m 或 10m，默认 10m\"}";
    }

    @Override
    public ToolResult execute(JsonNode input) {
        String scenarioId = text(input, "scenarioId");
        String metric = text(input, "metric");
        if (scenarioId.isEmpty()) {
            return ToolResult.fail("缺少参数 scenarioId");
        }
        if (metric.isEmpty()) {
            return ToolResult.fail("缺少参数 metric");
        }
        if (!repository.scenarioExists(scenarioId)) {
            return ToolResult.fail("场景不存在: " + scenarioId);
        }

        Optional<MetricSeries> series = repository.queryMetric(scenarioId, metric);
        if (series.isEmpty()) {
            return ToolResult.fail("指标不存在: " + metric + "，可用指标: "
                    + String.join(", ", repository.metricNames(scenarioId)));
        }

        int windowMinutes = parseWindowMinutes(text(input, "window"));
        return ToolResult.ok(format(series.get(), windowMinutes));
    }

    private String format(MetricSeries series, int windowMinutes) {
        List<MetricPoint> points = series.points();
        int wanted = Math.max(1, windowMinutes * 60 / Math.max(1, series.intervalSeconds()));
        int from = Math.max(0, points.size() - wanted);
        List<MetricPoint> window = points.subList(from, points.size());

        double min = Double.MAX_VALUE;
        double max = -Double.MAX_VALUE;
        double sum = 0;
        for (MetricPoint point : window) {
            min = Math.min(min, point.value());
            max = Math.max(max, point.value());
            sum += point.value();
        }
        double avg = sum / window.size();
        double last = window.get(window.size() - 1).value();

        StringJoiner joiner = new StringJoiner("\n");
        joiner.add("指标 " + series.metric() + "（单位 " + series.unit() + "）");
        joiner.add("场景 " + series.scenarioId());
        joiner.add("窗口 最近 " + windowMinutes + " 分钟，共 " + window.size()
                + " 个采样点，间隔 " + series.intervalSeconds() + " 秒");
        joiner.add("时间范围 " + TIME_FORMAT.format(Instant.ofEpochSecond(window.get(0).epochSeconds()))
                + " ~ " + TIME_FORMAT.format(Instant.ofEpochSecond(window.get(window.size() - 1).epochSeconds())));
        joiner.add("min=" + fmt(min) + " avg=" + fmt(avg) + " max=" + fmt(max) + " last=" + fmt(last));
        joiner.add("采样点:");
        for (MetricPoint point : window) {
            joiner.add("  " + TIME_FORMAT.format(Instant.ofEpochSecond(point.epochSeconds()))
                    + "  " + fmt(point.value()));
        }
        return joiner.toString();
    }

    private static String fmt(double value) {
        return String.format("%.4f", value);
    }

    private static String text(JsonNode input, String field) {
        JsonNode node = input.get(field);
        return node == null || node.isNull() ? "" : node.asText().trim();
    }

    private static int parseWindowMinutes(String window) {
        if (window == null || window.isBlank()) {
            return 10;
        }
        String normalized = window.trim().toLowerCase();
        try {
            if (normalized.endsWith("m")) {
                return Integer.parseInt(normalized.substring(0, normalized.length() - 1));
            }
            return Integer.parseInt(normalized);
        } catch (NumberFormatException e) {
            return 10;
        }
    }
}
