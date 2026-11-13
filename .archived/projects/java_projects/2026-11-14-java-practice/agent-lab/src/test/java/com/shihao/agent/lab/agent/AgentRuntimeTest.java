package com.shihao.agent.lab.agent;

import com.shihao.agent.lab.telemetry.FileTelemetryRepository;
import com.shihao.agent.lab.tool.QueryMetricTool;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AgentRuntimeTest {

    private static final String SCENARIO = "s1-payment-success-drop";

    private AgentRuntime runtime(FakeLlmClient llm) {
        ToolRegistry registry = new ToolRegistry(List.of(
                new QueryMetricTool(new FileTelemetryRepository())
        ));
        return new AgentRuntime(llm, registry, TraceListener.silent());
    }

    @Test
    void completesToolCallThenFinalAnswer() {
        FakeLlmClient llm = new FakeLlmClient(
                """
                Thought: 先看整体支付成功率。
                Action: query_metric
                Action Input: {"scenarioId":"s1-payment-success-drop","metric":"payment_success_rate","window":"10m"}
                """,
                """
                Thought: 成功率断崖下跌，需要看风控命中率。
                Final Answer: 根因疑似风控规则误杀，证据是成功率与风控命中率同步反转。
                """
        );

        DiagnosisResult result = runtime(llm).run(new DiagnosisRequest(SCENARIO, "支付成功率骤降"));

        assertTrue(result.success());
        assertEquals(2, result.llmCalls());
        assertEquals(1, result.toolCalls());
        assertTrue(result.answer().contains("风控"));
        assertTrue(result.trace().stream().anyMatch(line -> line.startsWith("Observation(ok)")));
    }

    @Test
    void answersDirectlyWithoutTool() {
        FakeLlmClient llm = new FakeLlmClient("""
                Thought: 描述已经足够明确。
                Final Answer: 根因是风控规则误杀。
                """);

        DiagnosisResult result = runtime(llm).run(new DiagnosisRequest(SCENARIO, "风控误杀"));

        assertTrue(result.success());
        assertEquals(1, result.llmCalls());
        assertEquals(0, result.toolCalls());
    }

    @Test
    void unknownToolDoesNotAbortDiagnosis() {
        FakeLlmClient llm = new FakeLlmClient(
                """
                Thought: 先查一下。
                Action: query_trace
                Action Input: {"scenarioId":"s1-payment-success-drop"}
                """,
                """
                Thought: 工具不存在，改用指标。
                Final Answer: 根因是风控规则误杀。
                """
        );

        DiagnosisResult result = runtime(llm).run(new DiagnosisRequest(SCENARIO, "支付失败"));

        assertTrue(result.success());
        assertTrue(result.trace().stream().anyMatch(line -> line.contains("未知工具")));
    }

    @Test
    void failsOnUnparsableResponse() {
        FakeLlmClient llm = new FakeLlmClient("我觉得是网络问题。");

        DiagnosisResult result = runtime(llm).run(new DiagnosisRequest(SCENARIO, "支付失败"));

        assertFalse(result.success());
        assertTrue(result.failureReason().contains("解析失败"));
    }

    @Test
    void stopsAtMaxRounds() {
        String call = """
                Thought: 再查一次。
                Action: query_metric
                Action Input: {"scenarioId":"s1-payment-success-drop","metric":"order_volume"}
                """;
        FakeLlmClient llm = new FakeLlmClient(call, call, call, call, call, call, call, call, call);

        DiagnosisResult result = runtime(llm).run(new DiagnosisRequest(SCENARIO, "支付失败"));

        assertFalse(result.success());
        assertTrue(result.failureReason().contains("最大轮次"));
        assertEquals(8, result.llmCalls());
    }
}
