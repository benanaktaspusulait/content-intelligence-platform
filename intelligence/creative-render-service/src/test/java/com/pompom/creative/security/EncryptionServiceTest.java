package com.pompom.creative.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import javax.crypto.SecretKey;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class EncryptionServiceTest {

  private EncryptionService encryptionService;

  @BeforeEach
  void setUp() {
    // Generate test key
    SecretKey testKey = EncryptionService.generateKey();
    String testKeyBase64 = EncryptionService.keyToBase64(testKey);

    encryptionService = new EncryptionService(testKeyBase64);
  }

  @Test
  void encrypt_plaintext_returnsBase64EncodedString() {
    // Given
    String plaintext = "test-access-token-123";

    // When
    String encrypted = encryptionService.encrypt(plaintext);

    // Then
    assertThat(encrypted).isNotNull();
    assertThat(encrypted).isNotEmpty();
    assertThat(encrypted).isNotEqualTo(plaintext);
    assertThat(encrypted).matches("^[A-Za-z0-9+/]+=*$"); // Base64 pattern
  }

  @Test
  void decrypt_encryptedText_returnsOriginalPlaintext() {
    // Given
    String plaintext = "my-secret-refresh-token";
    String encrypted = encryptionService.encrypt(plaintext);

    // When
    String decrypted = encryptionService.decrypt(encrypted);

    // Then
    assertThat(decrypted).isEqualTo(plaintext);
  }

  @Test
  void encrypt_sameTextTwice_producesDifferentCiphertext() {
    // Given
    String plaintext = "test-token";

    // When
    String encrypted1 = encryptionService.encrypt(plaintext);
    String encrypted2 = encryptionService.encrypt(plaintext);

    // Then
    assertThat(encrypted1).isNotEqualTo(encrypted2); // Different IVs
    assertThat(encryptionService.decrypt(encrypted1)).isEqualTo(plaintext);
    assertThat(encryptionService.decrypt(encrypted2)).isEqualTo(plaintext);
  }

  @Test
  void encrypt_nullInput_returnsNull() {
    // When
    String result = encryptionService.encrypt(null);

    // Then
    assertThat(result).isNull();
  }

  @Test
  void encrypt_emptyString_returnsNull() {
    // When
    String result = encryptionService.encrypt("");

    // Then
    assertThat(result).isNull();
  }

  @Test
  void decrypt_nullInput_returnsNull() {
    // When
    String result = encryptionService.decrypt(null);

    // Then
    assertThat(result).isNull();
  }

  @Test
  void decrypt_emptyString_returnsNull() {
    // When
    String result = encryptionService.decrypt("");

    // Then
    assertThat(result).isNull();
  }

  @Test
  void decrypt_invalidBase64_throwsException() {
    // Given
    String invalidBase64 = "not-valid-base64!!!";

    // When/Then
    assertThatThrownBy(() -> encryptionService.decrypt(invalidBase64))
        .isInstanceOf(RuntimeException.class)
        .hasMessageContaining("Failed to decrypt data");
  }

  @Test
  void decrypt_tamperedCiphertext_throwsException() {
    // Given
    String plaintext = "test-token";
    String encrypted = encryptionService.encrypt(plaintext);

    // Tamper with ciphertext (change last character)
    String tampered = encrypted.substring(0, encrypted.length() - 1) + "X";

    // When/Then
    assertThatThrownBy(() -> encryptionService.decrypt(tampered))
        .isInstanceOf(RuntimeException.class)
        .hasMessageContaining("Failed to decrypt data");
  }

  @Test
  void isConfigured_withKey_returnsTrue() {
    // Then
    assertThat(encryptionService.isConfigured()).isTrue();
  }

  @Test
  void encryptDecrypt_longText_worksCorrectly() {
    // Given
    String longText = "a".repeat(1000);

    // When
    String encrypted = encryptionService.encrypt(longText);
    String decrypted = encryptionService.decrypt(encrypted);

    // Then
    assertThat(decrypted).isEqualTo(longText);
  }

  @Test
  void encryptDecrypt_specialCharacters_worksCorrectly() {
    // Given
    String specialText = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`";

    // When
    String encrypted = encryptionService.encrypt(specialText);
    String decrypted = encryptionService.decrypt(encrypted);

    // Then
    assertThat(decrypted).isEqualTo(specialText);
  }
}
