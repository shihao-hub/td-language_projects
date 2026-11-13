package com.shihao.career.agent.controller;

import com.shihao.career.agent.alert.AlertStormSynthesizer;
import com.shihao.career.agent.skill.SkillTreeRouter;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/agent")
public class AgentDemoController {

    private final AlertStormSynthesizer alertSynthesizer = new AlertStormSynthesizer();
    private final SkillTreeRouter skillRouter = new SkillTreeRouter();

    public AgentDemoController() {
        // 注册诊断技能
        skillRouter.registerSkill(new SkillTreeRouter.DiagnosticSkill("SKILL_OOM_DUMP", "INFRA", "OOM", "抓取 jmap dump 并排查元空间与堆内存泄露"));
        skillRouter.registerSkill(new SkillTreeRouter.DiagnosticSkill("SKILL_PAY_RETRY", "BUSINESS", "支付超时", "核对渠道异步回调流水并触发重试"));
        skillRouter.registerSkill(new SkillTreeRouter.DiagnosticSkill("SKILL_RIDER_GPS", "NETWORK", "定位延迟", "排查 MQTT 消息堆积与基站上报延迟"));
    }

    @GetMapping("/synthesize-alerts")
    public List<AlertStormSynthesizer.SynthesizedIncident> testSynthesizeAlerts() {
        List<AlertStormSynthesizer.RawAlert> rawAlerts = List.of(
                new AlertStormSynthesizer.RawAlert("A01", "payment-service", "ERR_CHANNEL_TIMEOUT", "10.0.1.12", Instant.now()),
                new AlertStormSynthesizer.RawAlert("A02", "payment-service", "ERR_CHANNEL_TIMEOUT", "10.0.1.13", Instant.now()),
                new AlertStormSynthesizer.RawAlert("A03", "payment-service", "ERR_CHANNEL_TIMEOUT", "10.0.1.12", Instant.now()),
                new AlertStormSynthesizer.RawAlert("A04", "order-service", "ERR_DB_DEADLOCK", "10.0.2.88", Instant.now())
        );
        return alertSynthesizer.synthesize(rawAlerts);
    }

    @GetMapping("/route-skill")
    public List<SkillTreeRouter.DiagnosticSkill> routeSkill(@RequestParam(defaultValue = "线上微服务突发 OOM 崩溃") String query) {
        return skillRouter.matchSkills(query);
    }
}
