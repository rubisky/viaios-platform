package com.viaios.alarmservice.controller;

import com.viaios.alarmservice.entity.Rule;
import com.viaios.alarmservice.repository.RuleRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/alarms/rules")
public class RuleController {

    private static final Logger log = LoggerFactory.getLogger(RuleController.class);
    private final RuleRepository ruleRepository;

    public RuleController(RuleRepository ruleRepository) {
        this.ruleRepository = ruleRepository;
    }

    @GetMapping
    public ResponseEntity<List<Rule>> listRules(@RequestParam(required = false) String type) {
        log.info("Listing alarm rules - type: {}", type);
        List<Rule> rules;
        if (type != null && !type.isBlank()) {
            rules = ruleRepository.findByType(type);
        } else {
            rules = ruleRepository.findAll();
        }
        return ResponseEntity.ok(rules);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Rule> getRule(@PathVariable Long id) {
        log.info("Fetching rule: {}", id);
        return ruleRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Rule> createRule(@Valid @RequestBody CreateRuleRequest request) {
        log.info("Creating rule: {}", request.getName());

        Rule rule = new Rule();
        rule.setName(request.getName());
        rule.setType(request.getType());
        rule.setCondition(request.getCondition());
        rule.setAction(request.getAction());
        rule.setEnabled(request.getEnabled() != null ? request.getEnabled() : true);

        Rule saved = ruleRepository.save(rule);
        log.info("Rule created with id: {}", saved.getId());
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Rule> updateRule(@PathVariable Long id, @Valid @RequestBody UpdateRuleRequest request) {
        log.info("Updating rule: {}", id);
        return ruleRepository.findById(id)
                .map(r -> {
                    if (request.getName() != null) r.setName(request.getName());
                    if (request.getType() != null) r.setType(request.getType());
                    if (request.getCondition() != null) r.setCondition(request.getCondition());
                    if (request.getAction() != null) r.setAction(request.getAction());
                    if (request.getEnabled() != null) r.setEnabled(request.getEnabled());
                    Rule updated = ruleRepository.save(r);
                    return ResponseEntity.ok(updated);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, Object>> deleteRule(@PathVariable Long id) {
        log.info("Deleting rule: {}", id);
        if (!ruleRepository.existsById(id)) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of("error", "Rule not found", "ruleId", id));
        }
        ruleRepository.deleteById(id);
        return ResponseEntity.ok(Map.of("message", "Rule deleted", "ruleId", id));
    }

    @PatchMapping("/{id}/toggle")
    public ResponseEntity<Rule> toggleRule(@PathVariable Long id) {
        log.info("Toggling rule: {}", id);
        return ruleRepository.findById(id)
                .map(r -> {
                    r.setEnabled(!r.getEnabled());
                    Rule saved = ruleRepository.save(r);
                    log.info("Rule {} toggled to enabled={}", id, saved.getEnabled());
                    return ResponseEntity.ok(saved);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/enabled")
    public ResponseEntity<List<Rule>> getEnabledRules() {
        log.info("Fetching enabled rules");
        return ResponseEntity.ok(ruleRepository.findByEnabledTrue());
    }

    // --- Request DTOs ---

    public static class CreateRuleRequest {
        @NotBlank(message = "Name is required")
        @Size(max = 100, message = "Name must not exceed 100 characters")
        private String name;

        @NotBlank(message = "Type is required")
        private String type;

        @NotBlank(message = "Condition is required")
        private String condition;

        @NotBlank(message = "Action is required")
        private String action;

        private Boolean enabled;

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getCondition() { return condition; }
        public void setCondition(String condition) { this.condition = condition; }
        public String getAction() { return action; }
        public void setAction(String action) { this.action = action; }
        public Boolean getEnabled() { return enabled; }
        public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    }

    public static class UpdateRuleRequest {
        private String name;
        private String type;
        private String condition;
        private String action;
        private Boolean enabled;

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getCondition() { return condition; }
        public void setCondition(String condition) { this.condition = condition; }
        public String getAction() { return action; }
        public void setAction(String action) { this.action = action; }
        public Boolean getEnabled() { return enabled; }
        public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    }
}
