package com.pompom.ruleset.engine;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.domain.Rule;
import com.theokanning.openai.completion.chat.ChatCompletionRequest;
import com.theokanning.openai.completion.chat.ChatMessage;
import com.theokanning.openai.service.OpenAiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
@RequiredArgsConstructor
public class LlmEvaluator implements RuleEvaluator {
    
    private final OpenAiService openAiService;
    private final ObjectMapper objectMapper;
    
    @Value("${openai.model:gpt-4-turbo-preview}")
    private String model;
    
    @Value("${openai.temperature:0.3}")
    private double temperature;
    
    @Value("${openai.max-tokens:1000}")
    private int maxTokens;
    
    @Override
    public RuleResult evaluate(Rule rule, ConceptValidationRequest request) {
        log.debug("Evaluating rule {} with LLM evaluator", rule.getRuleCode());
        
        try {
            String prompt = buildPrompt(rule, request);
            String response = callOpenAi(prompt);
            return parseResponse(response);
        } catch (Exception e) {
            log.error("LLM evaluation failed for rule {}", rule.getRuleCode(), e);
            return RuleResult.warn("LLM evaluation failed: " + e.getMessage());
        }
    }
    
    @Override
    public boolean supports(Rule rule) {
        return rule.getEvaluationType() == Rule.EvaluationType.LLM ||
               rule.getEvaluationType() == Rule.EvaluationType.HYBRID;
    }
    
    private String buildPrompt(Rule rule, ConceptValidationRequest request) {
        Map<String, Object> yamlDef = rule.getYamlDefinition();
        String promptTemplate = (String) yamlDef.get("prompt");
        
        if (promptTemplate == null) {
            throw new IllegalArgumentException("Rule " + rule.getRuleCode() + " has no prompt template");
        }
        
        return promptTemplate
            .replace("{{conceptText}}", request.getConceptText())
            .replace("{{intent}}", request.getIntent() != null ? request.getIntent().toString() : "UNKNOWN");
    }
    
    private String callOpenAi(String prompt) {
        ChatCompletionRequest completionRequest = ChatCompletionRequest.builder()
            .model(model)
            .temperature(temperature)
            .maxTokens(maxTokens)
            .messages(List.of(
                new ChatMessage("system", "You are a creative concept evaluator for short-form video content. Respond ONLY with valid JSON."),
                new ChatMessage("user", prompt)
            ))
            .build();
        
        return openAiService.createChatCompletion(completionRequest)
            .getChoices()
            .get(0)
            .getMessage()
            .getContent();
    }
    
    private RuleResult parseResponse(String response) throws Exception {
        String json = response;
        if (response.contains("```json")) {
            json = response.substring(
                response.indexOf("```json") + 7,
                response.lastIndexOf("```")
            ).trim();
        } else if (response.contains("```")) {
            json = response.substring(
                response.indexOf("```") + 3,
                response.lastIndexOf("```")
            ).trim();
        }
        
        JsonNode node = objectMapper.readTree(json);
        
        double score = node.has("score") ? node.get("score").asDouble() : 0.0;
        String reason = node.has("reason") ? node.get("reason").asText() : "No reason provided";
        
        boolean passed = score >= 70.0;
        
        return RuleResult.builder()
            .passed(passed)
            .score(BigDecimal.valueOf(score))
            .reason(reason)
            .details(objectMapper.convertValue(node, Map.class))
            .build();
    }
}
