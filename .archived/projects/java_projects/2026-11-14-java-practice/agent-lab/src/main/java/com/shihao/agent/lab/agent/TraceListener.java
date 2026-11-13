package com.shihao.agent.lab.agent;

@FunctionalInterface
public interface TraceListener {

    void onEvent(String event);

    static TraceListener stdout() {
        return System.out::println;
    }

    static TraceListener silent() {
        return event -> {
        };
    }
}
