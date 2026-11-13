package com.shihao.agent.lab.agent;

public record DiagnosisRequest(String scenarioId, String query) {

    public DiagnosisRequest {
        if (scenarioId == null || scenarioId.isBlank()) {
            throw new IllegalArgumentException("scenarioId 不能为空");
        }
        if (query == null || query.isBlank()) {
            throw new IllegalArgumentException("query 不能为空");
        }
    }
}
