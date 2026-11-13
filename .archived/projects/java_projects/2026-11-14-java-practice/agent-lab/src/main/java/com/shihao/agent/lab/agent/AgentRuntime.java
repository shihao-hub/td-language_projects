package com.shihao.agent.lab.agent;

import com.shihao.agent.lab.llm.ChatMessage;
import com.shihao.agent.lab.llm.LlmClient;

import java.util.ArrayList;
import java.util.List;

/**
 * 诊断主循环（T01 版本：支持一次工具调用后收敛）。
 *
 * <p>多轮循环、Skill 化与证据链累积在后续切片中扩展；
 * 此处刻意保持最小可运行，先把"模型 → 解析 → 工具 → 回填 → 结论"跑通。
 */
public class AgentRuntime {

    private static final int MAX_REACT_ROUNDS = 8;

    private final LlmClient llm;
    private final ToolRegistry registry;
    private final ReActParser parser;
    private final TraceListener trace;

    public AgentRuntime(LlmClient llm, ToolRegistry registry, TraceListener trace) {
        this.llm = llm;
        this.registry = registry;
        this.parser = new ReActParser();
        this.trace = trace == null ? TraceListener.silent() : trace;
    }

    public DiagnosisResult run(DiagnosisRequest request) {
        List<String> events = new ArrayList<>();
        List<ChatMessage> messages = new ArrayList<>();
        messages.add(ChatMessage.system(systemPrompt()));
        messages.add(ChatMessage.user(userPrompt(request)));

        int llmCalls = 0;
        int toolCalls = 0;

        for (int round = 1; round <= MAX_REACT_ROUNDS; round++) {
            String raw = llm.chat(messages);
            llmCalls++;
            emit(events, "LLM#" + llmCalls + " 响应:\n" + raw);

            ReActStep step = parser.parse(raw);
            switch (step) {
                case ReActStep.FinalAnswer answer -> {
                    emit(events, "结论: " + answer.answer());
                    return DiagnosisResult.success(answer.answer(), events, llmCalls, toolCalls);
                }
                case ReActStep.ToolCall call -> {
                    emit(events, "Action: " + call.toolName() + " " + call.input());
                    ToolResult result = registry.execute(call.toolName(), call.input());
                    toolCalls++;
                    emit(events, "Observation(" + (result.success() ? "ok" : "fail") + "): " + result.content());
                    messages.add(ChatMessage.assistant(raw));
                    messages.add(ChatMessage.user("Observation:\n" + result.content()));
                }
                case ReActStep.ParseFailure failure -> {
                    emit(events, "解析失败: " + failure.reason());
                    return DiagnosisResult.failure("解析失败: " + failure.reason(), events, llmCalls, toolCalls);
                }
            }
        }
        return DiagnosisResult.failure("超过最大轮次 " + MAX_REACT_ROUNDS, events, llmCalls, toolCalls);
    }

    private String systemPrompt() {
        return """
                你是国际化外卖交易链路的故障诊断 Agent。
                你的任务是根据故障描述，自主调用工具收集证据，定位根因。

                可用工具:
                %s

                输出协议（严格遵守，每次只输出一种）:

                若还需要查数据，输出:
                Thought: <一句话说明你为什么查这个>
                Action: <工具名>
                Action Input: <JSON 对象>

                若证据已足够，输出:
                Thought: <一句话总结推理>
                Final Answer: <根因、关键证据、已排除的干扰项>

                规则:
                1. 只能使用上面列出的工具名，禁止编造。
                2. Action Input 必须是合法 JSON，不能包含注释或额外文字。
                3. 不要一次列多个 Action，每轮只做一个决定。
                4. 下结论前必须至少查过一个工具。
                """.formatted(registry.describeForPrompt());
    }

    private String userPrompt(DiagnosisRequest request) {
        return """
                场景 ID: %s
                故障描述: %s

                请开始诊断。数据窗口为最近 10 分钟。
                """.formatted(request.scenarioId(), request.query());
    }

    private void emit(List<String> events, String event) {
        events.add(event);
        trace.onEvent(event);
    }
}
