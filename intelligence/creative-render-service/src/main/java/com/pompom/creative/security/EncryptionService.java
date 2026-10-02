package com.pompom.creative.security;

import java.nio.ByteBuffer;
import java.security.SecureRandom;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * AES-256-GCM encryption service for sensitive data. Uses Galois/Counter Mode for authenticated
 * encryption.
 */
@Service
@Slf4j
public class EncryptionService {

  private static final String ALGORITHM = "AES/GCM/NoPadding";
  private static final int GCM_TAG_LENGTH = 128; // bits
  private static final int GCM_IV_LENGTH = 12; // bytes
  private static final int AES_KEY_SIZE = 256; // bits

  private final SecretKey secretKey;
  private final SecureRandom secureRandom;

  public EncryptionService(
      @Value("${pompom.security.encryption.key:}") String encryptionKeyBase64) {
    this.secureRandom = new SecureRandom();

    if (encryptionKeyBase64 == null || encryptionKeyBase64.isEmpty()) {
      log.warn("No encryption key provided, generating random key (NOT FOR PRODUCTION)");
      this.secretKey = generateKey();
    } else {
      byte[] decodedKey = Base64.getDecoder().decode(encryptionKeyBase64);
      this.secretKey = new SecretKeySpec(decodedKey, "AES");
      log.info("Encryption service initialized with provided key");
    }
  }

  /**
   * Encrypt plaintext string.
   *
   * @param plaintext Text to encrypt
   * @return Base64-encoded encrypted data with IV prepended
   */
  public String encrypt(String plaintext) {
    if (plaintext == null || plaintext.isEmpty()) {
      return null;
    }

    try {
      // Generate random IV
      byte[] iv = new byte[GCM_IV_LENGTH];
      secureRandom.nextBytes(iv);

      // Initialize cipher
      Cipher cipher = Cipher.getInstance(ALGORITHM);
      GCMParameterSpec parameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
      cipher.init(Cipher.ENCRYPT_MODE, secretKey, parameterSpec);

      // Encrypt
      byte[] ciphertext = cipher.doFinal(plaintext.getBytes());

      // Combine IV + ciphertext
      ByteBuffer byteBuffer = ByteBuffer.allocate(iv.length + ciphertext.length);
      byteBuffer.put(iv);
      byteBuffer.put(ciphertext);

      // Encode to Base64
      return Base64.getEncoder().encodeToString(byteBuffer.array());

    } catch (Exception e) {
      log.error("Encryption failed", e);
      throw new RuntimeException("Failed to encrypt data", e);
    }
  }

  /**
   * Decrypt encrypted string.
   *
   * @param encryptedBase64 Base64-encoded encrypted data with IV
   * @return Decrypted plaintext
   */
  public String decrypt(String encryptedBase64) {
    if (encryptedBase64 == null || encryptedBase64.isEmpty()) {
      return null;
    }

    try {
      // Decode from Base64
      byte[] decoded = Base64.getDecoder().decode(encryptedBase64);

      // Extract IV and ciphertext
      ByteBuffer byteBuffer = ByteBuffer.wrap(decoded);
      byte[] iv = new byte[GCM_IV_LENGTH];
      byteBuffer.get(iv);
      byte[] ciphertext = new byte[byteBuffer.remaining()];
      byteBuffer.get(ciphertext);

      // Initialize cipher
      Cipher cipher = Cipher.getInstance(ALGORITHM);
      GCMParameterSpec parameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
      cipher.init(Cipher.DECRYPT_MODE, secretKey, parameterSpec);

      // Decrypt
      byte[] plaintext = cipher.doFinal(ciphertext);

      return new String(plaintext);

    } catch (Exception e) {
      log.error("Decryption failed", e);
      throw new RuntimeException("Failed to decrypt data", e);
    }
  }

  /**
   * Generate a new AES-256 key. For initial key generation only - key should be persisted and
   * reused.
   */
  public static SecretKey generateKey() {
    try {
      KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
      keyGenerator.init(AES_KEY_SIZE);
      return keyGenerator.generateKey();
    } catch (Exception e) {
      throw new RuntimeException("Failed to generate encryption key", e);
    }
  }

  /** Convert SecretKey to Base64 string for storage. */
  public static String keyToBase64(SecretKey key) {
    return Base64.getEncoder().encodeToString(key.getEncoded());
  }

  /** Check if encryption is properly configured. */
  public boolean isConfigured() {
    return secretKey != null;
  }
}
