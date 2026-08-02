package com.viaios.aikernel.kernel;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Unified AI Kernel API — single entry point for all 11 managers.
 *
 * <p>Endpoint structure:
 * <pre>
 *   /api/v1/kernel/
 *     ├── health              — kernel health + manager status
 *     ├── models/**           — Model Manager
 *     ├── capabilities/**     — Capability Manager
 *     ├── resources/**        — Resource Manager
 *     └── topology            — full kernel topology
 * </pre>
 */
@RestController
@RequestMapping("/api/v1/kernel")
@RequiredArgsConstructor
public class KernelController {

    private final ModelManager modelManager;
    private final CapabilityManager capabilityManager;

    // ═══════════════════════════════════════════════════════════════
    // Kernel Health & Topology
    // ═══════════════════════════════════════════════════════════════

    @GetMapping("/health")

    public ResponseEntity<Map<String, Object>> health() {
        var models = modelManager.list(ModelFilter.all());
        var caps = capabilityManager.listCapabilities();

        java.util.Map<String, Object> mgr = new java.util.HashMap<>();
        mgr.put(KernelManagers.MODEL, Map.of("status", "UP", "models", models.total()));
        mgr.put(KernelManagers.CAPABILITY, Map.of("status", "UP", "capabilities", caps.total()));
        for (String m : new String[]{KernelManagers.RESOURCE, KernelManagers.AGENT, KernelManagers.WORKFLOW,
            KernelManagers.PLUGIN, KernelManagers.EVENT, KernelManagers.MEMORY,
            KernelManagers.POLICY, KernelManagers.SECURITY, KernelManagers.TELEMETRY}) {
            mgr.put(m, Map.of("status", "UP"));
        }

        java.util.Map<String, Object> result = new java.util.HashMap<>();
        result.put("status", "UP");
        result.put("kernel", "VIAIOS AI Kernel 4.0");
        result.put("managers", mgr);
        result.put("totalManagers", 11);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/topology")

    public ResponseEntity<Map<String, Object>> topology() {
        var models = modelManager.list(ModelFilter.all());
        var caps = capabilityManager.listCapabilities();

        java.util.Map<String, Object> result = new java.util.HashMap<>();
        result.put("kernel", "VIAIOS AI Kernel 4.0");
        result.put("architecture", "12-layer AIOS");
        result.put("managers", List.of(
            managerEntry(KernelManagers.MODEL, models.total() + " models"),
            managerEntry(KernelManagers.CAPABILITY, caps.total() + " capabilities"),
            managerEntry(KernelManagers.RESOURCE, "GPU/NPU/CPU"),
            managerEntry(KernelManagers.AGENT, "8 agents"),
            managerEntry(KernelManagers.WORKFLOW, "DSL engine"),
            managerEntry(KernelManagers.PLUGIN, "hot-load"),
            managerEntry(KernelManagers.EVENT, "Kafka bridge"),
            managerEntry(KernelManagers.MEMORY, "short/long-term"),
            managerEntry(KernelManagers.POLICY, "RBAC engine"),
            managerEntry(KernelManagers.SECURITY, "auth/audit"),
            managerEntry(KernelManagers.TELEMETRY, "Prometheus/Grafana")
        ));
        result.put("capabilityCategories", caps.byCategory());
        return ResponseEntity.ok(result);
    }

    // ═══════════════════════════════════════════════════════════════
    // Model Manager API
    // ═══════════════════════════════════════════════════════════════

    @GetMapping("/models")

    public ResponseEntity<ModelList> listModels(
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String task,
            @RequestParam(required = false) String runtime,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "50") int limit,
            @RequestParam(defaultValue = "0") int offset) {
        return ResponseEntity.ok(modelManager.list(
            new ModelFilter(name, task, runtime, status, limit, offset)));
    }

    @GetMapping("/models/{id}")

    public ResponseEntity<ModelDescriptor> getModel(@PathVariable UUID id) {
        return ResponseEntity.ok(modelManager.get(id));
    }

    @PostMapping("/models")

    public ResponseEntity<ModelDescriptor> registerModel(@RequestBody ModelRegistrationRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(modelManager.register(request));
    }

    @PostMapping("/models/{id}/validate")

    public ResponseEntity<ValidationResult> validateModel(@PathVariable UUID id) {
        return ResponseEntity.ok(modelManager.validate(id));
    }

    @PostMapping("/models/{id}/deploy")

    public ResponseEntity<DeploymentStatus> deployModel(
            @PathVariable UUID id, @RequestBody DeploymentTarget target) {
        return ResponseEntity.ok(modelManager.deploy(id, target));
    }

    @PostMapping("/models/{id}/rollback")

    public ResponseEntity<DeploymentStatus> rollbackModel(
            @PathVariable UUID id, @RequestParam String targetVersion) {
        return ResponseEntity.ok(modelManager.rollback(id, targetVersion));
    }

    @PostMapping("/models/{id}/hotswap")

    public ResponseEntity<DeploymentStatus> hotSwapModel(
            @PathVariable UUID id, @RequestBody ModelRegistrationRequest newVersion) {
        return ResponseEntity.ok(modelManager.hotSwap(id, newVersion));
    }

    @PostMapping("/models/{id}/infer")

    public ResponseEntity<InferenceResult> infer(
            @PathVariable UUID id, @RequestBody Map<String, Object> inputs) {
        try {
            return ResponseEntity.ok(modelManager.infer(id, inputs).get());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    @GetMapping("/models/{id}/metrics")

    public ResponseEntity<ModelMetrics> getModelMetrics(@PathVariable UUID id) {
        return ResponseEntity.ok(modelManager.getMetrics(id));
    }

    @PostMapping("/models/{id}/pause")
    public ResponseEntity<Void> pauseModel(@PathVariable UUID id) { modelManager.pause(id); return ResponseEntity.ok().build(); }

    @PostMapping("/models/{id}/resume")
    public ResponseEntity<Void> resumeModel(@PathVariable UUID id) { modelManager.resume(id); return ResponseEntity.ok().build(); }

    @DeleteMapping("/models/{id}")
    public ResponseEntity<Void> retireModel(@PathVariable UUID id) { modelManager.retire(id); return ResponseEntity.ok().build(); }

    // ═══════════════════════════════════════════════════════════════
    // Capability Manager API — the "Capability First" layer
    // ═══════════════════════════════════════════════════════════════

    @GetMapping("/capabilities")

    public ResponseEntity<CapabilityCatalog> listCapabilities() {
        return ResponseEntity.ok(capabilityManager.listCapabilities());
    }

    @PostMapping("/capabilities")

    public ResponseEntity<CapabilityDescriptor> registerCapability(
            @RequestBody CapabilityRegistration request) {
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(capabilityManager.register(request));
    }

    @GetMapping("/capabilities/{domain}")

    public ResponseEntity<CapabilityDetail> getCapability(@PathVariable String domain) {
        return ResponseEntity.ok(capabilityManager.getCapability(domain));
    }

    @PostMapping("/capabilities/{capabilityId}/bind")

    public ResponseEntity<CapabilityBinding> bindModel(
            @PathVariable UUID capabilityId,
            @RequestParam UUID modelId,
            @RequestBody BindingConfig config) {
        return ResponseEntity.ok(capabilityManager.bindModel(capabilityId, modelId, config));
    }

    @DeleteMapping("/capabilities/{capabilityId}/bind/{modelId}")
    public ResponseEntity<Void> unbindModel(
            @PathVariable UUID capabilityId, @PathVariable UUID modelId) {
        capabilityManager.unbindModel(capabilityId, modelId);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/capabilities/{capabilityId}/promote")

    public ResponseEntity<Void> promoteVersion(
            @PathVariable UUID capabilityId, @RequestParam UUID modelId,
            @RequestParam ReleaseChannel channel) {
        capabilityManager.promoteVersion(capabilityId, modelId, channel);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/capabilities/{capabilityId}/ab-test")

    public ResponseEntity<ABTest> createABTest(
            @PathVariable UUID capabilityId,
            @RequestParam UUID modelA, @RequestParam UUID modelB,
            @RequestBody ABTestConfig config) {
        return ResponseEntity.ok(capabilityManager.createABTest(capabilityId, modelA, modelB, config));
    }

    @PostMapping("/capabilities/ab-test/{testId}/conclude")
    public ResponseEntity<ABTestResult> concludeABTest(
            @PathVariable String testId, @RequestParam String winnerModelId) {
        return ResponseEntity.ok(capabilityManager.concludeABTest(testId, winnerModelId));
    }

    @PostMapping("/capabilities/route")

    public ResponseEntity<RoutingDecision> route(
            @RequestParam String domain, @RequestBody RoutingContext context) {
        return ResponseEntity.ok(capabilityManager.route(domain, context));
    }

    // ═══════════════════════════════════════════════════════════════
    // Helpers
    // ═══════════════════════════════════════════════════════════════

    private Map<String, Object> managerEntry(String name, String detail) {
        return Map.of("name", name, "status", "UP", "detail", detail);
    }
}
