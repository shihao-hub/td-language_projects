package com.shihao.agent.lab.config;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ConfigLoaderTest {

    @TempDir
    Path tempDir;

    @Test
    void missingFileFallsBackToLocalOllama() {
        LabConfig config = ConfigLoader.loadDisk(tempDir);

        assertEquals("http://localhost:11434/v1", config.normalizedBaseUrl());
        assertEquals("qwen2.5:7b", config.model());
        assertEquals("ollama", config.channel());
    }

    @Test
    void readsDiskConfig() throws IOException {
        Files.writeString(tempDir.resolve("config.json"), """
                {
                  "base_url": "https://opencode.ai/inference/go/openai/v1",
                  "model": "deepseek-v4.1-flash",
                  "api_key": "oc_sk_test",
                  "channel": "opencode"
                }
                """, StandardCharsets.UTF_8);

        LabConfig config = ConfigLoader.loadDisk(tempDir);

        assertEquals("https://opencode.ai/inference/go/openai/v1", config.normalizedBaseUrl());
        assertEquals("deepseek-v4.1-flash", config.model());
        assertTrue(config.isOpenCode());
        assertEquals("oc_s...test", config.maskedApiKey());
    }

    @Test
    void trimsTrailingSlash() throws IOException {
        Files.writeString(tempDir.resolve("config.json"), """
                {"base_url":"http://localhost:11434/v1/","model":"qwen2.5:7b","api_key":"x"}
                """, StandardCharsets.UTF_8);

        assertEquals("http://localhost:11434/v1", ConfigLoader.loadDisk(tempDir).normalizedBaseUrl());
    }

    @Test
    void brokenJsonFailsFast() throws IOException {
        Files.writeString(tempDir.resolve("config.json"), "{not json", StandardCharsets.UTF_8);

        assertThrows(IllegalStateException.class, () -> ConfigLoader.loadDisk(tempDir));
    }
}
