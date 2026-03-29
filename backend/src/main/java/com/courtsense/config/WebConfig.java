package com.courtsense.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.nio.file.Path;
import java.nio.file.Paths;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    // ==========================================
    // 1. THE CORS BOUNCER (NEW)
    // ==========================================
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins("http://localhost:3000") // Trust Next.js
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowCredentials(true); // Allow the Session Cookie to pass through!
    }

    // ==========================================
    // 2. THE MEDIA FILE SERVER (EXISTING)
    // ==========================================
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // Resolve the absolute path to the sessions root on disk
        Path sessionsRoot = Paths.get("../data/sessions").toAbsolutePath().normalize();

        // Map:  GET /media/{sessionId}/heatmap_xyz.png
        // To:   ../data/sessions/{sessionId}/output/heatmap_xyz.png
        //
        // Spring's resource handler treats the ** wildcard portion as the file path
        // within the mapped location, so the URL naturally scopes per session.
        //
        // Example:
        //   URL:  http://localhost:8080/media/aaa-111/heatmap_jobId.png
        //   File: ../data/sessions/aaa-111/output/heatmap_jobId.png
        //
        // This replaces the old flat /media/** → ../data/output/ mapping.
        registry.addResourceHandler("/media/**")
                .addResourceLocations("file:" + sessionsRoot + "/")
                .resourceChain(false);
        // Note: Spring resolves /media/aaa-111/heatmap.png as
        //       sessionsRoot + "/aaa-111/heatmap.png"
        // We store heatmaps at sessionsRoot/{sessionId}/output/heatmap.png,
        // so the URL we store in the DB includes the /output/ segment:
        //   http://localhost:8080/media/aaa-111/output/heatmap_jobId.png
        // MatchService builds the URL to match this exactly.
    }
}