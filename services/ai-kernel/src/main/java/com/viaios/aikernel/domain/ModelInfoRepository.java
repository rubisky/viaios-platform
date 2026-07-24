package com.viaios.aikernel.domain;

import com.viaios.aikernel.domain.ModelInfo;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ModelInfoRepository extends JpaRepository<ModelInfo, UUID> {
    List<ModelInfo> findByNameOrderByCreatedAtDesc(String name);
    Optional<ModelInfo> findByNameAndVersion(String name, String version);
    List<ModelInfo> findByStatus(String status);
    List<ModelInfo> findByTask(String task);
    List<ModelInfo> findByRuntime(String runtime);
    Optional<ModelInfo> findTopByNameOrderByCreatedAtDesc(String name);
}
