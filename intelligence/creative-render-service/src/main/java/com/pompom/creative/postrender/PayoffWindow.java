package com.pompom.creative.postrender;

public record PayoffWindow(
    PayoffWindowStatus status,
    Double startSeconds,
    Double endSeconds,
    String source,
    String reason) {}
