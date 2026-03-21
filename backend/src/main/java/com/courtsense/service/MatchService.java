package com.courtsense.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.courtsense.model.Match;
import com.courtsense.repository.MatchRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;

@Service
public class MatchService {

    @Autowired
    private MatchRepository matchRepository;

    // ADD THIS LINE - This tells Spring to connect the two services
    @Autowired
    private GeminiService geminiService; 

    private final ObjectMapper objectMapper = new ObjectMapper();

    public Match processPythonOutput(String filePath, String videoName) throws IOException {
        File jsonFile = new File(filePath);
        JsonNode root = objectMapper.readTree(jsonFile);
        JsonNode summary = root.path("match_summary");

        Match match = new Match();
        match.setVideoFilename(videoName);
        match.setTotalShots(summary.path("total_shots").asInt());
        match.setDurationSeconds(summary.path("duration_seconds").asDouble());
        match.setTotalRallies(summary.path("total_rallies").asInt());

        // Extracting stats
        match.setAvgRallyLengthSeconds(summary.path("avg_rally_length_seconds").asDouble());
        match.setHarderHitter(root.path("speed_comparison").path("harder_hitter").asText());

        // Save the raw minified JSON (Everything inside player dictionaries)
        match.setRawJsonPayload(root.toString());

        // 1. Generate the Prompt
        // 2. GET THE LIVE AI RESPONSE
        String aiResponse = geminiService.getLiveCoaching(match);
        
        // 3. Save the actual advice to the database, NOT the prompt
        match.setGeminiInsight(aiResponse);
        // Save to Postgres
        return matchRepository.save(match);
    }
}