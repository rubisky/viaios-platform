package com.viaios.search.repository;

import com.viaios.search.entity.SearchHistory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SearchHistoryRepository extends JpaRepository<SearchHistory, Long> {

    List<SearchHistory> findByUserIdOrderByCreatedAtDesc(String userId);

    Page<SearchHistory> findByUserId(String userId, Pageable pageable);

    List<SearchHistory> findByQueryTypeOrderByCreatedAtDesc(String queryType);

    Page<SearchHistory> findByUserIdAndQueryType(String userId, String queryType, Pageable pageable);

    void deleteByUserId(String userId);
}
