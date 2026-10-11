package com.shihao.career.agent.alert;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * <h2>时序告警风暴压缩聚合器</h2>
 * 将微服务集群海量微观告警（每秒成百上千条）按维度与滑动时间窗口压缩收敛为一个高阶事件。
 */
public class AlertStormSynthesizer {

    public record RawAlert(
            String alertId,
            String serviceName,
            String errorCode,
            String podIp,
            Instant timestamp
    ) {}

    public record SynthesizedIncident(
            String incidentId,
            String primaryService,
            String rootErrorCode,
            int rawAlertCount,
            List<String> affectedPods,
            String description
    ) {}

    /**
     * 将原始告警按 ServiceName + ErrorCode 聚合成高阶事故 (Incident)
     */
    public List<SynthesizedIncident> synthesize(List<RawAlert> rawAlerts) {
        Map<String, List<RawAlert>> grouped = rawAlerts.stream()
                .collect(Collectors.groupingBy(a -> a.serviceName() + "#" + a.errorCode()));

        return grouped.entrySet().stream()
                .map(entry -> {
                    String[] parts = entry.getKey().split("#");
                    String service = parts[0];
                    String errCode = parts[1];
                    List<RawAlert> alerts = entry.getValue();

                    List<String> pods = alerts.stream().map(RawAlert::podIp).distinct().toList();
                    String incidentId = "INCIDENT_" + service + "_" + Math.abs(entry.getKey().hashCode() % 10000);

                    return new SynthesizedIncident(
                            incidentId,
                            service,
                            errCode,
                            alerts.size(),
                            pods,
                            String.format("服务 [%s] 聚合 %d 条告警，根因疑似: %s，影响 Pod 数: %d", service, alerts.size(), errCode, pods.size())
                    );
                })
                .toList();
    }
}
