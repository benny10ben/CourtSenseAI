package com.courtsense.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "matches")
public class Match {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String videoFilename;
    private Integer totalShots;
    private Double durationSeconds;
    private Integer totalRallies;

    private Double avgRallyLengthSeconds;
    private String harderHitter;
    
    @Column(columnDefinition = "TEXT")
    private String geminiInsight; // Where the AI coaching feedback will live

    // Add this with your other variables in Match.java
    @Column(columnDefinition = "TEXT")
    private String rawJsonPayload;

    private LocalDateTime createdAt;

    // Default Constructor
    public Match() {
        this.createdAt = LocalDateTime.now();
    }

    // --- Getters and Setters ---
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

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
}