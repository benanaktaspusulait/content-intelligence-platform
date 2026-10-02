package com.pompom.creative.openart;

import com.pompom.creative.openart.dto.*;
import java.math.BigDecimal;
import java.nio.file.Path;

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

  /** Check if service is available. */
  boolean isAvailable();
}
