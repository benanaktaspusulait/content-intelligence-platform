package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentWorkspaceController;
import com.pompomhills.intelligence.video.VideoService;
import java.util.*;
import org.junit.jupiter.api.Test;

class IdeaDraftServiceTest {
  @Test
  void clientCannotSupplyApprovalsOrPaidConsentAsSavedState() {
    var state =
        IdeaDraftService.normalizedState(
            Map.of(
                "inputMode",
                "IDEA",
                "idea",
                "Notes follow Mimi",
                "workspacePath",
                "library/work",
                "approvalRecordId",
                "fake",
                "storyConsent",
                true,
                "renderAuthorized",
                true));
    assertThat(state)
        .containsEntry("idea", "Notes follow Mimi")
        .doesNotContainKeys("approvalRecordId", "storyConsent", "renderAuthorized");
  }

  @Test
  void missingWorkspaceIsActionableAndHasNoSideEffects() {
    var videos = mock(VideoService.class);
    var contents = mock(ContentWorkspaceController.class);
    var service = new IdeaDraftService(null, new ObjectMapper(), videos, contents);
    assertThatThrownBy(
            () ->
                service.save(
                    Map.of(
                        "draftId",
                        UUID.randomUUID().toString(),
                        "expectedRevision",
                        0,
                        "state",
                        Map.of("inputMode", "IDEA", "idea", "A short idea"))))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Select a workspace");
    verifyNoInteractions(videos, contents);
  }

  @Test
  void sourceBelongsToTheSelectedMode() {
    assertThat(
            IdeaDraftService.sourceText(
                Map.of(
                    "inputMode",
                    "DETAILED_STORY",
                    "idea",
                    "stale idea",
                    "storyText",
                    "Actual human story")))
        .isEqualTo("Actual human story");
    assertThat(
            IdeaDraftService.sourceText(
                Map.of(
                    "inputMode",
                    "EXISTING_PROMPT",
                    "idea",
                    "stale idea",
                    "promptText",
                    "Exact prompt")))
        .isEqualTo("Exact prompt");
  }

  @Test
  void unsupportedModesAndInvalidConfigurationCannotBePersisted() {
    assertThatThrownBy(() -> IdeaDraftService.normalizedState(Map.of("inputMode", "APPROVED")))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(
            () -> IdeaDraftService.normalizedState(Map.of("inputMode", "IDEA", "duration", -1)))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(
            () ->
                IdeaDraftService.normalizedState(Map.of("inputMode", "IDEA", "profile", "MADE_UP")))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void storyGenerationRequiresFreshAuthorizationAndBudgetBeforeAnyProviderCall() {
    var ml = mock(com.pompomhills.intelligence.quality.QualityMlClient.class);
    var videos = mock(VideoService.class);
    var workflow = new WorkflowService(null, ml, null, videos, new ObjectMapper(), null, null);
    assertThatThrownBy(
            () -> workflow.creativeRole(Map.of("role", "STORY", "text", "Idea", "maxCostUsd", 0.1)))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("authorization");
    assertThatThrownBy(
            () ->
                workflow.creativeRole(
                    Map.of(
                        "role",
                        "STORY",
                        "text",
                        "Idea",
                        "generationAuthorized",
                        true,
                        "maxCostUsd",
                        0)))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("ceiling");
    verifyNoInteractions(ml, videos);
  }
}
