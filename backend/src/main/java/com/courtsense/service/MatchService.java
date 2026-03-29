package com.courtsense.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.courtsense.model.Match;
import com.courtsense.repository.MatchRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.io.IOException;
import java.nio.file.Path;

@Service
public class MatchService {

    @Autowired
    private MatchRepository matchRepository;

    @Autowired
    private GeminiService geminiService;

    @Autowired
    private FileStorageService fileStorageService;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${app.base-url}")
    private String baseUrl;

    /**
     * Called by the background thread once Python finishes successfully.
     *
     * @param payloadPath  absolute path to coaching_payload.json inside the session's output dir
     * @param videoName    original upload filename (for display)
     * @param jobId        UUID that identifies this specific pipeline run
     * @param sessionId    UUID that identifies the browser session (user)
     */
    @Transactional
    public Match processPythonOutput(
            String payloadPath,
            String videoName,
            String jobId,
            String sessionId) throws IOException {

        // ── 1. Find the PROCESSING placeholder created during upload ──────────
        Match match = matchRepository.findByJobId(jobId)
                .orElseThrow(() -> new RuntimeException("Job ID not found in DB: " + jobId));

        // ── 2. Parse Python's coaching_payload.json ───────────────────────────
        File jsonFile = new File(payloadPath);
        JsonNode root    = objectMapper.readTree(jsonFile);
        JsonNode summary = root.path("match_summary");

        match.setTotalShots(summary.path("total_shots").asInt());
        match.setDurationSeconds(summary.path("duration_seconds").asDouble());
        match.setTotalRallies(summary.path("total_rallies").asInt());
        match.setAvgRallyLengthSeconds(summary.path("avg_rally_length_seconds").asDouble());
        match.setHarderHitter(root.path("speed_comparison").path("harder_hitter").asText());
        match.setRawJsonPayload(root.toString());

        // ── 3. Call Gemini for coaching insight ───────────────────────────────
        String aiResponse = geminiService.getLiveCoaching(match);
        match.setGeminiInsight(aiResponse);

        // ── 4. Rename the heatmap from temp name to a job-scoped permanent name ──
        //      Python writes to: {sessionDir}/output/player_heatmap.png  (temp)
        //      We rename it to:  {sessionDir}/output/heatmap_{jobId}.png (permanent)
        Path outputDir   = fileStorageService.getOutputDir(sessionId);
        File tempHeatmap = outputDir.resolve("player_heatmap.png").toFile();

        if (tempHeatmap.exists()) {
            String newFilename       = "heatmap_" + jobId + ".png";
            File   permanentHeatmap  = outputDir.resolve(newFilename).toFile();

            boolean renamed = tempHeatmap.renameTo(permanentHeatmap);
            if (renamed) {
                // URL served via WebConfig's /media/** handler.
                // WebConfig maps /media/** → ../data/sessions/
                // So the URL must include the /output/ segment to reach the file:
                //   URL:  /media/{sessionId}/output/heatmap_{jobId}.png
                //   File: ../data/sessions/{sessionId}/output/heatmap_{jobId}.png
                match.setHeatmapUrl(baseUrl + "/media/" + sessionId + "/output/" + newFilename);
            } else {
                System.err.println("⚠️  Could not rename heatmap for job " + jobId);
            }
        } else {
            System.err.println("⚠️  No heatmap found at: " + tempHeatmap.getAbsolutePath());
        }

        // ── 5. Mark as done ───────────────────────────────────────────────────
        match.setStatus("COMPLETED");
        return matchRepository.save(match);
    }
}