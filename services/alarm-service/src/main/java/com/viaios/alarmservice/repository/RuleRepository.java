package com.viaios.alarmservice.repository;

import com.viaios.alarmservice.entity.Rule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RuleRepository extends JpaRepository<Rule, Long> {

    List<Rule> findByEnabledTrue();

    List<Rule> findByType(String type);

    List<Rule> findByNameContainingIgnoreCase(String name);

    long countByEnabledTrue();
}
