package com.pompomhills.intelligence.common.api;

import jakarta.persistence.EntityNotFoundException;
import java.time.Instant;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(EntityNotFoundException.class)
  ResponseEntity<ApiError> notFound(EntityNotFoundException error) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .body(new ApiError("NOT_FOUND", error.getMessage(), Instant.now(), Map.of()));
  }

  @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
  ResponseEntity<ApiError> badRequest(RuntimeException error) {
    return ResponseEntity.badRequest()
        .body(new ApiError("INVALID_REQUEST", error.getMessage(), Instant.now(), Map.of()));
  }

  @ExceptionHandler(MethodArgumentNotValidException.class)
  ResponseEntity<ApiError> validation(MethodArgumentNotValidException error) {
    var fields =
        error.getBindingResult().getFieldErrors().stream()
            .collect(
                java.util.stream.Collectors.toMap(
                    item -> item.getField(),
                    item -> item.getDefaultMessage() == null ? "invalid" : item.getDefaultMessage(),
                    (first, ignored) -> first));
    return ResponseEntity.badRequest()
        .body(
            new ApiError("VALIDATION_FAILED", "Request validation failed", Instant.now(), fields));
  }
}
