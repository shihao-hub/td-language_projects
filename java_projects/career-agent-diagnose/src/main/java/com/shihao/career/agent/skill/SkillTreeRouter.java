package com.shihao.career.agent.skill;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * <h2>Agent 分层 Skill 树路由引擎</h2>
 * 针对海量 Skill 导致的大模型选路困惑与 Token 浪费，
 * 采用【两阶段选路：粗排领域分类 -> 精排意图分发】将大模型候选集从 200+ 压缩到 Top-3。
 */
public class SkillTreeRouter {

    public record DiagnosticSkill(
            String skillId,
            String domain, // 如 INFRA, BUSINESS, NETWORK
            String triggerPattern,
            String executionSop
    ) {}

    private final Map<String, List<DiagnosticSkill>> domainSkillTree = new ConcurrentHashMap<>();

    public void registerSkill(DiagnosticSkill skill) {
        domainSkillTree.computeIfAbsent(skill.domain(), k -> new java.util.concurrent.CopyOnWriteArrayList<>()).add(skill);
    }

    /**
     * 第一阶段：粗排 (按故障症状推导所属领域)
     */
    public String routeDomain(String symptomText) {
        if (symptomText.contains("OOM") || symptomText.contains("内存") || symptomText.contains("CPU") || symptomText.contains("线程池")) {
            return "INFRA";
        } else if (symptomText.contains("支付") || symptomText.contains("接单") || symptomText.contains("派单") || symptomText.contains("优惠券")) {
            return "BUSINESS";
        } else {
            return "NETWORK";
        }
    }

    /**
     * 第二阶段：精排 (在目标领域子树中召回匹配的专用 Skill)
     */
    public List<DiagnosticSkill> matchSkills(String symptomText) {
        String domain = routeDomain(symptomText);
        List<DiagnosticSkill> candidatePool = domainSkillTree.getOrDefault(domain, List.of());

        return candidatePool.stream()
                .filter(skill -> symptomText.contains(skill.triggerPattern()))
                .toList();
    }
}
