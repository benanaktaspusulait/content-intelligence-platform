package com.pompomhills.intelligence.quality;

/**
 * Public request to validate a prompt and persist the result as evidence.
 *
 * <p>{@code contentId}/{@code promptVersionId} are optional, but a validation can only ever become
 * render-authorizing evidence when both are present and resolve to a real, immutable prompt version
 * (see {@link com.pompomhills.intelligence.content.ContentPromptQueryService}). Standalone
 * validations with no linkage remain visible through this API but are permanently non-renderable -
 * {@link ValidationEvidenceService} rejects them as incomplete evidence.
 *
 * <p>{@code prompt} is intentionally unconstrained by Jakarta Bean Validation here: when {@code
 * contentId}/{@code promptVersionId} are both present, this field is never used (the stored
 * immutable prompt text is validated instead), so a declarative length constraint on it would
 * reject legitimate linked requests that pass a short placeholder. {@link
 * IntelligenceQualityValidationService#validateAndPersistEvidence} enforces the 100-10000 character
 * requirement itself, but only for the standalone (unlinked) case where this field is actually
 * used.
 *
 * @param prompt video prompt text (required only when unlinked; ignored when contentId/
 *     promptVersionId are both present)
 * @param rulesetVersion ruleset version to use (null = latest)
 * @param contentId optional external content ID to link this validation to
 * @param promptVersionId optional external prompt version ID to link this validation to
 */
public record IntelligenceValidateRequest(
    String prompt, String rulesetVersion, Long contentId, Long promptVersionId) {}
