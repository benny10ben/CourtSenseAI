package com.courtsense.repository;

import com.courtsense.model.Match;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional; // <-- ADDED IMPORT

import java.util.List;
import java.util.Optional;

@Repository
public interface MatchRepository extends JpaRepository<Match, Long> {

    // Existing — find a job regardless of session (used by background thread)
    Optional<Match> findByJobId(String jobId);

    // ── NEW ────────────────────────────────────────────────────────────────

    // Dashboard: fetch only this browser's matches
    List<Match> findBySessionId(String sessionId);

    // Cleanup: wipe all previous matches for this session before a new upload
    @Transactional // <-- ADDED PERMISSION SLIP HERE
    void deleteBySessionId(String sessionId);

    // Safety check: confirm a jobId actually belongs to the session polling it
    Optional<Match> findByJobIdAndSessionId(String jobId, String sessionId);

    // ───────────────────────────────────────────────────────────────────────
}