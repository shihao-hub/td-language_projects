package com.shihao.agent.lab;

import com.shihao.agent.lab.agent.AgentRuntime;
import com.shihao.agent.lab.agent.DiagnosisRequest;
import com.shihao.agent.lab.agent.DiagnosisResult;
import com.shihao.agent.lab.agent.ToolRegistry;
import com.shihao.agent.lab.agent.TraceListener;
import com.shihao.agent.lab.config.ConfigLoader;
import com.shihao.agent.lab.config.LabConfig;
import com.shihao.agent.lab.llm.OpenAiCompatClient;
import com.shihao.agent.lab.telemetry.FileTelemetryRepository;
import com.shihao.agent.lab.tool.QueryMetricTool;

import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * CLI 入口。第一层内核不依赖 Spring，可直接 main() 运行。
 */
public final class LabCli {

    private LabCli() {
    }

    public static void main(String[] args) {
        forceUtf8Console();
        if (args.length == 0) {
            usage();
            return;
        }
        try {
            switch (args[0]) {
                case "diagnose" -> diagnose(args);
                case "tools" -> tools();
                case "config" -> config();
                default -> {
                    System.err.println("未知命令: " + args[0]);
                    usage();
                }
            }
        } catch (Exception e) {
            System.err.println("运行失败: " + e.getMessage());
        }
    }

    private static void diagnose(String[] args) {
        String scenario = option(args, "--scenario");
        String query = option(args, "--query");
        if (scenario == null || query == null) {
            System.err.println("用法: diagnose --scenario <场景ID> --query \"<故障描述>\"");
            return;
        }

        LabConfig config = ConfigLoader.load();
        System.out.println("通道: " + config.channel() + " | 模型: " + config.model()
                + " | 地址: " + config.normalizedBaseUrl());
        System.out.println("配置: " + ConfigLoader.configFile());
        System.out.println("---");

        ToolRegistry registry = new ToolRegistry(List.of(
                new QueryMetricTool(new FileTelemetryRepository())
        ));
        AgentRuntime runtime = new AgentRuntime(
                new OpenAiCompatClient(config),
                registry,
                TraceListener.stdout()
        );

        DiagnosisResult result = runtime.run(new DiagnosisRequest(scenario, query));
        System.out.println("---");
        if (result.success()) {
            System.out.println("诊断结论:");
            System.out.println(result.answer());
        } else {
            System.out.println("诊断失败: " + result.failureReason());
        }
        System.out.println("LLM 调用 " + result.llmCalls() + " 次，工具调用 " + result.toolCalls() + " 次");
    }

    private static void tools() {
        ToolRegistry registry = new ToolRegistry(List.of(
                new QueryMetricTool(new FileTelemetryRepository())
        ));
        System.out.println("已注册工具:");
        System.out.println(registry.describeForPrompt());
    }

    private static void config() {
        LabConfig config = ConfigLoader.load();
        System.out.println("配置文件: " + ConfigLoader.configFile());
        System.out.println("通道: " + config.channel());
        System.out.println("地址: " + config.normalizedBaseUrl());
        System.out.println("模型: " + config.model());
        System.out.println("密钥: " + config.maskedApiKey());
    }

    private static String option(String[] args, String name) {
        for (int i = 0; i < args.length - 1; i++) {
            if (args[i].equals(name)) {
                return args[i + 1];
            }
        }
        return null;
    }

    private static void usage() {
        System.out.println("""
                agent-lab — 手写 ReAct 故障诊断 Agent

                用法:
                  diagnose --scenario <场景ID> --query "<故障描述>"
                  tools
                  config

                示例:
                  diagnose --scenario s1-payment-success-drop --query "墨西哥站支付成功率从 98% 掉到 71%"
                """);
    }

    private static void forceUtf8Console() {
        PrintStream out = new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8);
        System.setOut(out);
        System.setErr(new PrintStream(new FileOutputStream(FileDescriptor.err), true, StandardCharsets.UTF_8));
    }
}
