package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderJob;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class StoryVideoQcClientTest {
  @Test void completedRenderUsesSharedPersistedVideoQcWithImmutableSourcePlan() {
    var builder = RestClient.builder();
    var server = MockRestServiceServer.bindTo(builder).build();
    var client = new StoryVideoQcClient(builder, new ObjectMapper());
    ReflectionTestUtils.setField(client, "intelligenceBaseUrl", "http://intelligence");
    var id = UUID.randomUUID();
    String source = "{\"promptVersion\":\"2\",\"intent\":{\"timingIntent\":[{\"startTime\":0,\"endTime\":15,\"action\":\"Authored action\"}]}}";
    var job = RenderJob.builder().creativeContractSnapshot(source).build();
    var asset = RenderAsset.builder().videoId(id).renderJob(job).sha256("actual-bytes").relativePath("clip.mp4").build();
    server.expect(requestTo("http://intelligence/api/v1/videos/" + id + "/qc"))
        .andExpect(method(HttpMethod.POST)).andExpect(content().json(source))
        .andRespond(withSuccess("{\"assetHash\":\"actual-bytes\",\"storyStatus\":\"STORY_QC_NOT_EVALUATED\",\"approvalBlocked\":true}", MediaType.APPLICATION_JSON));
    assertThat(client.inspect(asset)).containsEntry("storyStatus", "STORY_QC_NOT_EVALUATED").containsEntry("approvalBlocked", true);
    server.verify();
  }
}
