package com.pompom.creative.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.ai.dto.CaptionRequest;
import com.pompom.creative.ai.dto.CaptionResponse;
import com.pompom.creative.oauth.PlatformType;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

/**
 * AI-powered caption generator using OpenAI API. Generates platform-optimized captions with
 * hashtags.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class CaptionGeneratorService {

  private static final String OPENAI_API_URL = "https://api.openai.com/v1/chat/completions";

  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Value("${pompom.ai.openai.api-key:}")
  private String openaiApiKey;

  @Value("${pompom.ai.openai.model:gpt-4}")
  private String openaiModel;

  @Value("${pompom.ai.enabled:false}")
  private Boolean aiEnabled;

  /** Generate caption for video. */
  public CaptionResponse generateCaption(CaptionRequest request) {
    log.info(
        "Generating caption: platform={}, language={}",
        request.getPlatform(),
        request.getLanguage());

    if (!aiEnabled || openaiApiKey == null || openaiApiKey.isEmpty()) {
      log.warn("AI caption generation disabled, using fallback");
      return generateFallbackCaption(request);
    }

    try {
      String prompt = buildPrompt(request);
      String aiResponse = callOpenAI(prompt);

      return parseAIResponse(aiResponse, request);

    } catch (Exception e) {
      log.error("AI caption generation failed, using fallback", e);
      return generateFallbackCaption(request);
    }
  }

  /** Build prompt for OpenAI based on platform and requirements. */
  private String buildPrompt(CaptionRequest request) {
    String platformGuidelines = getPlatformGuidelines(request.getPlatform());
    String languageInstruction =
        request.getLanguage().equals("tr") ? "Generate in Turkish." : "Generate in English.";

    return String.format(
        """
            You are a social media caption expert for kids' educational content (Pompom Hills).

            Video Title: %s
            Video Description: %s
            Target Audience: %s
            Content Type: %s
            Platform: %s
            Language: %s
            Max Length: %d characters

            Platform Guidelines:
            %s

            Generate:
            1. An engaging caption (within character limit)
            2. %d relevant hashtags

            %s

            Format your response as JSON:
            {
              "caption": "...",
              "hashtags": ["hashtag1", "hashtag2", ...]
            }

            Important:
            - Keep it child-friendly and educational
            - Use simple language
            - Include a call-to-action if appropriate
            - Hashtags should be popular and relevant
            """,
        request.getVideoTitle(),
        request.getVideoDescription(),
        request.getTargetAudience(),
        request.getContentType(),
        request.getPlatform(),
        request.getLanguage(),
        request.getMaxLength() != null ? request.getMaxLength() : 500,
        platformGuidelines,
        request.getHashtagCount() != null ? request.getHashtagCount() : 5,
        languageInstruction);
  }

  /** Get platform-specific guidelines. */
  private String getPlatformGuidelines(PlatformType platform) {
    return switch (platform) {
      case TIKTOK ->
          """
                - Start with a hook to grab attention in first 2 seconds
                - Use trending sounds/challenges when relevant
                - Include question or challenge to boost engagement
                - Keep it short and punchy
                - Emojis are encouraged
                """;
      case YOUTUBE ->
          """
                - First line should be compelling (visible without "Show more")
                - Include #Shorts hashtag
                - Add timestamps if relevant
                - Include call-to-action (like, subscribe, comment)
                - Can be longer and more descriptive
                """;
      case FACEBOOK ->
          """
                - Friendly and conversational tone
                - Include question to encourage comments
                - Add context about the video
                - Can use emojis moderately
                """;
      case INSTAGRAM ->
          """
                - First line is critical (above "more" button)
                - Use line breaks for readability
                - Emojis enhance visual appeal
                - Include call-to-action
                - Story-driven approach works well
                """;
    };
  }

  /** Call OpenAI API. */
  private String callOpenAI(String prompt) throws Exception {
    log.debug("Calling OpenAI API");

    RestClient restClient = restClientBuilder.build();

    Map<String, Object> requestBody =
        Map.of(
            "model",
            openaiModel,
            "messages",
            List.of(Map.of("role", "user", "content", prompt)),
            "temperature",
            0.7,
            "max_tokens",
            500);

    String response =
        restClient
            .post()
            .uri(OPENAI_API_URL)
            .header(HttpHeaders.AUTHORIZATION, "Bearer " + openaiApiKey)
            .contentType(MediaType.APPLICATION_JSON)
            .body(requestBody)
            .retrieve()
            .body(String.class);

    JsonNode json = objectMapper.readTree(response);
    String content = json.get("choices").get(0).get("message").get("content").asText();

    log.debug("OpenAI response received");
    return content;
  }

  /** Parse AI response. */
  private CaptionResponse parseAIResponse(String aiResponse, CaptionRequest request)
      throws Exception {
    // Extract JSON from response (AI might add markdown formatting)
    String jsonStr = aiResponse;
    if (aiResponse.contains("```json")) {
      jsonStr =
          aiResponse
              .substring(aiResponse.indexOf("```json") + 7, aiResponse.lastIndexOf("```"))
              .trim();
    } else if (aiResponse.contains("```")) {
      jsonStr =
          aiResponse.substring(aiResponse.indexOf("```") + 3, aiResponse.lastIndexOf("```")).trim();
    }

    JsonNode json = objectMapper.readTree(jsonStr);

    String caption = json.get("caption").asText();
    List<String> hashtags = new ArrayList<>();

    if (json.has("hashtags")) {
      json.get("hashtags").forEach(node -> hashtags.add(node.asText()));
    }

    int charCount = caption.length();
    Integer maxLength = request.getMaxLength() != null ? request.getMaxLength() : 500;

    return CaptionResponse.builder()
        .caption(caption)
        .hashtags(hashtags)
        .platform(request.getPlatform().name())
        .language(request.getLanguage())
        .characterCount(charCount)
        .withinLimit(charCount <= maxLength)
        .build();
  }

  /** Generate fallback caption (when AI is disabled or fails). */
  private CaptionResponse generateFallbackCaption(CaptionRequest request) {
    log.debug("Generating fallback caption");

    String caption = request.getVideoTitle();
    if (request.getVideoDescription() != null && !request.getVideoDescription().isEmpty()) {
      caption += "\n\n" + request.getVideoDescription();
    }

    List<String> hashtags = generateDefaultHashtags(request.getPlatform());

    return CaptionResponse.builder()
        .caption(caption)
        .hashtags(hashtags)
        .platform(request.getPlatform().name())
        .language(request.getLanguage() != null ? request.getLanguage() : "en")
        .characterCount(caption.length())
        .withinLimit(true)
        .build();
  }

  /** Generate default hashtags for platform. */
  private List<String> generateDefaultHashtags(PlatformType platform) {
    List<String> common = List.of("pompomhills", "kids", "educational", "children", "learning");

    return switch (platform) {
      case TIKTOK -> List.of("pompomhills", "kidstiktok", "educational", "funlearning", "toddlers");
      case YOUTUBE -> List.of("pompomhills", "shorts", "kidsvideo", "educational", "preschool");
      case FACEBOOK -> List.of("pompomhills", "kidsvideos", "educational", "parenting", "children");
      case INSTAGRAM ->
          List.of("pompomhills", "reels", "kidsofinstagram", "educational", "momlife");
    };
  }

  /** Check if AI is configured. */
  public boolean isConfigured() {
    return aiEnabled && openaiApiKey != null && !openaiApiKey.isEmpty();
  }
}
