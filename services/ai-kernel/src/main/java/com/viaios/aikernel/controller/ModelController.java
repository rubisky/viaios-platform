package com.viaios.aikernel.controller;

import com.viaios.aikernel.domain.ModelInfo;
import com.viaios.aikernel.domain.ModelInfoRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/v1/kernel/models")
@RequiredArgsConstructor
public class ModelController {

    private final ModelInfoRepository modelInfoRepository;

    @GetMapping
public ResponseEntity<List<ModelInfo>> listModels(
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String task,
            @RequestParam(required = false) String runtime,
            @RequestParam(required = false) String status) {
        if (name != null && !name.isBlank())
            return ResponseEntity.ok(modelInfoRepository.findByNameOrderByCreatedAtDesc(name));
        if (task != null) return ResponseEntity.ok(modelInfoRepository.findByTask(task));
        if (runtime != null) return ResponseEntity.ok(modelInfoRepository.findByRuntime(runtime));
        if (status != null) return ResponseEntity.ok(modelInfoRepository.findByStatus(status));
        return ResponseEntity.ok(modelInfoRepository.findAll());
    }

    @GetMapping("/{id}")
    public ResponseEntity<ModelInfo> getModel(@PathVariable UUID id) {
        return modelInfoRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
public ResponseEntity<ModelInfo> registerModel(@RequestBody ModelInfo modelInfo) {
        if (modelInfo.getStatus() == null) modelInfo.setStatus("REGISTERED");
        return ResponseEntity.status(HttpStatus.CREATED).body(modelInfoRepository.save(modelInfo));
    }

    @PostMapping("/{id}/deploy")
public ResponseEntity<ModelInfo> deployModel(@PathVariable UUID id) {
        return modelInfoRepository.findById(id).map(model -> {
            model.setStatus("DEPLOYING");
            modelInfoRepository.save(model);
            model.setStatus("ACTIVE");
            return ResponseEntity.ok(modelInfoRepository.save(model));
        }).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/infer")
public ResponseEntity<?> infer(
            @PathVariable UUID id, @RequestBody Map<String, Object> inputs) {
        return modelInfoRepository.findById(id).map(m -> {
            if (!"ACTIVE".equals(m.getStatus()))
                return ResponseEntity.badRequest().body(Map.of("error", "model not deployed"));
            return ResponseEntity.ok(Map.of(
                "modelId", id, "modelName", m.getName(),
                "status", "completed",
                "results", List.of(Map.of("class", "person", "confidence", 0.95))
            ));
        }).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/rollback")
public ResponseEntity<Map<String, String>> rollbackModel(@PathVariable UUID id) {
        return modelInfoRepository.findById(id).map(model -> {
            model.setStatus("ROLLING_BACK");
            modelInfoRepository.save(model);
            return ResponseEntity.ok(Map.of("status", "ROLLED_BACK", "modelId", model.getId().toString()));
        }).orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteModel(@PathVariable UUID id) {
        modelInfoRepository.deleteById(id);
        return ResponseEntity.ok().build();
    }
}
