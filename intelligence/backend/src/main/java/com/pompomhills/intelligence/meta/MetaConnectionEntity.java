package com.pompomhills.intelligence.meta;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

@Entity
@Table(
    name = "meta_connections",
    uniqueConstraints = {
      @UniqueConstraint(
          name = "uq_meta_connection_owner_provider_identity",
          columnNames = {
            "owner_key",
            "provider",
            "provider_user_id",
            "facebook_page_id",
            "instagram_account_id"
          }),
      @UniqueConstraint(
          name = "uq_meta_connection_owner_provider_page",
          columnNames = {"owner_key", "provider", "facebook_page_id"})
    })
public class MetaConnectionEntity {
  private static final String PROVIDER = "META";

  @Id @GeneratedValue(strategy = GenerationType.UUID) private UUID id;

  @Column(name = "owner_key", nullable = false, length = 200)
  private String ownerKey;

  @Column(nullable = false, length = 30)
  private String provider = PROVIDER;

  @Column(name = "provider_user_id", length = 200)
  private String providerUserId;

  @Column(name = "facebook_page_id", nullable = false, length = 100)
  private String facebookPageId;

  @Column(name = "instagram_account_id", length = 100)
  private String instagramAccountId;

  @Column(name = "instagram_account_type", length = 80)
  private String instagramAccountType;

  @JsonIgnore
  @Column(name = "user_access_token_encrypted", columnDefinition = "TEXT")
  private String encryptedUserAccessToken;

  @JsonIgnore
  @Column(name = "page_access_token_encrypted", columnDefinition = "TEXT")
  private String encryptedPageAccessToken;

  @JsonIgnore
  @Column(name = "refresh_token_encrypted", columnDefinition = "TEXT")
  private String encryptedRefreshToken;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "granted_scopes", nullable = false, columnDefinition = "jsonb")
  private List<String> grantedScopes = new ArrayList<>();

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 30)
  private MetaConnectionStatus status = MetaConnectionStatus.DEGRADED;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(nullable = false, columnDefinition = "jsonb")
  private Map<MetaCapability, MetaCapabilityStatus> capabilities =
      new EnumMap<>(MetaCapability.class);

  @Column(name = "facebook_page_eligible", nullable = false)
  private boolean facebookPageEligible;

  @Column(name = "instagram_account_eligible", nullable = false)
  private boolean instagramAccountEligible;

  @Column(name = "issued_at", nullable = false)
  private Instant issuedAt;

  @Column(name = "expires_at")
  private Instant expiresAt;

  @Column(name = "last_validated_at")
  private Instant lastValidatedAt;

  @Column(name = "failure_reason", columnDefinition = "TEXT")
  private String failureReason;

  @Column(name = "provider_error_code", length = 100)
  private String providerErrorCode;

  @Version
  @Column(name = "entity_version", nullable = false)
  private long entityVersion;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  @UpdateTimestamp
  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  protected MetaConnectionEntity() {}

  public static MetaConnectionEntity connected(
      String ownerKey,
      MetaProviderAdapter.AuthorizationResult authorization,
      MetaTokenEncryptionService encryption,
      Map<MetaCapability, MetaCapabilityStatus> capabilities) {
    MetaConnectionEntity entity = new MetaConnectionEntity();
    entity.ownerKey = requireOwnerKey(ownerKey);
    entity.applyAuthorization(authorization, encryption, capabilities);
    return entity;
  }

  public void applyAuthorization(
      MetaProviderAdapter.AuthorizationResult authorization,
      MetaTokenEncryptionService encryption,
      Map<MetaCapability, MetaCapabilityStatus> capabilityStatuses) {
    if (authorization == null) {
      throw new IllegalArgumentException("Meta authorization result is required.");
    }
    this.provider = PROVIDER;
    this.providerUserId = normalize(authorization.providerUserId());
    this.facebookPageId = normalize(authorization.facebookPageId());
    this.instagramAccountId = normalize(authorization.instagramAccountId());
    this.instagramAccountType = normalize(authorization.instagramAccountType());
    this.encryptedUserAccessToken = encryption.encrypt(authorization.userAccessToken());
    this.encryptedPageAccessToken = encryption.encrypt(authorization.pageAccessToken());
    this.encryptedRefreshToken = encryption.encrypt(authorization.refreshToken());
    this.grantedScopes = new ArrayList<>(authorization.grantedScopes());
    this.facebookPageEligible = authorization.facebookPageEligible();
    this.instagramAccountEligible = authorization.instagramAccountEligible();
    this.issuedAt = authorization.issuedAt();
    this.expiresAt = authorization.expiresAt();
    this.lastValidatedAt = authorization.issuedAt();
    this.failureReason =
        MetaErrorSanitizer.sanitizeOrNull(
            authorization.providerValidationReason(),
            authorization.userAccessToken(),
            authorization.pageAccessToken(),
            authorization.refreshToken());
    this.providerErrorCode = null;
    this.status = MetaConnectionStatus.CONNECTED;
    this.capabilities = copyCapabilities(capabilityStatuses);
  }

  void applyDiscoveryTarget(
      String facebookPageId,
      String instagramAccountId,
      String instagramAccountType,
      boolean facebookPageEligible,
      boolean instagramAccountEligible,
      Map<MetaCapability, MetaCapabilityStatus> capabilityStatuses,
      Instant validatedAt,
      String failureReason) {
    String normalizedPageId = normalize(facebookPageId);
    if (normalizedPageId == null) {
      throw new IllegalArgumentException("A discovered Meta Facebook Page id is required.");
    }
    this.facebookPageId = normalizedPageId;
    this.instagramAccountId = normalize(instagramAccountId);
    this.instagramAccountType = normalize(instagramAccountType);
    this.facebookPageEligible = facebookPageEligible;
    this.instagramAccountEligible = instagramAccountEligible;
    this.lastValidatedAt = validatedAt;
    this.failureReason = MetaErrorSanitizer.sanitizeOrNull(failureReason);
    this.providerErrorCode = null;
    this.capabilities = copyCapabilities(capabilityStatuses);
  }

  public UUID getId() {
    return id;
  }

  void setId(UUID id) {
    this.id = id;
  }

  public String getOwnerKey() {
    return ownerKey;
  }

  public String getOwnerIdentity() {
    return ownerKey;
  }

  public String getProvider() {
    return provider;
  }

  public String getProviderUserId() {
    return providerUserId;
  }

  public String getFacebookPageId() {
    return facebookPageId;
  }

  public String getInstagramAccountId() {
    return instagramAccountId;
  }

  public String getInstagramAccountType() {
    return instagramAccountType;
  }

  @JsonIgnore
  public String getEncryptedUserAccessToken() {
    return encryptedUserAccessToken;
  }

  @JsonIgnore
  public String getEncryptedPageAccessToken() {
    return encryptedPageAccessToken;
  }

  @JsonIgnore
  public String getEncryptedRefreshToken() {
    return encryptedRefreshToken;
  }

  public List<String> getGrantedScopes() {
    return List.copyOf(grantedScopes);
  }

  public MetaConnectionStatus getStatus() {
    return status;
  }

  public Map<MetaCapability, MetaCapabilityStatus> getCapabilities() {
    return Map.copyOf(capabilities);
  }

  public boolean isFacebookPageEligible() {
    return facebookPageEligible;
  }

  public boolean isInstagramAccountEligible() {
    return instagramAccountEligible;
  }

  public Instant getIssuedAt() {
    return issuedAt;
  }

  public Instant getExpiresAt() {
    return expiresAt;
  }

  public Instant getLastValidatedAt() {
    return lastValidatedAt;
  }

  public String getFailureReason() {
    return failureReason;
  }

  public String getProviderErrorCode() {
    return providerErrorCode;
  }

  public long getEntityVersion() {
    return entityVersion;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }

  public Instant getUpdatedAt() {
    return updatedAt;
  }

  void setExpiresAt(Instant expiresAt) {
    this.expiresAt = expiresAt;
  }

  void setStatus(MetaConnectionStatus status) {
    this.status = status;
  }

  void setFailureReason(String failureReason) {
    this.failureReason = MetaErrorSanitizer.sanitizeOrNull(failureReason);
  }

  void setLastValidatedAt(Instant lastValidatedAt) {
    this.lastValidatedAt = lastValidatedAt;
  }

  void setCapabilities(Map<MetaCapability, MetaCapabilityStatus> capabilities) {
    this.capabilities = copyCapabilities(capabilities);
  }

  void applyRefresh(
      MetaProviderAdapter.TokenRefreshResult refreshed, MetaTokenEncryptionService encryption) {
    if (refreshed == null) {
      throw new IllegalArgumentException("Meta refresh result is required.");
    }
    this.encryptedUserAccessToken = encryption.encrypt(refreshed.userAccessToken());
    this.encryptedPageAccessToken = encryption.encrypt(refreshed.pageAccessToken());
    this.encryptedRefreshToken = encryption.encrypt(refreshed.refreshToken());
    this.issuedAt = refreshed.issuedAt();
    this.expiresAt = refreshed.expiresAt();
    this.lastValidatedAt = refreshed.issuedAt();
  }

  void setEncryptedTokens(
      String encryptedUserAccessToken,
      String encryptedPageAccessToken,
      String encryptedRefreshToken) {
    this.encryptedUserAccessToken = encryptedUserAccessToken;
    this.encryptedPageAccessToken = encryptedPageAccessToken;
    this.encryptedRefreshToken = encryptedRefreshToken;
  }

  MetaProviderAdapter.StoredTokens decryptTokens(MetaTokenEncryptionService encryption) {
    return new MetaProviderAdapter.StoredTokens(
        encryption.decrypt(encryptedUserAccessToken),
        encryption.decrypt(encryptedPageAccessToken),
        encryption.decrypt(encryptedRefreshToken));
  }

  private static String requireOwnerKey(String ownerKey) {
    String normalized = ownerKey == null ? "" : ownerKey.trim();
    if (normalized.isBlank()) {
      throw new IllegalArgumentException("Meta connection owner identity is required.");
    }
    return normalized;
  }

  private static String normalize(String value) {
    return value == null ? null : value.trim();
  }

  private static Map<MetaCapability, MetaCapabilityStatus> copyCapabilities(
      Map<MetaCapability, MetaCapabilityStatus> capabilityStatuses) {
    EnumMap<MetaCapability, MetaCapabilityStatus> copy = new EnumMap<>(MetaCapability.class);
    if (capabilityStatuses != null) {
      copy.putAll(capabilityStatuses);
    }
    return copy;
  }
}
