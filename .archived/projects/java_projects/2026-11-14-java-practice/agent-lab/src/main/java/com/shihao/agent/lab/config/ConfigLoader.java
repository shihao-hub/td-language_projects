package com.shihao.agent.lab.config;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/**
 * 配置来源优先级：环境变量 > config.json > 内置默认值。
 * 内置默认值指向本地 Ollama，保证无密钥也能开工。
 */
public final class ConfigLoader {

    public static final String ENV_NAME = "LAB_ENV";
    public static final String ENV_BASE_URL = "LAB_BASE_URL";
    public static final String ENV_MODEL = "LAB_MODEL";
    public static final String ENV_API_KEY = "LAB_API_KEY";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private ConfigLoader() {
    }

    public static LabConfig load() {
        return load(defaultDir());
    }

    public static LabConfig load(Path dir) {
        LabConfig disk = loadDisk(dir);
        return applyEnvironment(disk);
    }

    public static LabConfig loadDisk(Path dir) {
        Path file = dir.resolve("config.json");
        if (!Files.exists(file)) {
            return defaults();
        }
        try {
            JsonNode node = MAPPER.readTree(Files.readString(file, StandardCharsets.UTF_8));
            return new LabConfig(
                    text(node, "base_url", defaults().baseUrl()),
                    text(node, "model", defaults().model()),
                    text(node, "api_key", ""),
                    text(node, "channel", "ollama")
            );
        } catch (IOException e) {
            throw new IllegalStateException("解析配置失败: " + file + " -> " + e.getMessage(), e);
        }
    }

    public static LabConfig applyEnvironment(LabConfig base) {
        String channel = base.channel();
        String baseUrl = override(ENV_BASE_URL, base.baseUrl());
        if (!baseUrl.equals(base.baseUrl())) {
            channel = baseUrl.contains("opencode.ai") ? "opencode" : "ollama";
        }
        return new LabConfig(
                baseUrl,
                override(ENV_MODEL, base.model()),
                override(ENV_API_KEY, base.apiKey()),
                channel
        );
    }

    /**
     * 运行时数据目录：%APPDATA%\language_projects\agent-lab\<dev|prod>。
     */
    public static Path defaultDir() {
        String env = firstNonBlank(System.getenv(ENV_NAME), System.getProperty("lab.env"), "dev")
                .toLowerCase(Locale.ROOT);
        String appData = firstNonBlank(System.getenv("APPDATA"), System.getenv("AppData"));
        Path root;
        if (appData != null) {
            root = Path.of(appData, "language_projects", "agent-lab");
        } else {
            root = Path.of(System.getProperty("user.home"), ".language_projects", "agent-lab");
        }
        return root.resolve(env);
    }

    public static Path configFile() {
        return defaultDir().resolve("config.json");
    }

    private static LabConfig defaults() {
        return new LabConfig("http://localhost:11434/v1", "qwen2.5:7b", "ollama", "ollama");
    }

    private static String text(JsonNode node, String field, String fallback) {
        JsonNode value = node.get(field);
        if (value == null || value.isNull() || value.asText().isBlank()) {
            return fallback;
        }
        return value.asText().trim();
    }

    private static String override(String envKey, String fallback) {
        String value = System.getenv(envKey);
        if (value == null || value.isBlank()) {
            return fallback;
        }
        return value.trim();
    }

    private static String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return null;
    }
}
