package com.pompom.creative.openart;

/** Provider reference asset identity returned by the documented upload catalog command. */
public record OpenArtReferenceDescriptor(
    String providerAssetId, String url, String label, String mediaType) {}
