package com.shihao.agent.lab.agent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 文本 ReAct 协议解析器。
 *
 * <p>不依赖模型原生 function calling，而是约定纯文本标记。
 * 7B 级模型的工具调用格式经常漂移，这里对全角冒号、代码围栏、
 * JSON 前后多余文字都做了容错。
 */
public final class ReActParser {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final Pattern THOUGHT = Pattern.compile("(?im)^\\s*thought\\s*[:：]\\s*");
    private static final Pattern ACTION = Pattern.compile("(?im)^\\s*action\\s*[:：][ \\t]*([^\\r\\n]*)");
    private static final Pattern ACTION_INPUT = Pattern.compile("(?im)^\\s*action\\s*input\\s*[:：]\\s*");
    private static final Pattern FINAL_ANSWER = Pattern.compile("(?im)^\\s*final\\s*answer\\s*[:：]\\s*");

    public ReActStep parse(String raw) {
        if (raw == null || raw.isBlank()) {
            return new ReActStep.ParseFailure(raw, "模型返回空响应");
        }
        String text = stripFences(raw).replace("\r\n", "\n").trim();

        Matcher finalMatcher = FINAL_ANSWER.matcher(text);
        if (finalMatcher.find()) {
            String thought = extractThought(text, finalMatcher.start());
            String answer = text.substring(finalMatcher.end()).trim();
            if (answer.isEmpty()) {
                return new ReActStep.ParseFailure(raw, "Final Answer 内容为空");
            }
            return new ReActStep.FinalAnswer(thought, answer);
        }

        Matcher actionMatcher = ACTION.matcher(text);
        if (!actionMatcher.find()) {
            return new ReActStep.ParseFailure(raw, "既没有 Final Answer 也没有 Action");
        }

        String toolName = actionMatcher.group(1).trim();
        if (toolName.isEmpty()) {
            return new ReActStep.ParseFailure(raw, "Action 工具名为空");
        }
        if (toolName.contains(" ")) {
            toolName = toolName.split("\\s+")[0];
        }

        Matcher inputMatcher = ACTION_INPUT.matcher(text);
        if (!inputMatcher.find(actionMatcher.end())) {
            return new ReActStep.ParseFailure(raw, "Action 后缺少 Action Input");
        }

        String json = text.substring(inputMatcher.end()).trim();
        JsonNode input = parseJsonObject(json);
        if (input == null) {
            return new ReActStep.ParseFailure(raw, "Action Input 不是合法 JSON 对象");
        }
        return new ReActStep.ToolCall(extractThought(text, actionMatcher.start()), toolName, input);
    }

    private static String extractThought(String text, int boundary) {
        Matcher matcher = THOUGHT.matcher(text);
        if (!matcher.find()) {
            return "";
        }
        int start = matcher.end();
        if (start >= boundary) {
            return matcher.group().trim();
        }
        return text.substring(start, boundary).trim();
    }

    private static JsonNode parseJsonObject(String text) {
        JsonNode direct = tryParse(text);
        if (direct != null) {
            return direct;
        }
        int start = text.indexOf('{');
        int end = text.lastIndexOf('}');
        if (start < 0 || end <= start) {
            return null;
        }
        return tryParse(text.substring(start, end + 1));
    }

    private static JsonNode tryParse(String text) {
        try {
            JsonNode node = MAPPER.readTree(text);
            return node != null && node.isObject() ? node : null;
        } catch (Exception ignored) {
            return null;
        }
    }

    private static String stripFences(String text) {
        return text.replace("```json", "").replace("```JSON", "").replace("```", "");
    }
}
