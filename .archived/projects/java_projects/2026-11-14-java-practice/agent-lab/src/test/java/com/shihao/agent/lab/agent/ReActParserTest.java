package com.shihao.agent.lab.agent;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ReActParserTest {

    private final ReActParser parser = new ReActParser();

    @Test
    void parsesFinalAnswer() {
        ReActStep step = parser.parse("""
                Thought: 三个渠道同步下跌，渠道自身健康，先看风控。
                Final Answer: 根因是风控规则误杀。
                """);

        ReActStep.FinalAnswer answer = assertInstanceOf(ReActStep.FinalAnswer.class, step);
        assertEquals("根因是风控规则误杀。", answer.answer());
        assertTrue(answer.thought().contains("风控"));
    }

    @Test
    void parsesToolCallWithJson() {
        ReActStep step = parser.parse("""
                Thought: 先看支付成功率整体趋势。
                Action: query_metric
                Action Input: {"scenarioId":"s1-payment-success-drop","metric":"payment_success_rate","window":"10m"}
                """);

        ReActStep.ToolCall call = assertInstanceOf(ReActStep.ToolCall.class, step);
        assertEquals("query_metric", call.toolName());
        assertEquals("s1-payment-success-drop", call.input().get("scenarioId").asText());
        assertEquals("payment_success_rate", call.input().get("metric").asText());
    }

    @Test
    void toleratesFullWidthColonAndFences() {
        ReActStep step = parser.parse("""
                ```text
                Thought：先查渠道成功率。
                Action：query_metric
                Action Input：{"scenarioId":"s1","metric":"psp_a_success_rate"}
                ```
                """);

        ReActStep.ToolCall call = assertInstanceOf(ReActStep.ToolCall.class, step);
        assertEquals("query_metric", call.toolName());
    }

    @Test
    void extractsJsonFromNoisyText() {
        ReActStep step = parser.parse("""
                Thought: 查一下。
                Action: query_metric
                Action Input: 这是参数 {"scenarioId":"s1","metric":"order_volume"} 请执行
                """);

        ReActStep.ToolCall call = assertInstanceOf(ReActStep.ToolCall.class, step);
        assertEquals("order_volume", call.input().get("metric").asText());
    }

    @Test
    void reportsFailureWhenNeitherBranchPresent() {
        ReActStep step = parser.parse("我觉得可能是网络问题。");

        ReActStep.ParseFailure failure = assertInstanceOf(ReActStep.ParseFailure.class, step);
        assertTrue(failure.reason().contains("Final Answer"));
    }

    @Test
    void reportsFailureOnBrokenJson() {
        ReActStep step = parser.parse("""
                Thought: 查一下。
                Action: query_metric
                Action Input: {scenarioId: s1}
                """);

        assertInstanceOf(ReActStep.ParseFailure.class, step);
    }
}
