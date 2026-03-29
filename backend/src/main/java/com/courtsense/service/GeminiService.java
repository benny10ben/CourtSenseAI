package com.courtsense.service;

import com.courtsense.model.Match;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.util.List;
import java.util.Map;

@Service
public class GeminiService {

    @Value("${GEMINI_API_KEY}")
    private String apiKey;

    @Value("${GEMINI_API_URL}")
    private String apiUrl;

    private static final int MAX_RETRIES = 3;
    private static final long BASE_DELAY_MS = 2000; // 2s → 4s → 8s

    private final WebClient webClient = WebClient.builder().build();

    public String getLiveCoaching(Match match) {
        String prompt = buildCoachingPrompt(match);

        for (int attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            try {
                System.out.println("🤖 Gemini attempt " + attempt + "/" + MAX_RETRIES);
                return callGemini(prompt);

            } catch (WebClientResponseException e) {
                // This gives you the REAL error body from Google (e.g. invalid model name, quota exceeded)
                System.err.println("❌ Gemini HTTP " + e.getStatusCode() + " on attempt " + attempt);
                System.err.println("   Response body: " + e.getResponseBodyAsString());

                boolean isRetryable = e.getStatusCode().value() == 503
                                   || e.getStatusCode().value() == 429; // 429 = rate limit

                if (isRetryable && attempt < MAX_RETRIES) {
                    long delay = BASE_DELAY_MS * (long) Math.pow(2, attempt - 1);
                    System.out.println("⏳ Retrying in " + delay + "ms...");
                    try {
                        Thread.sleep(delay);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                } else {
                    // 4xx errors (bad model name, bad API key, etc.) — no point retrying
                    System.err.println("⛔ Non-retryable error. Stopping.");
                    break;
                }

            } catch (Exception e) {
                System.err.println("❌ Unexpected Gemini error on attempt " + attempt + ": " + e.getMessage());
                break;
            }
        }

        return buildFallbackInsight(match);
    }

    @SuppressWarnings("unchecked")
    private String callGemini(String prompt) {
        Map<String, Object> response = webClient.post()
            .uri(apiUrl + "?key=" + apiKey)  // <-- pass key as query param (standard Google pattern)
            .header("Content-Type", "application/json")
            .bodyValue(Map.of(
                "contents", List.of(
                    Map.of("parts", List.of(
                        Map.of("text", prompt)
                    ))
                )
            ))
            .retrieve()
            .bodyToMono(Map.class)
            .block();

        if (response == null) {
            throw new RuntimeException("Gemini returned a null response body.");
        }

        List<Object> candidates = (List<Object>) response.get("candidates");
        if (candidates == null || candidates.isEmpty()) {
            // Google sometimes returns a "promptFeedback" block with a BLOCK_REASON instead
            Object feedback = response.get("promptFeedback");
            throw new RuntimeException("No candidates in Gemini response. Feedback: " + feedback);
        }

        Map<String, Object> candidate = (Map<String, Object>) candidates.get(0);
        Map<String, Object> content   = (Map<String, Object>) candidate.get("content");
        List<Object>        parts     = (List<Object>) content.get("parts");
        Map<String, Object> part      = (Map<String, Object>) parts.get(0);

        return (String) part.get("text");
    }

    private String buildFallbackInsight(Match match) {
        return String.format(
            "⚠️ AI coaching is temporarily unavailable.\n\n" +
            "**Match Summary:** %d shots across %d rallies " +
            "(avg rally: %.1fs). Harder hitter: **%s**.\n\n" +
            "Your full stats have been saved. Refresh later for AI feedback.",
            match.getTotalShots(),
            match.getTotalRallies(),
            match.getAvgRallyLengthSeconds(),
            match.getHarderHitter()
        );
    }

    public String buildCoachingPrompt(Match match) {
        return """
            You are an elite badminton coach analyzing match data. Speak directly to Player 1.

            MATCH DATA (JSON):
            %s

            Analyze Player 2's weaknesses from their stats. Respond in exactly these 3 sections under 150 words total:

            ### 🏸 Match Dynamic
            2 sentences on overall pace and who controls the court.

            ### 🎯 Exploit The Opponent
            Specific zones, speeds, or coverage limits where Player 2 is vulnerable.

            ### ⚔️ Kill Strategy
            1 specific actionable tactic using exact shots to exploit that weakness.

            Be direct, aggressive, and specific to the numbers.
            """.formatted(match.getRawJsonPayload());
    }
}