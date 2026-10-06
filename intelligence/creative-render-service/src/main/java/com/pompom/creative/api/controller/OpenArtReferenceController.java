package com.pompom.creative.api.controller;

import com.pompom.creative.openart.OpenArtAdapter;
import com.pompom.creative.openart.OpenArtCapabilities;
import com.pompom.creative.openart.OpenArtReferenceAsset;
import com.pompom.creative.openart.OpenArtReferenceCatalogService;
import java.nio.file.Path;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/openart/references")
@RequiredArgsConstructor
public class OpenArtReferenceController {

  private final OpenArtReferenceCatalogService catalog;
  private final OpenArtAdapter adapter;

  @GetMapping("/capabilities")
  public OpenArtCapabilities capabilities() {
    return adapter.capabilities();
  }

  @GetMapping
  public List<OpenArtReferenceAsset> list(
      @RequestParam(value = "canonicalKey", required = false) String canonicalKey) {
    return catalog.list(canonicalKey);
  }

  @PostMapping("/sync")
  public ResponseEntity<SyncResponse> sync(@RequestBody SyncRequest request) {
    int workspace = request.workspace() ? catalog.syncWorkspaceAssets().size() : 0;
    int local =
        request.local() == null
            ? 0
            : request.local().stream()
                .map(
                    item ->
                        catalog.syncLocalReference(
                            item.canonicalKey(), item.displayName(), Path.of(item.localPath())))
                .toList()
                .size();
    return ResponseEntity.ok(new SyncResponse(workspace, local));
  }

  public record SyncRequest(boolean workspace, List<LocalReference> local) {}

  public record LocalReference(String canonicalKey, String displayName, String localPath) {}

  public record SyncResponse(int workspaceAssets, int localAssets) {}
}
