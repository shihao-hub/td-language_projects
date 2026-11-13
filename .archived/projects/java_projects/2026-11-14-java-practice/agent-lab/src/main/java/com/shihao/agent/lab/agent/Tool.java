package com.shihao.agent.lab.agent;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * 工具契约。实现类只做数据读取与格式化，不做任何推理。
 */
public interface Tool {

    String name();

    String description();

    String inputSchema();

    ToolResult execute(JsonNode input);
}
