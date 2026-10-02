package com.pompomhills.intelligence.quality;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Request to validate a single video prompt.
 *
 * @param prompt Video prompt text (required)
 * @param rulesetVersion Ruleset version to use (null = latest)
 */
public record ValidatePromptRequest(
    @NotBlank(message = "Prompt text cannot be blank") @Size(min = 100, max = 10000, message = "Prompt must be between 100-10000 characters") String prompt,
    String rulesetVersion) {}
