package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.nullable;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class MetaAccountDiscoveryServiceTest {
  private static final Instant ISSUED_AT = Instant.parse("2026-10-01T12:00:00Z");
  private static final Instant EXPIRES_AT = Instant.parse("2026-10-01T13:00:00Z");

  private MetaConnectionRepository repository;
  private MetaGraphReadClient graph;
  private MetaAccountDiscoveryService service;
  private MetaConnectionEntity connection;

  @BeforeEach
  void setUp() {
    repository = org.mockito.Mockito.mock(MetaConnectionRepository.class);
    graph = org.mockito.Mockito.mock(MetaGraphReadClient.class);
    connection = connectedEntity();
    when(repository.findByIdAndOwnerKey(connection.getId(), "owner-1"))
        .thenReturn(Optional.of(connection));
    when(repository.save(any(MetaConnectionEntity.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));
    service =
        new MetaAccountDiscoveryService(
            repository,
            graph,
            new MetaTokenEncryptionService("test-encryption-key"),
            properties(),
            Clock.fixed(ISSUED_AT, ZoneOffset.UTC));
  }

  @Test
  void discoversManagedPagesAndPersistsLinkedInstagramIdentityWithoutSecrets() throws Exception {
    when(graph.listManagedPages("user-secret", null, 25))
        .thenReturn(
            new MetaGraphReadClient.PageAccountPage(
                List.of(
                    new MetaGraphReadClient.PageAccount(
                        "page-1", "Pompom Hills", "Education", true, "instagram-1")),
                new MetaGraphReadClient.Paging(
                    new MetaGraphReadClient.Cursors(null, null), null, null)));

    MetaAccountDiscoveryResponse response = service.discover(connection.getId());

    assertThat(response.pages()).hasSize(1);
    MetaAccountDiscoveryResponse.PageTarget page = response.pages().get(0);
    assertThat(page.id()).isEqualTo("page-1");
    assertThat(page.selected()).isTrue();
    assertThat(page.instagramAccount()).isNotNull();
    assertThat(page.instagramAccount().id()).isEqualTo("instagram-1");
    assertThat(page.instagramAccount().mediaEligibility())
        .isEqualTo(MetaCapabilityStatus.UNKNOWN);
    assertThat(page.capabilities().get(MetaCapability.META_FACEBOOK_ANALYTICS_READ))
        .isEqualTo(MetaCapabilityStatus.SUPPORTED);
    assertThat(connection.getFacebookPageId()).isEqualTo("page-1");
    assertThat(connection.getInstagramAccountId()).isEqualTo("instagram-1");
    assertThat(connection.isInstagramAccountEligible()).isFalse();
    assertThat(response.selectedPageId()).isEqualTo("page-1");
    assertThat(response.selectedInstagramAccountId()).isEqualTo("instagram-1");
    verify(graph).listManagedPages("user-secret", null, 25);

    String serialized = new ObjectMapper().findAndRegisterModules().writeValueAsString(response);
    assertThat(serialized)
        .doesNotContain("user-secret", "page-secret", "\"access_token\":", "refreshToken");
  }

  @Test
  void missingLinkedInstagramAccountRemainsASecretFreePartialResult() {
    when(graph.listManagedPages("user-secret", null, 25))
        .thenReturn(
            new MetaGraphReadClient.PageAccountPage(
                List.of(new MetaGraphReadClient.PageAccount("page-1", "Pompom Hills", null, true, null)),
                null));

    MetaAccountDiscoveryResponse response = service.discover(connection.getId());

    assertThat(response.pages().get(0).instagramAccount()).isNull();
    assertThat(response.selectedInstagramAccountId()).isNull();
    assertThat(connection.getInstagramAccountId()).isNull();
    assertThat(response.pages().get(0).capabilities().get(MetaCapability.META_INSTAGRAM_ANALYTICS_READ))
        .isEqualTo(MetaCapabilityStatus.UNKNOWN);
  }

  @Test
  void discoveryStopsAtBoundedPaginationAndDeduplicatesPageIds() {
    when(graph.listManagedPages("user-secret", null, 25))
        .thenReturn(
            new MetaGraphReadClient.PageAccountPage(
                List.of(new MetaGraphReadClient.PageAccount("page-1", "One", null, true, null)),
                new MetaGraphReadClient.Paging(
                    new MetaGraphReadClient.Cursors(null, "cursor-1"), null, null)));
    when(graph.listManagedPages("user-secret", "cursor-1", 25))
        .thenReturn(
            new MetaGraphReadClient.PageAccountPage(
                List.of(
                    new MetaGraphReadClient.PageAccount("page-1", "One", null, true, null),
                    new MetaGraphReadClient.PageAccount("page-2", "Two", null, true, null)),
                new MetaGraphReadClient.Paging(
                    new MetaGraphReadClient.Cursors(null, "cursor-1"), null, null)));

    MetaAccountDiscoveryResponse response = service.discover(connection.getId());

    assertThat(response.pages()).extracting(MetaAccountDiscoveryResponse.PageTarget::id)
        .containsExactly("page-1", "page-2");
  }

  @Test
  void enforcesFourRequestAndOneHundredPageBounds() {
    when(graph.listManagedPages(eq("user-secret"), nullable(String.class), eq(25)))
        .thenAnswer(
            invocation -> {
              String cursor = invocation.getArgument(1);
              int batch = cursor == null ? 0 : Integer.parseInt(cursor.substring("cursor-".length()));
              int first = batch * 25 + 1;
              List<MetaGraphReadClient.PageAccount> pages =
                  java.util.stream.IntStream.range(first, first + 25)
                      .mapToObj(
                          index ->
                              new MetaGraphReadClient.PageAccount(
                                  "page-" + index, "Page " + index, null, true, null))
                      .toList();
              return new MetaGraphReadClient.PageAccountPage(
                  pages,
                  new MetaGraphReadClient.Paging(
                      new MetaGraphReadClient.Cursors(null, "cursor-" + (batch + 1)),
                      null,
                      null));
            });

    MetaAccountDiscoveryResponse response = service.discover(connection.getId());

    assertThat(response.pages()).hasSize(100);
    verify(graph, org.mockito.Mockito.times(4))
        .listManagedPages(eq("user-secret"), nullable(String.class), eq(25));
  }

  @Test
  void pageWithoutAccessTokenIsNotReportedAsEligible() {
    when(graph.listManagedPages("user-secret", null, 25))
        .thenReturn(
            new MetaGraphReadClient.PageAccountPage(
                List.of(new MetaGraphReadClient.PageAccount("page-1", "Pompom Hills", null, false, null)),
                null));

    MetaAccountDiscoveryResponse response = service.discover(connection.getId());

    MetaAccountDiscoveryResponse.PageTarget page = response.pages().get(0);
    assertThat(page.pageEligibility()).isEqualTo(MetaCapabilityStatus.UNKNOWN);
    assertThat(page.capabilities().get(MetaCapability.META_FACEBOOK_ANALYTICS_READ))
        .isEqualTo(MetaCapabilityStatus.UNKNOWN);
  }

  @Test
  void permissionFailureDoesNotExposeProviderTextOrClaimCapability() {
    when(graph.listManagedPages("user-secret", null, 25))
        .thenThrow(
            new MetaGraphException(
                403, 10, null, "OAuthException", "trace-1", "secret provider detail"));

    MetaAccountDiscoveryResponse response = service.discover(connection.getId());

    assertThat(response.pages()).isEmpty();
    assertThat(response.message()).doesNotContain("secret provider detail");
    assertThat(response.capabilities()).doesNotContainValue(MetaCapabilityStatus.SUPPORTED);
    assertThat(connection.getCapabilities()).doesNotContainValue(MetaCapabilityStatus.SUPPORTED);
  }

  private MetaConnectionEntity connectedEntity() {
    MetaConnectionEntity entity =
        MetaConnectionEntity.connected(
            "owner-1",
            new MetaProviderAdapter.AuthorizationResult(
                "meta-user-1",
                "page-1",
                "old-instagram",
                "PROFESSIONAL",
                "user-secret",
                "page-secret",
                "refresh-secret",
                Set.of("pages_show_list", "pages_read_engagement", "instagram_basic", "instagram_manage_insights"),
                ISSUED_AT,
                EXPIRES_AT,
                true,
                true,
                null),
            new MetaTokenEncryptionService("test-encryption-key"),
            Map.of(
                MetaCapability.META_FACEBOOK_ANALYTICS_READ, MetaCapabilityStatus.SUPPORTED,
                MetaCapability.META_INSTAGRAM_ANALYTICS_READ, MetaCapabilityStatus.SUPPORTED));
    entity.setId(UUID.randomUUID());
    return entity;
  }

  private MetaReadProperties properties() {
    return new MetaReadProperties(
        true,
        "v26.0",
        "",
        "",
        "",
        "",
        Duration.ofSeconds(5),
        Duration.ofSeconds(15),
        false,
        false,
        "owner-1");
  }
}
