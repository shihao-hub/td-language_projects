package com.shihao.agent.lab.agent;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.StringJoiner;

/**
 * 工具注册表：负责发现、描述与隔离异常。
 * 未知工具返回失败结果而不是抛异常——幻觉工具名是常态，不能让它打断整个诊断。
 */
public final class ToolRegistry {

    private final Map<String, Tool> tools = new LinkedHashMap<>();

    public ToolRegistry(List<Tool> tools) {
        for (Tool tool : tools) {
            Tool previous = this.tools.putIfAbsent(tool.name(), tool);
            if (previous != null) {
                throw new IllegalArgumentException("工具名重复: " + tool.name());
            }
        }
    }

    public Optional<Tool> find(String name) {
        return Optional.ofNullable(tools.get(name));
    }

    public List<String> names() {
        return List.copyOf(tools.keySet());
    }

    public ToolResult execute(String name, JsonNode input) {
        Tool tool = tools.get(name);
        if (tool == null) {
            return ToolResult.fail("未知工具 [" + name + "]，可用工具: " + String.join(", ", names()));
        }
        try {
            return tool.execute(input == null ? com.fasterxml.jackson.databind.node.JsonNodeFactory.instance.objectNode() : input);
        } catch (Exception e) {
            return ToolResult.fail("工具执行异常: " + e.getMessage());
        }
    }

    public String describeForPrompt() {
        StringJoiner joiner = new StringJoiner("\n");
        for (Tool tool : tools.values()) {
            joiner.add("- " + tool.name() + ": " + tool.description()
                    + "\n  参数: " + tool.inputSchema());
        }
        return joiner.toString();
    }
}
