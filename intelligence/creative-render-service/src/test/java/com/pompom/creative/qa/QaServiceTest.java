package com.pompom.creative.qa;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.service.AssetLibraryManager;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClient;

@ExtendWith(MockitoExtension.class)
class QaServiceTest {

  @Mock private RestClient.Builder restClientBuilder;

  @Mock private AssetLibraryManager assetLibraryManager;

  @Mock private RestClient restClient;

  @Mock private RestClient.RequestBodyUriSpec requestBodyUriSpec;

  @Mock private RestClient.RequestBodySpec requestBodySpec;

  @Mock private RestClient.ResponseSpec responseSpec;

  private QaService qaService;

  @BeforeEach
  void setUp() {
    // Setup RestClient mock chain
    when(restClientBuilder.baseUrl(anyString())).thenReturn(restClientBuilder);
    when(restClientBuilder.build()).thenReturn(restClient);

    when(restClient.post()).thenReturn(requestBodyUriSpec);
    when(requestBodyUriSpec.uri(anyString())).thenReturn(requestBodySpec);
    // The service calls RequestBodySpec.body(Object). A bare any() binds to a
    // different overload (StreamingHttpOutputMessage.Body), so the stub never
    // matches the real invocation and the call falls into the catch block.
    // any(Object.class) pins the matcher to the Object overload that is used.
    when(requestBodySpec.body(any(Object.class))).thenReturn(requestBodySpec);
    when(requestBodySpec.retrieve()).thenReturn(responseSpec);

    qaService = new QaService(restClientBuilder, assetLibraryManager);

    // @Value fields are not populated when constructing the service directly in a
    // plain Mockito test, so inject them explicitly. Without this, getAssetPath()
    // calls Path.of(null) and throws NullPointerException before any QA logic runs.
    ReflectionTestUtils.setField(qaService, "dataRoot", "/tmp/pompom-data-test");
    ReflectionTestUtils.setField(qaService, "qaServiceUrl", "http://localhost:8001");
  }

  @Test
  void analyzeAsset_allChecksPass_returns100Score() {
    // Given: Asset with no issues
    RenderJob job = RenderJob.builder().contentId(1L).contentTitleSnapshot("Kiko Episode").build();

    RenderAsset asset =
        RenderAsset.builder()
            .id(java.util.UUID.randomUUID())
            .renderJob(job)
            .contentId(1L)
            .assetType(RenderAsset.AssetType.VIDEO)
            .relativePath("content/1/render-v1.mp4")
            .build();

    // Mock Python service responses - all pass
    mockDeadAirResponse(false, 0);
    mockCharacterIdentityResponse(true, 0.95);

    // When
    QaAnalysisResult result = qaService.analyzeAsset(asset);

    // Then
    assertThat(result.getComplianceScore()).isEqualTo(100);
    assertThat(result.isHasDeadAir()).isFalse();
    assertThat(result.isCharacterIdentityVerified()).isTrue();
    assertThat(result.getConfidence()).isEqualTo(0.95);
  }

  @Test
  void analyzeAsset_hasDeadAir_deductsPoints() {
    // Given: Asset with dead air
    RenderJob job = RenderJob.builder().contentId(1L).contentTitleSnapshot("Mimi Episode").build();

    RenderAsset asset =
        RenderAsset.builder()
            .renderJob(job)
            .contentId(1L)
            .assetType(RenderAsset.AssetType.VIDEO)
            .relativePath("content/1/render-v1.mp4")
            .build();

    // Mock Python service responses - dead air present
    mockDeadAirResponse(true, 3000);
    mockCharacterIdentityResponse(true, 0.9);

    // When
    QaAnalysisResult result = qaService.analyzeAsset(asset);

    // Then
    assertThat(result.getComplianceScore()).isEqualTo(70); // 100 - 30 for dead air
    assertThat(result.isHasDeadAir()).isTrue();
    assertThat(result.getDeadAirDurationMs()).isEqualTo(3000);
  }

  @Test
  void analyzeAsset_characterMismatch_deductsPoints() {
    // Given: Asset with character mismatch
    RenderJob job = RenderJob.builder().contentId(1L).contentTitleSnapshot("Opa Episode").build();

    RenderAsset asset =
        RenderAsset.builder()
            .renderJob(job)
            .contentId(1L)
            .assetType(RenderAsset.AssetType.VIDEO)
            .relativePath("content/1/render-v1.mp4")
            .build();

    // Mock Python service responses - character mismatch
    mockDeadAirResponse(false, 0);
    mockCharacterIdentityResponse(false, 0.3);

    // When
    QaAnalysisResult result = qaService.analyzeAsset(asset);

    // Then
    assertThat(result.getComplianceScore()).isEqualTo(50); // 100 - 50 for character mismatch
    assertThat(result.isCharacterIdentityVerified()).isFalse();
  }

  @Test
  void analyzeAsset_multipleIssues_cumulative() {
    // Given: Asset with multiple issues
    RenderJob job = RenderJob.builder().contentId(1L).contentTitleSnapshot("Arda Episode").build();

    RenderAsset asset =
        RenderAsset.builder()
            .renderJob(job)
            .contentId(1L)
            .assetType(RenderAsset.AssetType.VIDEO)
            .relativePath("content/1/render-v1.mp4")
            .build();

    // Mock Python service responses - both issues
    mockDeadAirResponse(true, 2500);
    mockCharacterIdentityResponse(false, 0.4);

    // When
    QaAnalysisResult result = qaService.analyzeAsset(asset);

    // Then
    assertThat(result.getComplianceScore()).isEqualTo(20); // 100 - 30 - 50 = 20
    assertThat(result.isHasDeadAir()).isTrue();
    assertThat(result.isCharacterIdentityVerified()).isFalse();
  }

  // Helper methods to mock Python service responses

  private void mockDeadAirResponse(boolean hasDeadAir, int durationMs) {
    QaService.DeadAirResponse response =
        new QaService.DeadAirResponse(
            hasDeadAir, java.util.List.of(), durationMs, hasDeadAir ? 1 : 0);

    when(responseSpec.body(QaService.DeadAirResponse.class)).thenReturn(response);
  }

  private void mockCharacterIdentityResponse(boolean verified, double confidence) {
    QaService.CharacterIdentityResponse response =
        new QaService.CharacterIdentityResponse(
            verified,
            confidence,
            verified ? null : "Character mismatch detected",
            verified ? "Character verified successfully" : "Character does not match expected");

    when(responseSpec.body(QaService.CharacterIdentityResponse.class)).thenReturn(response);
  }
}
