package com.pompom.creative.openart;

import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.openart.dto.OpenArtImageRequest;
import com.pompom.creative.openart.dto.OpenArtJobResponse;
import com.pompom.creative.openart.dto.OpenArtJobStatus;
import com.pompom.creative.openart.dto.OpenArtVideoRequest;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.util.List;

public interface OpenArtAdapter {

  /** Generate first frame image from prompt. */
  OpenArtJobResponse generateImage(OpenArtImageRequest request);

  /** Generate video from prompt + first frame. */
  OpenArtJobResponse generateVideo(OpenArtVideoRequest request);

  /** Poll job status. */
  OpenArtJobStatus getJobStatus(String jobId);

  /** Download generated asset to destination path. */
  DownloadResult downloadAsset(String jobId, Path destination);

  /** Get current credit balance. */
  BigDecimal getCreditBalance();

  /** Return provider capabilities verified for the active adapter. */
  OpenArtCapabilities capabilities();

  /** List provider reference assets using the provider's documented catalog command. */
  List<OpenArtReferenceDescriptor> listReferenceAssets();

  /** Check if service is available. */
  boolean isAvailable();
}
