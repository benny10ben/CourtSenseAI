package com.courtsense.service;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;

@Service
public class FileStorageService {

    // Root that all session folders live under
    // Structure: ../data/sessions/{sessionId}/input/
    //                                         /output/
    //                                         /assets/
    private static final Path SESSIONS_ROOT =
            Paths.get("../data/sessions").toAbsolutePath().normalize();

    public FileStorageService() {
        try {
            Files.createDirectories(SESSIONS_ROOT);
        } catch (Exception ex) {
            throw new RuntimeException("Could not create sessions root directory.", ex);
        }
    }

    /**
     * Returns the absolute path to a session's input directory,
     * creating it (and the sibling output/ and assets/ dirs) if they don't exist.
     */
    public Path getOrCreateSessionDirs(String sessionId) {
        try {
            Path sessionRoot = SESSIONS_ROOT.resolve(sessionId).normalize();
            Path inputDir    = sessionRoot.resolve("input");
            Path outputDir   = sessionRoot.resolve("output");
            Path assetsDir   = sessionRoot.resolve("assets");

            Files.createDirectories(inputDir);
            Files.createDirectories(outputDir);
            Files.createDirectories(assetsDir);

            return sessionRoot;
        } catch (IOException ex) {
            throw new RuntimeException("Could not create session directories for: " + sessionId, ex);
        }
    }

    /**
     * Saves the uploaded video into ../data/sessions/{sessionId}/input/
     * and returns its absolute path string (passed to Python as --video).
     */
    public String storeFile(MultipartFile file, String sessionId) {
        try {
            Path inputDir = getOrCreateSessionDirs(sessionId).resolve("input");

            String originalFileName = file.getOriginalFilename();

            // Timestamp prefix prevents collisions if the same filename is uploaded twice
            String newFileName = System.currentTimeMillis() + "_" + originalFileName;

            Path targetLocation = inputDir.resolve(newFileName);
            Files.copy(file.getInputStream(), targetLocation, StandardCopyOption.REPLACE_EXISTING);

            return targetLocation.toString();

        } catch (IOException ex) {
            throw new RuntimeException(
                "Could not store file " + file.getOriginalFilename() + ". Please try again!", ex);
        }
    }

    /**
     * Returns the absolute path to the session's output directory.
     * Python writes all CSVs, heatmap, and coaching_payload.json here.
     */
    public Path getOutputDir(String sessionId) {
        return SESSIONS_ROOT.resolve(sessionId).resolve("output").normalize();
    }

    /**
     * Returns the absolute path to the session's assets directory.
     * Python copies the working video here (replaces the global assets/badminton.mp4).
     */
    public Path getAssetsDir(String sessionId) {
        return SESSIONS_ROOT.resolve(sessionId).resolve("assets").normalize();
    }
}