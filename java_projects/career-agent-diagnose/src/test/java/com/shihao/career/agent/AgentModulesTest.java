package com.shihao.career.agent;

import com.shihao.career.agent.alert.AlertStormSynthesizer;
import com.shihao.career.agent.skill.SkillTreeRouter;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
public class AgentModulesTest {

    @Test
    @DisplayName("测试告警风暴多维度收敛聚合")
    void testAlertStormSynthesizer() {
        AlertStormSynthesizer synthesizer = new AlertStormSynthesizer();
        List<AlertStormSynthesizer.RawAlert> rawAlerts = List.of(
                new AlertStormSynthesizer.RawAlert("1", "order-svc", "TIMEOUT", "10.0.0.1", Instant.now()),
                new AlertStormSynthesizer.RawAlert("2", "order-svc", "TIMEOUT", "10.0.0.2", Instant.now()),
                new AlertStormSynthesizer.RawAlert("3", "order-svc", "TIMEOUT", "10.0.0.1", Instant.now()),
                new AlertStormSynthesizer.RawAlert("4", "pay-svc", "500_ERROR", "10.0.1.1", Instant.now())
        );

        List<AlertStormSynthesizer.SynthesizedIncident> incidents = synthesizer.synthesize(rawAlerts);
        assertEquals(2, incidents.size(), "4 条细碎告警应收敛为 2 个高阶事件");

        AlertStormSynthesizer.SynthesizedIncident orderIncident = incidents.stream()
                .filter(i -> i.primaryService().equals("order-svc"))
                .findFirst()
                .orElseThrow();

        assertEquals(3, orderIncident.rawAlertCount(), "order-svc 的 3 条超时告警应被聚合成 1 个事故");
        assertEquals(2, orderIncident.affectedPods().size(), "应识别出跨越了 2 个不同的 Pod IP");
    }

    @Test
    @DisplayName("测试 Skill 树两阶段精准路由与候选集剪枝")
    void testSkillTreeRouting() {
        SkillTreeRouter router = new SkillTreeRouter();
        router.registerSkill(new SkillTreeRouter.DiagnosticSkill("SK1", "INFRA", "OOM", "dump 堆内存"));
        router.registerSkill(new SkillTreeRouter.DiagnosticSkill("SK2", "INFRA", "CPU 飙高", "抓取 top H 线程栈"));
        router.registerSkill(new SkillTreeRouter.DiagnosticSkill("SK3", "BUSINESS", "优惠券失效", "查询规则中心"));

        // 验证粗排领域推导
        assertEquals("INFRA", router.routeDomain("生产集群节点内存打满发生 OOM"));
        assertEquals("BUSINESS", router.routeDomain("用户反馈外卖优惠券失效"));

        // 验证精排匹配
        List<SkillTreeRouter.DiagnosticSkill> matched = router.matchSkills("生产集群节点内存打满发生 OOM");
        assertEquals(1, matched.size());
        assertEquals("SK1", matched.get(0).skillId());
    }
}
