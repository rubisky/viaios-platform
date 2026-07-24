package com.viaios.reportservice.repository;

import com.viaios.reportservice.entity.Template;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TemplateRepository extends JpaRepository<Template, Long> {

    Optional<Template> findByNameAndVersion(String name, Integer version);

    List<Template> findByNameOrderByVersionDesc(String name);

    List<Template> findByType(String type);

    Page<Template> findByType(String type, Pageable pageable);

    Optional<Template> findTopByNameOrderByVersionDesc(String name);
}
