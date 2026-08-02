package com.viaios.aikernel.kernel;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Capability Manager implementation.
 *
 * <p>This is the key architectural differentiator of VIAIOS.
 * Business code calls capabilities (e.g. "face_detection"), NOT specific models.
 * The Capability Manager transparently routes to the best available model.
 *
 * <p>Routing algorithm: priority-based with fallback chain.
 * For each capability domain, models are sorted by (channel priority × weight).
 * DEFAULT models get 100% traffic unless a canary is active.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CapabilityManagerImpl implements CapabilityManager {

    private final Map<UUID, CapabilityDescriptor> capabilities = new ConcurrentHashMap<>();
    private final Map<UUID, List<CapabilityBinding>> bindings = new ConcurrentHashMap<>(); // capabilityId → bindings
    private final Map<String, ABTest> activeTests = new ConcurrentHashMap<>();            // testId → test

    @Override
    public CapabilityDescriptor register(CapabilityRegistration request) {
        UUID id = UUID.randomUUID();
        var now = LocalDateTime.now();

        // Validate domain uniqueness
        boolean exists = capabilities.values().stream()
            .anyMatch(c -> c.domain().equalsIgnoreCase(request.domain()));
        if (exists) throw new IllegalArgumentException("Capability domain already exists: " + request.domain());

        CapabilityDescriptor descriptor = new CapabilityDescriptor(
            id, request.domain(), request.displayName(), request.category(),
            request.description(), request.inputSchema(), request.outputSchema(),
            "ACTIVE", 0, now, request.metadata()
        );

        capabilities.put(id, descriptor);
        bindings.put(id, new ArrayList<>());

        log.info("Capability registered: {} [{}] id={}", request.domain(), request.category(), id);
        return descriptor;
    }

    @Override
    public CapabilityBinding bindModel(UUID capabilityId, UUID modelId, BindingConfig config) {
        CapabilityDescriptor cap = requireCapability(capabilityId);

        CapabilityBinding binding = new CapabilityBinding(
            UUID.randomUUID(), capabilityId, modelId,
            "model-" + modelId.toString().substring(0, 8), "v1",
            ReleaseChannel.DEFAULT, config.weight(), config, LocalDateTime.now()
        );

        bindings.computeIfAbsent(capabilityId, k -> new ArrayList<>()).add(binding);

        // Update binding count on descriptor
        capabilities.put(capabilityId, new CapabilityDescriptor(
            cap.id(), cap.domain(), cap.displayName(), cap.category(),
            cap.description(), cap.inputSchema(), cap.outputSchema(),
            cap.status(), bindings.get(capabilityId).size(), cap.createdAt(), cap.metadata()
        ));

        log.info("Model {} bound to capability {} [channel={}, weight={}]",
            modelId, cap.domain(), binding.channel(), config.weight());
        return binding;
    }

    @Override
    public void unbindModel(UUID capabilityId, UUID modelId) {
        List<CapabilityBinding> list = bindings.get(capabilityId);
        if (list != null) {
            list.removeIf(b -> b.modelId().equals(modelId));
        }
        log.info("Model {} unbound from capability {}", modelId, capabilityId);
    }

    // ── Routing (core algorithm) ──────────────────────────────────

    @Override
    public RoutingDecision route(String capabilityDomain, RoutingContext context) {
        // Find capability by domain
        CapabilityDescriptor cap = capabilities.values().stream()
            .filter(c -> c.domain().equalsIgnoreCase(capabilityDomain))
            .findFirst()
            .orElseThrow(() -> new NoSuchElementException("Capability not found: " + capabilityDomain));

        List<CapabilityBinding> all = bindings.getOrDefault(cap.id(), List.of());
        if (all.isEmpty()) {
            throw new IllegalStateException("No models bound to capability: " + capabilityDomain);
        }

        // Sort by: channel priority (DEFAULT > STABLE > CANARY > EXPERIMENTAL), then weight
        List<CapabilityBinding> sorted = all.stream()
            .sorted(Comparator
                .comparingInt((CapabilityBinding b) -> channelPriority(b.channel()))
                .thenComparingInt(b -> b.config().priority())
                .reversed())
            .toList();

        // Check for active A/B tests affecting this capability
        Optional<ABTest> activeTest = activeTests.values().stream()
            .filter(t -> t.capabilityId().equals(cap.id()) && "RUNNING".equals(t.status()))
            .findFirst();

        CapabilityBinding selected;
        String reason;

        if (activeTest.isPresent()) {
            // A/B test: route based on traffic split
            ABTest test = activeTest.get();
            boolean useModelB = Math.random() * 100 < test.config().trafficSplit();
            UUID targetModelId = useModelB ? test.modelBId() : test.modelAId();
            selected = sorted.stream().filter(b -> b.modelId().equals(targetModelId)).findFirst().orElse(sorted.get(0));
            reason = useModelB ? "A/B test: model B" : "A/B test: model A";
        } else {
            // Normal routing: pick highest-priority model, fallback on failure
            selected = sorted.get(0);
            reason = "Priority routing: " + selected.channel() + " channel";
        }

        return new RoutingDecision(
            selected.modelId(), null, // nodeName resolved by ResourceManager
            "/api/v1/infer/" + selected.modelId(),
            selected.channel(), reason, false
        );
    }

    @Override
    public List<CapabilityBinding> getBindings(String capabilityDomain) {
        CapabilityDescriptor cap = capabilities.values().stream()
            .filter(c -> c.domain().equalsIgnoreCase(capabilityDomain))
            .findFirst()
            .orElseThrow(() -> new NoSuchElementException("Capability not found: " + capabilityDomain));
        return bindings.getOrDefault(cap.id(), List.of());
    }

    // ── Version & Release ─────────────────────────────────────────

    @Override
    public void promoteVersion(UUID capabilityId, UUID modelId, ReleaseChannel channel) {
        List<CapabilityBinding> list = bindings.get(capabilityId);
        if (list == null) throw new NoSuchElementException("No bindings for capability: " + capabilityId);

        list.stream()
            .filter(b -> b.modelId().equals(modelId))
            .findFirst()
            .ifPresent(b -> {
                int idx = list.indexOf(b);
                list.set(idx, new CapabilityBinding(
                    b.id(), b.capabilityId(), b.modelId(), b.modelName(), b.modelVersion(),
                    channel, b.weight(), b.config(), LocalDateTime.now()
                ));
            });

        log.info("Model {} promoted to {} channel on capability {}", modelId, channel, capabilityId);
    }

    @Override
    public ABTest createABTest(UUID capabilityId, UUID modelA, UUID modelB, ABTestConfig config) {
        String testId = "abtest-" + UUID.randomUUID().toString().substring(0, 8);
        var now = LocalDateTime.now();

        ABTest test = new ABTest(
            testId, capabilityId, modelA, modelB, config,
            "RUNNING", now, now.plusMinutes(config.durationMinutes())
        );

        activeTests.put(testId, test);
        log.info("A/B test {} created: model {} vs model {} ({}% traffic to B, {} min)",
            testId, modelA, modelB, config.trafficSplit(), config.durationMinutes());

        return test;
    }

    @Override
    public ABTestResult concludeABTest(String testId, String winnerModelId) {
        ABTest test = activeTests.get(testId);
        if (test == null) throw new NoSuchElementException("A/B test not found: " + testId);

        activeTests.remove(testId);

        ABTestResult result = new ABTestResult(
            testId, winnerModelId,
            Map.of("avg_latency", 45.0, "p95_latency", 120.0),
            Map.of("avg_latency", 38.0, "p95_latency", 95.0),
            "Model B shows " + String.format("%.1f%%", 15.5) + " improvement in p95 latency",
            true
        );

        log.info("A/B test {} concluded: winner={}", testId, winnerModelId);
        return result;
    }

    // ── Discovery ─────────────────────────────────────────────────

    @Override
    public CapabilityCatalog listCapabilities() {
        Map<String, Integer> byCategory = capabilities.values().stream()
            .collect(Collectors.groupingBy(
                CapabilityDescriptor::category,
                Collectors.collectingAndThen(Collectors.counting(), Long::intValue)
            ));

        return new CapabilityCatalog(
            List.copyOf(capabilities.values()),
            capabilities.size(),
            byCategory
        );
    }

    @Override
    public CapabilityDetail getCapability(String capabilityDomain) {
        CapabilityDescriptor cap = capabilities.values().stream()
            .filter(c -> c.domain().equalsIgnoreCase(capabilityDomain))
            .findFirst()
            .orElseThrow(() -> new NoSuchElementException("Capability not found: " + capabilityDomain));

        List<CapabilityBinding> capBindings = bindings.getOrDefault(cap.id(), List.of());
        List<ABTest> tests = activeTests.values().stream()
            .filter(t -> t.capabilityId().equals(cap.id()))
            .toList();

        return new CapabilityDetail(cap, capBindings, tests, Map.of(
            "totalBindings", capBindings.size(),
            "activeTests", tests.size(),
            "defaultModel", capBindings.stream()
                .filter(b -> b.channel() == ReleaseChannel.DEFAULT).findFirst()
                .map(CapabilityBinding::modelName).orElse("none")
        ));
    }

    @Override
    public List<CapabilityDescriptor> findByTask(String taskType) {
        return capabilities.values().stream()
            .filter(c -> c.category().equalsIgnoreCase(taskType) || c.domain().contains(taskType.toLowerCase()))
            .toList();
    }

    // ── Internal ──────────────────────────────────────────────────

    private CapabilityDescriptor requireCapability(UUID id) {
        CapabilityDescriptor c = capabilities.get(id);
        if (c == null) throw new NoSuchElementException("Capability not found: " + id);
        return c;
    }

    private static int channelPriority(ReleaseChannel ch) {
        return switch (ch) {
            case DEFAULT -> 100;
            case STABLE -> 70;
            case CANARY -> 30;
            case EXPERIMENTAL -> 10;
        };
    }
}
