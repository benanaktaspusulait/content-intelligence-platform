package com.pompomhills.intelligence.workflow;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
class OptimizationFailureContractTest {
  @Test void legacyRealFailureIsNotMisclassifiedAsProviderOrConfigurationFailure() {
    var saved=Map.<String,Object>of("recordId","057b9209-036d-4096-a645-7bd49ffc0d94","attemptState","PROVIDER_RESULT_REJECTED","attemptDiagnostics",Map.of("error","Workflow service returned HTTP 409: Prompt optimization candidates must be distinct unsaved revisions","providerDispatched",true));
    var summary=WorkflowService.optimizationFailure(saved);
    assertThat(summary).containsEntry("category","CANDIDATE_STRUCTURE_INVALID").containsEntry("providerResponseReturned",true).containsEntry("retrySafe",false).containsEntry("attemptId","057b9209-036d-4096-a645-7bd49ffc0d94");
    assertThat(summary).doesNotContainKeys("tokenUsage","actualCostUsd");
  }
  @Test void summaryPreservesDiagnosticsButExcludesRecoveryPayloadAndRequiresOperatorAction() {
    var diagnostic=new LinkedHashMap<String,Object>();diagnostic.put("category","PROVIDER_USAGE_MISSING");diagnostic.put("providerDispatched",true);diagnostic.put("providerResponseReturned",true);diagnostic.put("providerResultForRecovery",Map.of("sensitive","private-provider-output"));diagnostic.put("actualCostUsd",null);
    var summary=WorkflowService.optimizationFailure(Map.of("recordId","fixture-id","attemptDiagnostics",diagnostic));
    assertThat(summary.toString()).doesNotContain("private-provider-output");assertThat(summary).containsEntry("retryRequiresOperatorAuthorization",true).doesNotContainKeys("providerResultForRecovery","actualCostUsd");
    var exception=new com.pompomhills.intelligence.quality.MlWorkflowException(409,diagnostic);assertThat(exception.diagnostics()).containsKey("actualCostUsd");
  }
}
