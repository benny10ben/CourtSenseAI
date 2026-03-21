package com.courtsense.controller;

import com.courtsense.model.Match;
import com.courtsense.repository.MatchRepository;
import com.courtsense.service.MatchService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.util.List;

@RestController
@RequestMapping("/api/matches")
public class MatchController {

    @Autowired
    private MatchRepository matchRepository;

    @Autowired
    private MatchService matchService;

    @Value("${INTERNAL_SECRET_KEY}")
    private String internalSecret;

    @GetMapping
    public List<Match> getAllMatches() {
        return matchRepository.findAll();
    }

    @Value("${courtsense.pipeline.output.path}")
    private String payloadPath;

    @Value("${courtsense.pipeline.video.name}")
    private String videoName;

    @PostMapping("/process-latest")
    public ResponseEntity<?> processLatest(@RequestHeader(value = "X-Internal-Secret", required = false) String secret) throws IOException {
        
        // SECURITY GATEKEEPER: If the secret header is missing or wrong, block the request
        if (secret == null || !secret.equals(internalSecret)) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                                 .body("Error: Unauthorized. Scrapers not allowed!");
        }

        // Relative path from the backend folder to your data output
        Match savedMatch = matchService.processPythonOutput(payloadPath, videoName);

        return ResponseEntity.ok(savedMatch);
    }
}