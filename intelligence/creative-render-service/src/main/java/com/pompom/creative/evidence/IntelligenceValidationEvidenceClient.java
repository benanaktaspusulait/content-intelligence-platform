package com.pompom.creative.evidence;

/** Fetches immutable validation evidence from the intelligence backend. */
public interface IntelligenceValidationEvidenceClient {
  ValidationEvidenceDto getEvidence(long validationRecordId);
}
