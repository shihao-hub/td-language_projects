package com.shihao.agent.lab.llm;

import java.util.List;

/**
 * 模型接缝：唯一允许出现不确定性的边界。
 * 其余所有层都必须可确定性测试。
 */
public interface LlmClient {

    String chat(List<ChatMessage> messages);
}
