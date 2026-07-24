package com.viaios.caseservice.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "cases")
public class CaseEntity {
    @Id @GeneratedValue
    private UUID id;

    private String title;
    private String description;
    private String status = "NEW";
    private String priority = "P2";

    @Column(name = "created_at")
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at")
    private Instant updatedAt;

    public CaseEntity() {}

    public UUID getId() { return id; }
    public String getTitle() { return title; }
    public void setTitle(String t) { title = t; }
    public String getDescription() { return description; }
    public void setDescription(String d) { description = d; }
    public String getStatus() { return status; }
    public void setStatus(String s) { status = s; }
    public String getPriority() { return priority; }
    public void setPriority(String p) { priority = p; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant t) { createdAt = t; }
    public Instant getUpdatedAt() { return updatedAt; }
}
