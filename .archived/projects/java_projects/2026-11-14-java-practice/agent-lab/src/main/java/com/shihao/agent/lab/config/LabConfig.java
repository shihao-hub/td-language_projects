package com.shihao.agent.lab.config;

/**
 * 模型通道配置。channel 仅用于展示与日志，不参与协议选择。
 */
public record LabConfig(String baseUrl, String model, String apiKey, String channel) {

    public String normalizedBaseUrl() {
        String url = baseUrl == null ? "" : baseUrl.trim();
        while (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        return url;
    }

    /**
     * opencode go 需要一个会话路由头，其它 OpenAI 兼容端点不需要。
     */
    public boolean isOpenCode() {
        return normalizedBaseUrl().contains("opencode.ai");
    }

    public String maskedApiKey() {
        if (apiKey == null || apiKey.isBlank()) {
            return "<empty>";
        }
        if (apiKey.length() <= 8) {
            return "<set>";
        }
        return apiKey.substring(0, 4) + "..." + apiKey.substring(apiKey.length() - 4);
    }
}
