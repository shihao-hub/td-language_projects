package com.shihao.agent.lab.telemetry;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 从 classpath:/dataset/&lt;scenarioId&gt;/metrics.json 读取指标。
 * 文件是只读资产，运行时产生的数据一律走 APPDATA 目录。
 */
public class FileTelemetryRepository implements TelemetryRepository {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final String resourceRoot;
    private final Map<String, ScenarioMetrics> cache = new ConcurrentHashMap<>();

    public FileTelemetryRepository() {
        this("/dataset");
    }

    public FileTelemetryRepository(String resourceRoot) {
        this.resourceRoot = resourceRoot.endsWith("/")
                ? resourceRoot.substring(0, resourceRoot.length() - 1)
                : resourceRoot;
    }

    @Override
    public boolean scenarioExists(String scenarioId) {
        return load(scenarioId) != null;
    }

    @Override
    public List<String> metricNames(String scenarioId) {
        ScenarioMetrics metrics = load(scenarioId);
        return metrics == null ? List.of() : List.copyOf(metrics.metrics().keySet());
    }

    @Override
    public Optional<MetricSeries> queryMetric(String scenarioId, String metric) {
        ScenarioMetrics scenario = load(scenarioId);
        if (scenario == null) {
            return Optional.empty();
        }
        MetricData data = scenario.metrics().get(metric);
        if (data == null) {
            return Optional.empty();
        }
        List<MetricPoint> points = new ArrayList<>(data.values().size());
        for (int i = 0; i < data.values().size(); i++) {
            long epoch = scenario.startEpochSeconds() + (long) i * scenario.intervalSeconds();
            points.add(new MetricPoint(epoch, data.values().get(i)));
        }
        return Optional.of(new MetricSeries(
                scenarioId,
                metric,
                data.unit(),
                scenario.startEpochSeconds(),
                scenario.intervalSeconds(),
                points
        ));
    }

    private ScenarioMetrics load(String scenarioId) {
        if (scenarioId == null || scenarioId.isBlank()) {
            return null;
        }
        return cache.computeIfAbsent(scenarioId, id -> {
            String path = resourceRoot + "/" + id + "/metrics.json";
            try (InputStream stream = getClass().getResourceAsStream(path)) {
                if (stream == null) {
                    return null;
                }
                String json = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
                JsonNode root = MAPPER.readTree(json);
                Map<String, MetricData> metrics = new java.util.LinkedHashMap<>();
                JsonNode metricsNode = root.path("metrics");
                metricsNode.fields().forEachRemaining(entry -> {
                    JsonNode metricNode = entry.getValue();
                    List<Double> values = new ArrayList<>();
                    metricNode.path("values").forEach(value -> values.add(value.asDouble()));
                    metrics.put(entry.getKey(), new MetricData(
                            metricNode.path("unit").asText(""),
                            List.copyOf(values)
                    ));
                });
                return new ScenarioMetrics(
                        Instant.parse(root.path("startTime").asText()).getEpochSecond(),
                        root.path("intervalSeconds").asInt(60),
                        java.util.Collections.unmodifiableMap(metrics)
                );
            } catch (IOException e) {
                throw new IllegalStateException("读取场景指标失败: " + path, e);
            }
        });
    }

    private record ScenarioMetrics(long startEpochSeconds, int intervalSeconds, Map<String, MetricData> metrics) {
    }

    private record MetricData(String unit, List<Double> values) {
    }
}
