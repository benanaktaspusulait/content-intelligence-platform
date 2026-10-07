package com.pompom.publishersupport;

import com.pompom.publishercontract.PublishCommand;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import java.util.Comparator;
import java.util.Set;
import java.util.stream.Collectors;

/** Validates the provider-neutral boundary before a publisher service performs any side effect. */
public final class PublisherRequestValidator {

  /** The existing control-plane publication title storage bound. */
  public static final int MAX_TITLE_LENGTH = 500;

  /** Maximum persisted command idempotency-key size. */
  public static final int MAX_KEY_LENGTH = 200;

  /** The documented shared caption bound; provider services may apply stricter rules later. */
  public static final int MAX_CAPTION_LENGTH = 2200;

  private final Validator beanValidator;

  public PublisherRequestValidator() {
    this(Validation.buildDefaultValidatorFactory().getValidator());
  }

  PublisherRequestValidator(Validator beanValidator) {
    this.beanValidator = beanValidator;
  }

  /**
   * Validates a command without normalizing or enriching it.
   *
   * @throws IllegalArgumentException when the shared command boundary is invalid
   */
  public void validate(PublishCommand command) {
    if (command == null) {
      throw new IllegalArgumentException("publish command is required");
    }

    Set<ConstraintViolation<PublishCommand>> violations = beanValidator.validate(command);
    if (!violations.isEmpty()) {
      throw new IllegalArgumentException(formatViolations(violations));
    }

    if (command.idempotencyKey().length() > MAX_KEY_LENGTH) {
      throw new IllegalArgumentException(
          "idempotencyKey exceeds the persisted maximum of " + MAX_KEY_LENGTH + " characters");
    }
    if (command.title() != null && command.title().length() > MAX_TITLE_LENGTH) {
      throw new IllegalArgumentException(
          "title exceeds the shared maximum of " + MAX_TITLE_LENGTH + " characters");
    }
    if (command.caption() != null && command.caption().length() > MAX_CAPTION_LENGTH) {
      throw new IllegalArgumentException(
          "caption exceeds the shared maximum of " + MAX_CAPTION_LENGTH + " characters");
    }
  }

  /** Returns whether a command satisfies the same fail-closed validation boundary. */
  public boolean isValid(PublishCommand command) {
    try {
      validate(command);
      return true;
    } catch (IllegalArgumentException exception) {
      return false;
    }
  }

  private String formatViolations(Set<ConstraintViolation<PublishCommand>> violations) {
    return violations.stream()
        .sorted(Comparator.comparing(violation -> violation.getPropertyPath().toString()))
        .map(violation -> violation.getPropertyPath() + " " + violation.getMessage())
        .collect(Collectors.joining("; "));
  }
}
