package com.pompom.tiktokpublisher.api;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishResult;
import com.pompom.tiktokpublisher.security.TikTokWriteCapabilityGuard;
import com.pompom.tiktokpublisher.service.TikTokPublishService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Internal-only HTTP boundary; no provider or frontend route is exposed. */
@RestController
@RequestMapping("/internal/v1")
public class TikTokPublisherController {

  private final TikTokPublishService service;
  private final TikTokWriteCapabilityGuard guard;

  public TikTokPublisherController(TikTokPublishService service, TikTokWriteCapabilityGuard guard) {
    this.service = service;
    this.guard = guard;
  }

  @PostMapping("/publish")
  public PublishResult publish(
      @RequestHeader(value = TikTokWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, required = false)
          String internalToken,
      @RequestHeader(value = TikTokWriteCapabilityGuard.CALLER_ENABLED_HEADER, required = false)
          String callerEnabled,
      @RequestHeader(value = TikTokWriteCapabilityGuard.CAPABILITY_HEADER, required = false)
          String capability,
      @Valid @RequestBody PublishCommand command) {
    guard.assertPublishAllowed(
        internalToken, callerEnabled, capability, command.platformAccountId());
    return service.publish(command, guard.normalizeCapability(capability));
  }

  @PostMapping("/reconcile")
  public PublishResult reconcile(
      @RequestHeader(value = TikTokWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, required = false)
          String internalToken,
      @Valid @RequestBody TikTokPublishService.ReconcileCommand command) {
    guard.assertInternalCaller(internalToken);
    if (command == null) {
      throw new IllegalArgumentException("reconciliation command is required");
    }
    guard.normalizeCapability(command.capability());
    return service.reconcile(command);
  }

  @ExceptionHandler(TikTokWriteCapabilityGuard.UnauthorizedException.class)
  ResponseEntity<ApiError> unauthorized(RuntimeException exception) {
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(new ApiError("unauthorized"));
  }

  @ExceptionHandler(TikTokWriteCapabilityGuard.ForbiddenException.class)
  ResponseEntity<ApiError> forbidden(RuntimeException exception) {
    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(new ApiError("forbidden"));
  }

  @ExceptionHandler(TikTokWriteCapabilityGuard.UnsupportedCapabilityException.class)
  ResponseEntity<ApiError> unsupportedCapability(RuntimeException exception) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(new ApiError("unsupported_capability"));
  }

  @ExceptionHandler(TikTokPublishService.IdempotencyConflictException.class)
  ResponseEntity<ApiError> idempotencyConflict(RuntimeException exception) {
    return ResponseEntity.status(HttpStatus.CONFLICT).body(new ApiError("idempotency_conflict"));
  }

  @ExceptionHandler(IllegalArgumentException.class)
  ResponseEntity<ApiError> invalidRequest(IllegalArgumentException exception) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(new ApiError("invalid_request"));
  }

  public record ApiError(String error) {}
}
