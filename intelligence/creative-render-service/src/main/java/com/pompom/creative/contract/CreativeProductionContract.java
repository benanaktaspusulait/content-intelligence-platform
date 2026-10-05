package com.pompom.creative.contract;

import java.util.List;
import java.util.Map;

/** Immutable normalized production intent captured for one render attempt. */
public record CreativeProductionContract(
    String status,
    String contractVersion,
    String contentFamily,
    String videoPlanVersion,
    String promptVersion,
    String activePreRenderRulesetVersion,
    Map<String, Object> intent,
    List<String> sourceValidationEvidence,
    List<String> errors) {}
