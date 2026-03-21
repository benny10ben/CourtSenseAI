package com.courtsense.repository;

import com.courtsense.model.Match;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MatchRepository extends JpaRepository<Match, Long> {
    // You can add custom search methods here later, like:
    // List<Match> findByVideoFilename(String filename);
}