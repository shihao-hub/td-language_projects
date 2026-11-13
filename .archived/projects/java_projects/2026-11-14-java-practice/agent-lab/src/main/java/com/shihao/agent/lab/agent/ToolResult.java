package com.shihao.agent.lab.agent;

public record ToolResult(boolean success, String content) {

    public static ToolResult ok(String content) {
        return new ToolResult(true, content);
    }

    public static ToolResult fail(String content) {
        return new ToolResult(false, content);
    }
}
