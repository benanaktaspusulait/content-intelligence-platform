package com.pompomhills.intelligence.meta;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Encrypts Meta token material before it is stored; ciphertext is never used as an API value. */
@Component
public final class MetaTokenEncryptionService {
  private static final String VERSION = "v1";
  private static final int IV_BYTES = 12;
  private static final int TAG_BITS = 128;
  private static final SecureRandom RANDOM = new SecureRandom();

  private final SecretKeySpec key;

  public MetaTokenEncryptionService(
      @Value("${pompom.security.encryption.key:}") String configuredKey) {
    this.key = deriveKey(configuredKey);
  }

  public boolean isConfigured() {
    return key != null;
  }

  public String encrypt(String plaintext) {
    if (plaintext == null || plaintext.isBlank()) {
      return null;
    }
    requireConfigured();
    byte[] iv = new byte[IV_BYTES];
    RANDOM.nextBytes(iv);
    try {
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
      byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
      return VERSION
          + ":"
          + Base64.getUrlEncoder().withoutPadding().encodeToString(iv)
          + ":"
          + Base64.getUrlEncoder().withoutPadding().encodeToString(ciphertext);
    } catch (GeneralSecurityException error) {
      throw new IllegalStateException("Meta token encryption failed.");
    }
  }

  public String decrypt(String encrypted) {
    if (encrypted == null || encrypted.isBlank()) {
      return null;
    }
    requireConfigured();
    String[] parts = encrypted.split(":", -1);
    if (parts.length != 3 || !VERSION.equals(parts[0])) {
      throw new IllegalStateException("Stored Meta token material is invalid.");
    }
    try {
      byte[] iv = Base64.getUrlDecoder().decode(parts[1]);
      byte[] ciphertext = Base64.getUrlDecoder().decode(parts[2]);
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
      return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
    } catch (GeneralSecurityException | IllegalArgumentException error) {
      throw new IllegalStateException("Stored Meta token material could not be decrypted.");
    }
  }

  private void requireConfigured() {
    if (!isConfigured()) {
      throw new IllegalStateException("Meta token encryption is not configured.");
    }
  }

  private static SecretKeySpec deriveKey(String configuredKey) {
    if (configuredKey == null || configuredKey.isBlank()) {
      return null;
    }
    try {
      byte[] digest =
          MessageDigest.getInstance("SHA-256")
              .digest(configuredKey.trim().getBytes(StandardCharsets.UTF_8));
      return new SecretKeySpec(digest, "AES");
    } catch (java.security.NoSuchAlgorithmException error) {
      throw new IllegalStateException("Meta token encryption is unavailable.");
    }
  }
}
