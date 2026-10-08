package com.pompom.metapublisher.api;

import com.pompom.metapublisher.security.MetaWriteCapabilityGuard;
import com.pompom.metapublisher.service.MetaPublishService;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishResult;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/v1")
public class MetaPublisherController {

  private final MetaPublishService service;
  private final MetaWriteCapabilityGuard guard;

  public MetaPublisherController(MetaPublishService service, MetaWriteCapabilityGuard guard) {
    this.service = service;
    this.guard = guard;
  }

  @PostMapping("/publish")
  public PublishResult publish(
      @RequestHeader(value = MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, required = false)
          String internalToken,
      @RequestHeader(value = MetaWriteCapabilityGuard.CALLER_ENABLED_HEADER, required = false)
          String callerEnabled,
      @RequestHeader(value = MetaWriteCapabilityGuard.CAPABILITY_HEADER, required = false)
          String capability,
      @Valid @RequestBody PublishCommand command) {
    guard.assertPublishAllowed(
        internalToken, callerEnabled, capability, command.platformAccountId());
    return service.publish(command, guard.normalizeCapability(capability));
  }

  @PostMapping("/reconcile")
  public PublishResult reconcile(
      @RequestHeader(value = MetaWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, required = false)
          String internalToken,
      @Valid @RequestBody MetaPublishService.ReconcileCommand command) {
    guard.assertInternalCaller(internalToken);
    if (command == null) {
      throw new IllegalArgumentException("reconciliation command is required");
    }
    guard.normalizeCapability(command.capability());
    return service.reconcile(command);
  }

  @ExceptionHandler(MetaWriteCapabilityGuard.UnauthorizedException.class)
  ResponseEntity<ApiError> unauthorized(RuntimeException exception) {
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(new ApiError("unauthorized"));
  }

  @ExceptionHandler(MetaWriteCapabilityGuard.ForbiddenException.class)
  ResponseEntity<ApiError> forbidden(RuntimeException exception) {
    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(new ApiError("forbidden"));
  }

  @ExceptionHandler(MetaWriteCapabilityGuard.UnsupportedCapabilityException.class)
  ResponseEntity<ApiError> unsupportedCapability(RuntimeException exception) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(new ApiError("unsupported_capability"));
  }

  @ExceptionHandler(MetaPublishService.IdempotencyConflictException.class)
  ResponseEntity<ApiError> idempotencyConflict(RuntimeException exception) {
    return ResponseEntity.status(HttpStatus.CONFLICT).body(new ApiError("idempotency_conflict"));
  }

  @ExceptionHandler(IllegalArgumentException.class)
  ResponseEntity<ApiError> invalidRequest(IllegalArgumentException exception) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(new ApiError("invalid_request"));
  }

  public record ApiError(String error) {}
}
