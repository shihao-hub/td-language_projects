package com.shihao.agent.lab.agent;

import java.util.List;

public record DiagnosisResult(
        boolean success,
        String answer,
        List<String> trace,
        int llmCalls,
        int toolCalls,
        String failureReason
) {

    public static DiagnosisResult success(String answer, List<String> trace, int llmCalls, int toolCalls) {
        return new DiagnosisResult(true, answer, List.copyOf(trace), llmCalls, toolCalls, null);
    }

    public static DiagnosisResult failure(String reason, List<String> trace, int llmCalls, int toolCalls) {
        return new DiagnosisResult(false, "", List.copyOf(trace), llmCalls, toolCalls, reason);
    }
}
