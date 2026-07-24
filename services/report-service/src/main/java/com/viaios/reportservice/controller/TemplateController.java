package com.viaios.reportservice.controller;

import com.viaios.reportservice.entity.Template;
import com.viaios.reportservice.repository.TemplateRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/reports/templates")
public class TemplateController {

    private static final Logger log = LoggerFactory.getLogger(TemplateController.class);
    private final TemplateRepository templateRepository;

    public TemplateController(TemplateRepository templateRepository) {
        this.templateRepository = templateRepository;
    }

    @GetMapping
    public ResponseEntity<Page<Template>> listTemplates(
            @RequestParam(required = false) String type,
            Pageable pageable) {
        log.info("Listing templates - type: {}", type);
        Page<Template> page;
        if (type != null && !type.isBlank()) {
            page = templateRepository.findByType(type, pageable);
        } else {
            page = templateRepository.findAll(pageable);
        }
        return ResponseEntity.ok(page);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Template> getTemplate(@PathVariable Long id) {
        log.info("Fetching template: {}", id);
        return templateRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Template> createTemplate(@Valid @RequestBody CreateTemplateRequest request) {
        log.info("Creating template: {}", request.getName());

        Template template = new Template();
        template.setName(request.getName());
        template.setType(request.getType());
        template.setContent(request.getContent());
        template.setVersion(1);

        // Check for existing versions and bump
        templateRepository.findTopByNameOrderByVersionDesc(request.getName())
                .ifPresent(latest -> template.setVersion(latest.getVersion() + 1));

        Template saved = templateRepository.save(template);
        log.info("Template created with id: {}, version: {}", saved.getId(), saved.getVersion());
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Template> updateTemplate(@PathVariable Long id, @Valid @RequestBody UpdateTemplateRequest request) {
        log.info("Updating template: {}", id);
        return templateRepository.findById(id)
                .map(t -> {
                    if (request.getName() != null) t.setName(request.getName());
                    if (request.getContent() != null) t.setContent(request.getContent());
                    if (request.getType() != null) t.setType(request.getType());
                    t.setVersion(t.getVersion() + 1);
                    Template updated = templateRepository.save(t);
                    return ResponseEntity.ok(updated);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/search")
    public ResponseEntity<List<Template>> searchByName(@RequestParam String name) {
        log.info("Searching templates by name: {}", name);
        return ResponseEntity.ok(templateRepository.findByNameOrderByVersionDesc(name));
    }

    // --- Request DTOs ---

    public static class CreateTemplateRequest {
        @NotBlank(message = "Name is required")
        @Size(max = 100, message = "Name must not exceed 100 characters")
        private String name;

        @NotBlank(message = "Type is required")
        private String type;

        @NotBlank(message = "Content is required")
        private String content;

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getContent() { return content; }
        public void setContent(String content) { this.content = content; }
    }

    public static class UpdateTemplateRequest {
        private String name;
        private String type;
        private String content;

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getContent() { return content; }
        public void setContent(String content) { this.content = content; }
    }
}
