package com.shihao.agent.lab.tool;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.shihao.agent.lab.agent.ToolResult;
import com.shihao.agent.lab.telemetry.FileTelemetryRepository;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class QueryMetricToolTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final QueryMetricTool tool = new QueryMetricTool(new FileTelemetryRepository());

    @Test
    void returnsAggregatedWindow() {
        ObjectNode input = MAPPER.createObjectNode();
        input.put("scenarioId", "s1-payment-success-drop");
        input.put("metric", "payment_success_rate");
        input.put("window", "5m");

        ToolResult result = tool.execute(input);

        assertTrue(result.success());
        assertTrue(result.content().contains("指标 payment_success_rate"));
        assertTrue(result.content().contains("最近 5 分钟"));
        assertTrue(result.content().contains("min="));
        assertTrue(result.content().contains("last="));
    }

    @Test
    void failsWithoutScenario() {
        ObjectNode input = MAPPER.createObjectNode();
        input.put("metric", "payment_success_rate");

        ToolResult result = tool.execute(input);

        assertFalse(result.success());
        assertTrue(result.content().contains("scenarioId"));
    }

    @Test
    void failsOnUnknownMetricAndListsAlternatives() {
        ObjectNode input = MAPPER.createObjectNode();
        input.put("scenarioId", "s1-payment-success-drop");
        input.put("metric", "nope");

        ToolResult result = tool.execute(input);

        assertFalse(result.success());
        assertTrue(result.content().contains("可用指标"));
    }

    @Test
    void invalidWindowFallsBackToTenMinutes() {
        ObjectNode input = MAPPER.createObjectNode();
        input.put("scenarioId", "s1-payment-success-drop");
        input.put("metric", "order_volume");
        input.put("window", "abc");

        ToolResult result = tool.execute(input);

        assertTrue(result.success());
        assertTrue(result.content().contains("最近 10 分钟"));
    }
}
