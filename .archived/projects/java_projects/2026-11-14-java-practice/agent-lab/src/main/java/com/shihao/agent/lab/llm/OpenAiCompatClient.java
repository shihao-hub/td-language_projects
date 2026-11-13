package com.shihao.agent.lab.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.shihao.agent.lab.config.LabConfig;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.UUID;

/**
 * 标准 OpenAI Chat Completions 客户端，同时覆盖 Ollama 与 opencode go。
 * 不依赖任何 Spring 或第三方 SDK。
 */
public class OpenAiCompatClient implements LlmClient {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Duration TIMEOUT = Duration.ofSeconds(120);

    private final LabConfig config;
    private final HttpClient http;
    private final String sessionId;
    private final int maxAttempts;

    public OpenAiCompatClient(LabConfig config) {
        this(config, HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build(), 2);
    }

    public OpenAiCompatClient(LabConfig config, HttpClient http, int maxAttempts) {
        this.config = config;
        this.http = http;
        this.sessionId = UUID.randomUUID().toString();
        this.maxAttempts = Math.max(1, maxAttempts);
    }

    @Override
    public String chat(List<ChatMessage> messages) {
        LlmException last = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                return doChat(messages);
            } catch (LlmException e) {
                last = e;
                if (!e.retryable() || attempt == maxAttempts) {
                    throw e;
                }
            }
        }
        throw last == null ? new LlmException("模型调用失败") : last;
    }

    private String doChat(List<ChatMessage> messages) {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(config.normalizedBaseUrl() + "/chat/completions"))
                .timeout(TIMEOUT)
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .header("Authorization", "Bearer " + config.apiKey())
                .header("x-opencode-session", sessionId)
                .POST(HttpRequest.BodyPublishers.ofString(buildBody(messages)))
                .build();

        HttpResponse<String> response;
        try {
            response = http.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (IOException e) {
            throw new LlmException("请求模型失败: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new LlmException("模型调用被中断", e);
        }

        if (response.statusCode() != 200) {
            throw new LlmException("模型返回非 200", response.statusCode(), truncate(response.body()));
        }
        return extractContent(response.body());
    }

    private String buildBody(List<ChatMessage> messages) {
        ObjectNode root = MAPPER.createObjectNode();
        root.put("model", config.model());
        root.put("temperature", 0.1);
        root.put("stream", false);
        ArrayNode array = root.putArray("messages");
        for (ChatMessage message : messages) {
            ObjectNode node = array.addObject();
            node.put("role", message.role());
            node.put("content", message.content());
        }
        try {
            return MAPPER.writeValueAsString(root);
        } catch (IOException e) {
            throw new LlmException("序列化请求失败", e);
        }
    }

    private String extractContent(String body) {
        try {
            JsonNode root = MAPPER.readTree(body);
            JsonNode content = root.path("choices").path(0).path("message").path("content");
            if (content.isMissingNode() || content.isNull()) {
                throw new LlmException("模型响应缺少 choices[0].message.content", 200, truncate(body));
            }
            return content.asText();
        } catch (IOException e) {
            throw new LlmException("解析模型响应失败: " + truncate(body), e);
        }
    }

    private static String truncate(String text) {
        if (text == null) {
            return "";
        }
        return text.length() <= 800 ? text : text.substring(0, 800) + "...";
    }
}
