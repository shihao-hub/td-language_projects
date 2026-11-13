package com.shihao.agent.lab.agent;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * 一轮 ReAct 的解析结果。三项互斥，调用方用 switch 模式匹配穷尽处理。
 */
public sealed interface ReActStep {

    record FinalAnswer(String thought, String answer) implements ReActStep {
    }

    record ToolCall(String thought, String toolName, JsonNode input) implements ReActStep {
    }

    record ParseFailure(String raw, String reason) implements ReActStep {
    }
}
