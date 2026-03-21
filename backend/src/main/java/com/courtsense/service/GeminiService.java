package com.courtsense.service;

import com.courtsense.model.Match;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import java.util.Map;
import java.util.List;

@Service
public class GeminiService {

    @Value("${GEMINI_API_KEY}")
    private String apiKey;

    @Value("${GEMINI_API_URL}")
    private String apiUrl;

    private final WebClient webClient = WebClient.builder().build();

    public String getLiveCoaching(Match match) {
        String prompt = buildCoachingPrompt(match);

        try {
            // Making the call with the Key in the HEADER (x-goog-api-key)
            Map<String, Object> response = webClient.post()
                .uri(apiUrl)
                .header("x-goog-api-key", apiKey) 
                .bodyValue(Map.of("contents", List.of(Map.of("parts", List.of(Map.of("text", prompt))))))
                .retrieve()
                .bodyToMono(Map.class)
                .block();

            // Extracting the AI's response text
            List candidates = (List) response.get("candidates");
            Map candidate = (Map) candidates.get(0);
            Map content = (Map) candidate.get("content");
            List parts = (List) content.get("parts");
            Map part = (Map) parts.get(0);
            
            return (String) part.get("text");

        } catch (Exception e) {
            System.err.println("Gemini Error: " + e.getMessage());
            return "Coach is currently reviewing the tapes... (Check your API key and URL)";
        }
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