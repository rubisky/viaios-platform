package com.viaios.caseservice.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "evidence")
public class Evidence {
    @Id @GeneratedValue
    private UUID id;

    @Column(name = "case_id")
    private UUID caseId;

    private String type = "IMAGE";
    private String title;
    private String url;
    private String source;

    @Column(name = "created_at")
    private Instant createdAt = Instant.now();

    public Evidence() {}

    public UUID getId() { return id; }
    public UUID getCaseId() { return caseId; }
    public void setCaseId(UUID c) { caseId = c; }
    public String getType() { return type; }
    public void setType(String t) { type = t; }
    public String getTitle() { return title; }
    public void setTitle(String t) { title = t; }
    public String getUrl() { return url; }
    public void setUrl(String u) { url = u; }
    public String getSource() { return source; }
    public void setSource(String s) { source = s; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant t) { createdAt = t; }
}
