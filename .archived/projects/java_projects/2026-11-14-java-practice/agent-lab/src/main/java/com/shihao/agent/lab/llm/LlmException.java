package com.shihao.agent.lab.llm;

public class LlmException extends RuntimeException {

    private final int status;

    public LlmException(String message) {
        this(message, -1, null);
    }

    public LlmException(String message, Throwable cause) {
        super(message, cause);
        this.status = -1;
    }

    public LlmException(String message, int status, String body) {
        super(message + (body == null || body.isBlank() ? "" : " | body=" + body));
        this.status = status;
    }

    public int status() {
        return status;
    }

    public boolean retryable() {
        return status == -1 || status == 429 || status >= 500;
    }
}
