package com.pompom.creative.postrender;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAsset;
import java.util.LinkedHashMap;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/** Inspects these exact downloaded bytes, never a previous video-level analysis. */
@Component
@RequiredArgsConstructor
public class StoryVideoQcClient {
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper mapper;

  @Value("${pompom.qa.service.url:http://localhost:8001}")
  private String serviceUrl;

  public Map<String, Object> inspect(RenderAsset asset) {
    try {
      var body = new LinkedHashMap<String, Object>();
      body.put("relativePath", asset.getRelativePath());
      String serialized = asset.getRenderJob().getCreativeContractSnapshot();
      var snapshot = mapper.readTree(serialized == null ? "{}" : serialized);
      var contract = snapshot.path("intent").get("visualAcceptanceContract");
      if (contract == null) contract = snapshot.get("visualAcceptanceContract");
      body.put("visualAcceptanceContract", contract);
      Map<String, Object> result = restClientBuilder.baseUrl(serviceUrl).build().post()
          .uri("/v1/analysis/video-qc").body(body).retrieve()
          .body(new ParameterizedTypeReference<>() {});
      if (result != null && asset.getSha256() != null && asset.getSha256().equals(result.get("assetHash")))
        return result;
      return unavailable("QC response did not match the downloaded asset checksum");
    } catch (Exception error) {
      return unavailable("QC inspection unavailable: " + error.getClass().getSimpleName());
    }
  }

  private Map<String, Object> unavailable(String reason) {
    return Map.of("status", "VIDEO_QC_NOT_EVALUATED", "approvalBlocked", true, "reason", reason);
  }
}
