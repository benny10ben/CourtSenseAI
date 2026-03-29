package com.courtsense.controller;

import com.courtsense.model.Match;
import com.courtsense.repository.MatchRepository;
import com.courtsense.service.FileStorageService;
import com.courtsense.service.MatchService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import jakarta.servlet.http.HttpServletRequest;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@RestController
@RequestMapping("/api/matches")
public class MatchController {

    @Autowired
    private MatchRepository matchRepository;

    @Autowired
    private MatchService matchService;

    @Autowired
    private FileStorageService fileStorageService;

    @Value("${INTERNAL_SECRET_KEY}")
    private String internalSecret;

    @GetMapping
    public List<Match> getAllMatches(HttpServletRequest request) {
        String sessionId = (String) request.getAttribute("sessionId");
        return matchRepository.findBySessionId(sessionId);
    }

    // ==========================================
    // POST /api/matches/upload
    // ==========================================
    @PostMapping("/upload")
    // BUG FIX 1: Removed @Transactional from here to prevent the Race Condition!
    public ResponseEntity<?> uploadVideo(
            @RequestParam("video") MultipartFile file,
            @RequestParam("coords") String coordsJson,
            @RequestHeader(value = "X-Internal-Secret", required = false) String secret,
            HttpServletRequest request) {

        if (secret == null || !secret.equals(internalSecret)) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body("Error: Unauthorized.");
        }

        String sessionId = (String) request.getAttribute("sessionId");

        try {
            cleanupSession(sessionId);
            System.out.println("🧹 Cleaned up previous data for session: " + sessionId);

            Path sessionRoot = fileStorageService.getOrCreateSessionDirs(sessionId);
            Path outputDir   = fileStorageService.getOutputDir(sessionId);
            
            String payloadPath = outputDir.resolve("coaching_payload.json").toString();
            String jobId = UUID.randomUUID().toString();
            System.out.println("📥 New upload for session " + sessionId + " | Job: " + jobId);

            // BUG FIX 2: Extract the filename NOW before the HTTP request dies!
            String originalFilename = file.getOriginalFilename();

            // Save the match immediately so the async thread can find it if it crashes
            Match pendingMatch = new Match();
            pendingMatch.setSessionId(sessionId);
            pendingMatch.setJobId(jobId);
            pendingMatch.setStatus("PROCESSING");
            pendingMatch.setVideoFilename(originalFilename);
            matchRepository.save(pendingMatch);

            String savedVideoPath = fileStorageService.storeFile(file, sessionId);
            
            // BUG FIX 3: Force the video path to be Absolute so Python doesn't get lost
            String absoluteVideoPath = Paths.get(savedVideoPath).toAbsolutePath().normalize().toString();

            String jsonFilename = "coords_" + jobId + ".json";
            Path jsonPath = sessionRoot.resolve("input").resolve(jsonFilename).normalize().toAbsolutePath();
            Files.writeString(jsonPath, coordsJson);

            // ── FIRE AND FORGET ──
            CompletableFuture.runAsync(() -> {
                try {
                    System.out.println("🚀 Booting pipeline | Session: " + sessionId + " | Job: " + jobId);

                    ProcessBuilder pb = new ProcessBuilder(
                        "venv_stable/bin/python", "pipeline/run_pipeline.py",
                        "--coords",      jsonPath.toString(),
                        "--video",       absoluteVideoPath, // <-- Passed absolute path!
                        "--session-dir", sessionRoot.toAbsolutePath().toString()
                    );
                    pb.directory(new File("../"));
                    pb.redirectErrorStream(true);

                    Process process = pb.start();
                    try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                        String line;
                        while ((line = reader.readLine()) != null) {
                            System.out.println("[" + sessionId.substring(0, 8) + "/" + jobId.substring(0, 8) + "] " + line);
                        }
                    }

                    int exitCode = process.waitFor();
                    if (exitCode != 0) throw new RuntimeException("Python pipeline exited with code " + exitCode);

                    // Pass the safe originalFilename instead of the dead 'file' object
                    matchService.processPythonOutput(payloadPath, originalFilename, jobId, sessionId);

                    Files.deleteIfExists(jsonPath);

                } catch (Exception e) {
                    System.err.println("❌ Pipeline failed | Session: " + sessionId + " | Job: " + jobId + " | " + e.getMessage());
                    // Because @Transactional is gone, this lookup will now successfully find the row!
                    matchRepository.findByJobId(jobId).ifPresent(m -> {
                        m.setStatus("FAILED");
                        matchRepository.save(m);
                    });
                }
            });

            return ResponseEntity.accepted().body(Map.of(
                "jobId",   jobId,
                "status",  "PROCESSING",
                "message", "Pipeline started in the background."
            ));

        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                                 .body("Upload failed: " + e.getMessage());
        }
    }

    @GetMapping("/status/{jobId}")
    public ResponseEntity<?> getJobStatus(@PathVariable String jobId, HttpServletRequest request) {
        String sessionId = (String) request.getAttribute("sessionId");
        Optional<Match> matchOpt = matchRepository.findByJobIdAndSessionId(jobId, sessionId);

        if (matchOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", "Job not found for this session."));
        }

        Match match = matchOpt.get();
        return ResponseEntity.ok(Map.of(
            "jobId",  match.getJobId(),
            "status", match.getStatus(),
            "match",  match
        ));
    }

    private void cleanupSession(String sessionId) {
        matchRepository.deleteBySessionId(sessionId);
        Path sessionDir = fileStorageService.getOrCreateSessionDirs(sessionId).getParent().resolve(sessionId);
        deleteDirectoryRecursively(sessionDir.toFile());
        System.out.println("🗑️  Deleted session directory: " + sessionDir);
    }

    private void deleteDirectoryRecursively(File dir) {
        if (dir == null || !dir.exists()) return;
        File[] contents = dir.listFiles();
        if (contents != null) {
            for (File f : contents) {
                deleteDirectoryRecursively(f);
            }
        }
        dir.delete();
    }
}