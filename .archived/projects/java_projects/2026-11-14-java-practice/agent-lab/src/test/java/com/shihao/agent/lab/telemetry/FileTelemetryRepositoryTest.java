package com.shihao.agent.lab.telemetry;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class FileTelemetryRepositoryTest {

    private final FileTelemetryRepository repository = new FileTelemetryRepository();

    @Test
    void loadsScenarioMetrics() {
        assertTrue(repository.scenarioExists("s1-payment-success-drop"));

        Optional<MetricSeries> series = repository.queryMetric("s1-payment-success-drop", "payment_success_rate");
        assertTrue(series.isPresent());
        assertEquals(20, series.get().size());
        assertEquals("ratio", series.get().unit());
        assertEquals(0.986, series.get().points().get(0).value(), 0.0001);
        assertEquals(0.728, series.get().points().get(19).value(), 0.0001);
    }

    @Test
    void exposesMetricNames() {
        List<String> names = repository.metricNames("s1-payment-success-drop");
        assertTrue(names.contains("payment_success_rate"));
        assertTrue(names.contains("risk_rule_hit_rate"));
        assertTrue(names.contains("psp_http_error_rate"));
    }

    @Test
    void unknownScenarioReturnsEmpty() {
        assertFalse(repository.scenarioExists("nope"));
        assertTrue(repository.queryMetric("nope", "payment_success_rate").isEmpty());
        assertTrue(repository.metricNames("nope").isEmpty());
    }

    @Test
    void unknownMetricReturnsEmpty() {
        assertTrue(repository.queryMetric("s1-payment-success-drop", "nope").isEmpty());
    }
}
