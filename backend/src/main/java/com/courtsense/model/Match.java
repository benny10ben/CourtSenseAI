package com.courtsense.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "matches")
public class Match {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ── NEW: ties this match to a browser session ──────────────────────────
    @Column(nullable = false)
    private String sessionId;
    // ───────────────────────────────────────────────────────────────────────

    private String videoFilename;
    private Integer totalShots;
    private Double durationSeconds;
    private Integer totalRallies;

    private String jobId;
    private String status;

    private Double avgRallyLengthSeconds;
    private String harderHitter;

    @Column(columnDefinition = "TEXT")
    private String geminiInsight;

    @Column(columnDefinition = "TEXT")
    private String rawJsonPayload;

    private String heatmapUrl;

    private LocalDateTime createdAt;

    public Match() {
        this.createdAt = LocalDateTime.now();
    }

    // --- Getters and Setters ---

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    // ── NEW ────────────────────────────────────────────────────────────────
    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }
    // ───────────────────────────────────────────────────────────────────────

    public String getVideoFilename() { return videoFilename; }
    public void setVideoFilename(String videoFilename) { this.videoFilename = videoFilename; }

    public Integer getTotalShots() { return totalShots; }
    public void setTotalShots(Integer totalShots) { this.totalShots = totalShots; }

    public Double getDurationSeconds() { return durationSeconds; }
    public void setDurationSeconds(Double durationSeconds) { this.durationSeconds = durationSeconds; }

    public Integer getTotalRallies() { return totalRallies; }
    public void setTotalRallies(Integer totalRallies) { this.totalRallies = totalRallies; }

    public String getGeminiInsight() { return geminiInsight; }
    public void setGeminiInsight(String geminiInsight) { this.geminiInsight = geminiInsight; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public Double getAvgRallyLengthSeconds() { return avgRallyLengthSeconds; }
    public void setAvgRallyLengthSeconds(Double avgRallyLengthSeconds) { this.avgRallyLengthSeconds = avgRallyLengthSeconds; }

    public String getHarderHitter() { return harderHitter; }
    public void setHarderHitter(String harderHitter) { this.harderHitter = harderHitter; }

    public String getRawJsonPayload() { return rawJsonPayload; }
    public void setRawJsonPayload(String rawJsonPayload) { this.rawJsonPayload = rawJsonPayload; }

    public String getHeatmapUrl() { return heatmapUrl; }
    public void setHeatmapUrl(String heatmapUrl) { this.heatmapUrl = heatmapUrl; }

    public String getJobId() { return jobId; }
    public void setJobId(String jobId) { this.jobId = jobId; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}