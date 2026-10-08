package com.pompom.metapublisher.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.metapublisher.MetaPublisherProperties;
import com.pompom.metapublisher.facebook.FacebookReelsClient;
import com.pompom.metapublisher.instagram.InstagramReelsClient;
import com.pompom.metapublisher.security.MetaWriteCapabilityGuard;
import com.pompom.metapublisher.service.MetaPublishService;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishercontract.PublisherCapability;
import com.pompom.publishersupport.ProviderOperationRecord;
import com.pompom.publishersupport.ProviderOperationRepository;
import com.pompom.publishersupport.PublisherRequestValidator;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class MetaPublisherControllerTest {

  private static final String INTERNAL_TOKEN = "internal-test-secret";
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  @Test
  void rejectsPublishWhenInternalAuthenticationIsMissing() throws Exception {
    MetaPublishService service = mock(MetaPublishService.class);
    MockMvc mvc = mvc(service, new MetaWriteCapabilityGuard(true, INTERNAL_TOKEN));

    mvc.perform(
            post("/internal/v1/publish")
                .header(MetaWriteCapabilityGuard.CAPABILITY_HEADER, "facebook_reels")
                .header(MetaWriteCapabilityGuard.CALLER_ENABLED_HEADER, "true")
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command())))
        .andExpect(status().isUnauthorized())
        .andExpect(
            content()
                .string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("secret"))));
  }

  @Test
  void rejectsPublishWhenServiceWriteCapabilityIsDisabled() throws Exception {
    MetaPublishService service = mock(MetaPublishService.class);
    MockMvc mvc = mvc(service, new MetaWriteCapabilityGuard(false, INTERNAL_TOKEN));

    mvc.perform(
            post("/internal/v1/publish")
                .header(MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .header(MetaWriteCapabilityGuard.CAPABILITY_HEADER, "facebook_reels")
                .header(MetaWriteCapabilityGuard.CALLER_ENABLED_HEADER, "true")
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command())))
        .andExpect(status().isForbidden());
  }

  @Test
  void acceptsAuthenticatedCommandAndReturnsNormalizedResult() throws Exception {
    MetaPublishService service = mock(MetaPublishService.class);
    PublishResult result =
        new PublishResult(
            PublishStatus.COMPLETED,
            "post-1",
            "video-1",
            "https://facebook.example/post-1",
            "trace-1",
            null,
            null,
            false);
    when(service.publish(any(PublishCommand.class), eq("facebook_reels"))).thenReturn(result);
    MockMvc mvc = mvc(service, new MetaWriteCapabilityGuard(true, INTERNAL_TOKEN));

    mvc.perform(
            post("/internal/v1/publish")
                .header(MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .header(MetaWriteCapabilityGuard.CAPABILITY_HEADER, "facebook_reels")
                .header(MetaWriteCapabilityGuard.CALLER_ENABLED_HEADER, "true")
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command())))
        .andExpect(status().isOk())
        .andExpect(content().json(OBJECT_MAPPER.writeValueAsString(result)));

    verify(service).publish(any(PublishCommand.class), eq("facebook_reels"));
  }

  @Test
  void reconciliationRequiresInternalAuthenticationButNotWriteEnablement() throws Exception {
    MetaPublishService service = mock(MetaPublishService.class);
    MetaPublishService.ReconcileCommand reconcileCommand =
        new MetaPublishService.ReconcileCommand(
            UUID.fromString("11111111-1111-1111-1111-111111111111"),
            "facebook_reels",
            "page-1",
            "post-1",
            "video-1",
            "trace-1");
    PublishResult result =
        new PublishResult(
            PublishStatus.RECONCILIATION_REQUIRED,
            null,
            "video-1",
            null,
            "trace-1",
            "reconciliation_required",
            "not found",
            true);
    when(service.reconcile(any(MetaPublishService.ReconcileCommand.class))).thenReturn(result);
    MockMvc mvc = mvc(service, new MetaWriteCapabilityGuard(false, INTERNAL_TOKEN));

    mvc.perform(
            post("/internal/v1/reconcile")
                .header(MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(reconcileCommand)))
        .andExpect(status().isOk())
        .andExpect(content().json(OBJECT_MAPPER.writeValueAsString(result)));

    verify(service).reconcile(any(MetaPublishService.ReconcileCommand.class));
  }

  @Test
  void sharedCommandRejectsCredentialLikeProviderOptions() {
    assertThatThrownBy(
            () ->
                new PublishCommand(
                    UUID.randomUUID(),
                    UUID.randomUUID(),
                    "key-1",
                    "page-1",
                    "asset.mp4",
                    "a".repeat(64),
                    null,
                    null,
                    List.of(),
                    false,
                    Map.of("access_token", "secret")))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("credential-like");
  }

  @Test
  void completedDuplicateReturnsStoredResultWithoutProviderCall() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    ProviderOperationRepository.OperationClaim claim =
        mock(ProviderOperationRepository.OperationClaim.class);
    PublishResult existing = completedResult();
    when(claim.newOperation()).thenReturn(false);
    when(claim.existingResult()).thenReturn(Optional.of(existing));
    when(repository.claim(any(PublishCommand.class), any(PublisherCapability.class)))
        .thenReturn(claim);

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "page-token", "page-1", "ig-token")));

    assertThat(service.publish(command(), "facebook_reels")).isEqualTo(existing);
    verifyNoInteractions(facebook, instagram);
  }

  @Test
  void inFlightDuplicateIsAcceptedWithoutASecondProviderCall() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    ProviderOperationRepository.OperationClaim claim =
        mock(ProviderOperationRepository.OperationClaim.class);
    when(claim.newOperation()).thenReturn(false);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(repository.claim(any(PublishCommand.class), any(PublisherCapability.class)))
        .thenReturn(claim);

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "page-token", "page-1", "ig-token")));

    PublishResult result = service.publish(command(), "facebook_reels");

    assertThat(result.status()).isEqualTo(PublishStatus.ACCEPTED);
    assertThat(result.reconciliationRequired()).isFalse();
    verifyNoInteractions(facebook, instagram);
  }

  @Test
  void routesInstagramCapabilityToInstagramClientAndRecordsItsResult() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    ProviderOperationRepository.OperationClaim claim =
        mock(ProviderOperationRepository.OperationClaim.class);
    PublishResult result = completedResult();
    when(claim.newOperation()).thenReturn(true);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(repository.claim(any(PublishCommand.class), any(PublisherCapability.class)))
        .thenReturn(claim);
    when(instagram.publish(any(PublishCommand.class))).thenReturn(result);

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "page-token", "page-1", "ig-token")));
    PublishCommand publishCommand = command();

    assertThat(service.publish(publishCommand, "instagram_reels")).isEqualTo(result);
    verify(instagram).publish(any(PublishCommand.class));
    verify(facebook, never()).publish(any(PublishCommand.class));
    verify(repository)
        .recordResult(
            eq(PublisherCapability.INSTAGRAM_REELS),
            argThat(key -> key.startsWith("instagram_reels:")),
            eq(result));
  }

  @Test
  void reconciliationUsesProviderReadOnlyClientOperation() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    PublishResult result = completedResult();
    when(facebook.reconcile("page-1", "post-1", "video-1")).thenReturn(result);

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "page-token", "page-1", "ig-token")));
    MetaPublishService.ReconcileCommand command =
        new MetaPublishService.ReconcileCommand(
            UUID.randomUUID(), "facebook_reels", "page-1", "post-1", "video-1", "trace-1");

    assertThat(service.reconcile(command)).isEqualTo(result);
    verify(facebook).reconcile("page-1", "post-1", "video-1");
    verify(facebook, never()).publish(any(PublishCommand.class));
    verifyNoInteractions(instagram);
    verify(repository)
        .findByPublicationAttemptId(
            eq(PublisherCapability.FACEBOOK_REELS), eq(command.publicationAttemptId()));
  }

  @Test
  void capabilityIsBoundToProviderOperationIdentity() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    ProviderOperationRepository.OperationClaim claim =
        mock(ProviderOperationRepository.OperationClaim.class);
    List<String> claimedKeys = new ArrayList<>();
    when(claim.newOperation()).thenReturn(true);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(repository.claim(any(PublishCommand.class), any(PublisherCapability.class)))
        .thenAnswer(
            invocation -> {
              claimedKeys.add(invocation.getArgument(0, PublishCommand.class).idempotencyKey());
              return claim;
            });
    when(facebook.publish(any(PublishCommand.class))).thenReturn(completedResult());
    when(instagram.publish(any(PublishCommand.class))).thenReturn(completedResult());

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "page-token", "page-1", "ig-token")));
    PublishCommand publishCommand = command();

    service.publish(publishCommand, "facebook_reels");
    service.publish(publishCommand, "instagram_reels");

    assertThat(claimedKeys).hasSize(2).doesNotHaveDuplicates();
    verify(facebook).publish(any(PublishCommand.class));
    verify(instagram).publish(any(PublishCommand.class));
  }

  @Test
  void scopedRepositoryIdentityKeepsSameCommandProjectionIndependentAcrossCapabilities() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    ProviderOperationRepository.OperationClaim claim =
        mock(ProviderOperationRepository.OperationClaim.class);
    List<PublisherCapability> capabilities = new ArrayList<>();
    when(claim.newOperation()).thenReturn(true);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(repository.claim(any(PublishCommand.class), any(PublisherCapability.class)))
        .thenAnswer(
            invocation -> {
              capabilities.add(invocation.getArgument(1, PublisherCapability.class));
              return claim;
            });
    when(facebook.publish(any(PublishCommand.class))).thenReturn(completedResult());
    when(instagram.publish(any(PublishCommand.class))).thenReturn(completedResult());

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(true, INTERNAL_TOKEN));
    PublishCommand publishCommand = command();

    service.publish(publishCommand, "facebook_reels");
    service.publish(publishCommand, "instagram_reels");

    assertThat(capabilities)
        .containsExactly(PublisherCapability.FACEBOOK_REELS, PublisherCapability.INSTAGRAM_REELS);
    verify(facebook).publish(any(PublishCommand.class));
    verify(instagram).publish(any(PublishCommand.class));
  }

  @Test
  void reconciliationAdvancesTheExistingCapabilityScopedOperation() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    ProviderOperationRecord uncertain = mock(ProviderOperationRecord.class);
    PublishResult completed = completedResult();
    UUID attemptId = UUID.randomUUID();
    when(uncertain.getCommandIdempotencyKey()).thenReturn("facebook_reels:bound-key");
    when(repository.findByPublicationAttemptId(PublisherCapability.FACEBOOK_REELS, attemptId))
        .thenReturn(Optional.of(uncertain));
    when(facebook.reconcile("page-1", "post-1", "video-1")).thenReturn(completed);

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(true, INTERNAL_TOKEN));

    PublishResult result =
        service.reconcile(
            new MetaPublishService.ReconcileCommand(
                attemptId, "facebook_reels", "page-1", "post-1", "video-1", "trace-1"));

    assertThat(result).isEqualTo(completed);
    verify(repository)
        .recordResult(PublisherCapability.FACEBOOK_REELS, "facebook_reels:bound-key", completed);
    verify(facebook).reconcile("page-1", "post-1", "video-1");
    verify(facebook, never()).publish(any(PublishCommand.class));
    verifyNoInteractions(instagram);
  }

  @Test
  void directServiceAdmissionFailsBeforeClaimWhenProviderCredentialsAreMissing() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "", "ig-1", "ig-token")));

    assertThatThrownBy(() -> service.publish(command(), "facebook_reels"))
        .isInstanceOf(MetaWriteCapabilityGuard.ForbiddenException.class);
    verifyNoInteractions(repository, facebook, instagram);
  }

  @Test
  void serviceAcceptsEmojiCaptionAtTheInstagramProviderCodePointLimit() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    ProviderOperationRepository.OperationClaim claim =
        mock(ProviderOperationRepository.OperationClaim.class);
    PublishCommand base = command();
    PublishCommand emojiCommand =
        new PublishCommand(
            base.publicationJobId(),
            base.publicationAttemptId(),
            base.idempotencyKey(),
            base.platformAccountId(),
            base.assetReference(),
            base.assetSha256(),
            base.title(),
            "😀".repeat(2200),
            base.hashtags(),
            base.isPrivate(),
            base.providerOptions());
    when(claim.newOperation()).thenReturn(true);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(repository.claim(any(PublishCommand.class), any(PublisherCapability.class)))
        .thenReturn(claim);
    when(instagram.publish(any(PublishCommand.class))).thenReturn(completedResult());

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "page-token", "page-1", "ig-token")));

    service.publish(emojiCommand, "instagram_reels");

    verify(instagram)
        .publish(
            argThat(
                published ->
                    published.caption().codePointCount(0, published.caption().length()) <= 2200));
  }

  @Test
  void reconciliationDoesNotCrossMatchProviderPostAndVideoIdentityFields() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    when(facebook.reconcile("page-1", "post-requested", "video-requested"))
        .thenReturn(
            new PublishResult(
                PublishStatus.COMPLETED,
                "video-requested",
                null,
                "https://facebook.example/post-requested",
                "trace-1",
                null,
                null,
                false));

    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "page-token", "page-1", "ig-token")));

    PublishResult result =
        service.reconcile(
            new MetaPublishService.ReconcileCommand(
                UUID.randomUUID(),
                "facebook_reels",
                "page-1",
                "post-requested",
                "video-requested",
                "trace-1"));

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.reconciliationRequired()).isTrue();
  }

  @Test
  void enabledServiceRejectsPublishWhenProviderCredentialsAreMissing() throws Exception {
    MetaPublishService service = mock(MetaPublishService.class);
    MetaPublisherProperties properties = properties("page-1", "", "ig-1", "");
    MockMvc mvc = mvc(service, new MetaWriteCapabilityGuard(properties));

    mvc.perform(
            post("/internal/v1/publish")
                .header(MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .header(MetaWriteCapabilityGuard.CAPABILITY_HEADER, "facebook_reels")
                .header(MetaWriteCapabilityGuard.CALLER_ENABLED_HEADER, "true")
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command())))
        .andExpect(status().isForbidden());
  }

  @Test
  void enabledServiceRejectsPublishForAnUnconfiguredTargetAccount() throws Exception {
    MetaPublishService service = mock(MetaPublishService.class);
    MetaPublisherProperties properties =
        properties("different-page", "page-token", "ig-1", "ig-token");
    MockMvc mvc = mvc(service, new MetaWriteCapabilityGuard(properties));

    mvc.perform(
            post("/internal/v1/publish")
                .header(MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .header(MetaWriteCapabilityGuard.CAPABILITY_HEADER, "facebook_reels")
                .header(MetaWriteCapabilityGuard.CALLER_ENABLED_HEADER, "true")
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command())))
        .andExpect(status().isForbidden());
  }

  @Test
  void malformedReconciliationCommandReturnsBadRequest() throws Exception {
    MetaPublishService service = mock(MetaPublishService.class);
    MockMvc mvc = mvc(service, new MetaWriteCapabilityGuard(false, INTERNAL_TOKEN));
    MetaPublishService.ReconcileCommand malformed =
        new MetaPublishService.ReconcileCommand(
            UUID.randomUUID(), "facebook_reels", "page-1", null, null, null);

    mvc.perform(
            post("/internal/v1/reconcile")
                .header(MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(malformed)))
        .andExpect(status().isBadRequest());
    verifyNoInteractions(service);
  }

  @Test
  void malformedReconciliationIdentifierReturnsBadRequestBeforeDelegation() throws Exception {
    MetaPublishService service = mock(MetaPublishService.class);
    MockMvc mvc = mvc(service, new MetaWriteCapabilityGuard(false, INTERNAL_TOKEN));
    MetaPublishService.ReconcileCommand malformed =
        new MetaPublishService.ReconcileCommand(
            UUID.randomUUID(), "facebook_reels", "page-1", "video/with/slash", null, null);

    mvc.perform(
            post("/internal/v1/reconcile")
                .header(MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(malformed)))
        .andExpect(status().isBadRequest());
    verifyNoInteractions(service);
  }

  @Test
  void directReconciliationAdmissionFailsBeforeProviderReadWhenCredentialsAreMissing() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    FacebookReelsClient facebook = mock(FacebookReelsClient.class);
    InstagramReelsClient instagram = mock(InstagramReelsClient.class);
    MetaPublishService service =
        new MetaPublishService(
            repository,
            new PublisherRequestValidator(),
            facebook,
            instagram,
            new MetaWriteCapabilityGuard(properties("page-1", "", "ig-1", "ig-token")));

    assertThatThrownBy(
            () ->
                service.reconcile(
                    new MetaPublishService.ReconcileCommand(
                        UUID.randomUUID(),
                        "facebook_reels",
                        "page-1",
                        "post-1",
                        "video-1",
                        "trace-1")))
        .isInstanceOf(MetaWriteCapabilityGuard.ForbiddenException.class);
    verifyNoInteractions(repository, facebook, instagram);
  }

  private MetaPublisherProperties properties(
      String pageId, String pageToken, String instagramId, String instagramToken) {
    return new MetaPublisherProperties(
        true,
        true,
        INTERNAL_TOKEN,
        "v26.0",
        "https://graph.example",
        "https://rupload.example/video-upload",
        pageId,
        pageToken,
        instagramId,
        instagramToken,
        Duration.ofSeconds(1),
        Duration.ofSeconds(1),
        Duration.ofSeconds(1),
        Duration.ZERO,
        1,
        true,
        "",
        "none",
        "",
        "",
        "",
        true);
  }

  private PublishResult completedResult() {
    return new PublishResult(
        PublishStatus.COMPLETED,
        "post-1",
        "video-1",
        "https://facebook.example/post-1",
        "trace-1",
        null,
        null,
        false);
  }

  private MockMvc mvc(MetaPublishService service, MetaWriteCapabilityGuard guard) {
    return MockMvcBuilders.standaloneSetup(new MetaPublisherController(service, guard)).build();
  }

  private PublishCommand command() {
    return new PublishCommand(
        UUID.fromString("11111111-1111-1111-1111-111111111111"),
        UUID.fromString("22222222-2222-2222-2222-222222222222"),
        "command-1",
        "page-1",
        "https://media.example/video.mp4",
        "a".repeat(64),
        "Title",
        "Caption",
        List.of("reels"),
        false,
        Map.of());
  }
}
