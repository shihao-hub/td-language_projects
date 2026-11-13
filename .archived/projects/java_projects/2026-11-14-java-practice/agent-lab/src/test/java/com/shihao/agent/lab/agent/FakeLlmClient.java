package com.shihao.agent.lab.agent;

import com.shihao.agent.lab.llm.ChatMessage;
import com.shihao.agent.lab.llm.LlmClient;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * 脚本化模型替身：把不确定性关进 LlmClient 这一个接缝。
 */
class FakeLlmClient implements LlmClient {

    private final Deque<String> responses = new ArrayDeque<>();
    private final List<List<ChatMessage>> calls = new ArrayList<>();

    FakeLlmClient(String... scripted) {
        for (String response : scripted) {
            responses.add(response);
        }
    }

    @Override
    public String chat(List<ChatMessage> messages) {
        calls.add(List.copyOf(messages));
        if (responses.isEmpty()) {
            throw new IllegalStateException("FakeLlmClient 脚本已耗尽");
        }
        return responses.removeFirst();
    }

    List<List<ChatMessage>> calls() {
        return calls;
    }
}
