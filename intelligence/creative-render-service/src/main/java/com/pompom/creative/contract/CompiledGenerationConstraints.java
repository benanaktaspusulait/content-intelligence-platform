package com.pompom.creative.contract;

import java.util.List;

/** Deterministic, provider-facing constraints compiled from a validated contract. */
public record CompiledGenerationConstraints(
    String compilerVersion, String status, List<String> constraints, List<String> conflicts) {}
