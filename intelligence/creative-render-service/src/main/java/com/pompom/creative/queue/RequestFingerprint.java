package com.pompom.creative.queue;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import org.springframework.stereotype.Component;

/**
 * Computes a stable SHA-256 digest of a queue request's canonical JSON form (POJO properties and
 * map entries both sorted by key), so {@code RenderJobQueueService} can tell a legitimate
 * idempotent replay (same {@code Idempotency-Key}, same fingerprint) apart from a conflicting reuse
 * of the same key with different parameters (same key, different fingerprint).
 */
@Component
public class RequestFingerprint {

  private final ObjectMapper canonicalMapper;

  public RequestFingerprint(ObjectMapper baseMapper) {
    this.canonicalMapper =
        baseMapper
            .copy()
            .enable(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY)
            .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);
  }

  public String sha256(QueueRenderJobRequest request) {
    try {
      byte[] canonicalJson = canonicalMapper.writeValueAsBytes(request);
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      return HexFormat.of().formatHex(digest.digest(canonicalJson));
    } catch (NoSuchAlgorithmException error) {
      throw new IllegalStateException("SHA-256 is unavailable", error);
    } catch (JsonProcessingException error) {
      throw new IllegalArgumentException("Unable to canonicalize queue request", error);
    }
  }
}
