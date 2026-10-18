package com.pompomhills.intelligence.quality;

import java.net.http.*;
import java.time.Duration;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClient;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

class QualityMlAssessmentTimeoutTest {
  @Test void actualBuiltHttpRequestsIsolateAssessmentTimeout() throws Exception {
    var transport=mock(HttpClient.class);var response=mock(HttpResponse.class);
    when(response.statusCode()).thenReturn(200);when(response.body()).thenReturn("{}");
    when(transport.send(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(response);
    var client=new QualityMlClient("http://127.0.0.1:1",RestClient.builder());ReflectionTestUtils.setField(client,"httpClient",transport);
    var assessment=Map.<String,Object>of("role","STORY_REVIEW","context",Map.of("assessmentOnlyPolicy","ASSESSMENT_ONLY_UNKNOWN_SOURCE_V1"));
    client.workflow("creative-role",assessment);
    client.workflow("creative-role",Map.of("role","STORY_REVIEW","context",Map.of()));
    client.workflow("creative-role",Map.of("role","STORY","context",assessment.get("context")));
    client.workflow("creative-role",Map.of("role","PROMPT_OPTIMIZATION","context",assessment.get("context")));
    client.workflow("story-experiment/assessment-preflight",assessment);
    client.workflow("cpq-pilot/capabilities",Map.of());
    var capture=org.mockito.ArgumentCaptor.forClass(HttpRequest.class);
    verify(transport,times(6)).send(capture.capture(),any(HttpResponse.BodyHandler.class));
    assertThat(capture.getAllValues().stream().map(r->r.timeout().orElseThrow().toSeconds()).toList()).containsExactly(300L,25L,25L,25L,25L,130L);
    assertThat(QualityMlClient.assessmentTransportPolicy()).containsEntry("readSeconds",240).containsEntry("backendHttpSeconds",300).containsEntry("workflowDeadlineSeconds",600);
  }

  @Test void outerTimeoutAndInterruptionRetainCauseWithoutHttpRetry() throws Exception {
    for(Exception failure:new Exception[]{new HttpTimeoutException("Offline outer timeout"),new InterruptedException("Offline cancellation")}) {
      var transport=mock(HttpClient.class);when(transport.send(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenThrow(failure);
      var client=new QualityMlClient("http://127.0.0.1:1",RestClient.builder());ReflectionTestUtils.setField(client,"httpClient",transport);
      var request=Map.<String,Object>of("role","STORY_REVIEW","context",Map.of("assessmentOnlyPolicy","ASSESSMENT_ONLY_UNKNOWN_SOURCE_V1"));
      assertThatThrownBy(()->client.workflow("creative-role",request)).isInstanceOf(MlServiceException.class).hasCause(failure);
      verify(transport,times(1)).send(any(HttpRequest.class),any(HttpResponse.BodyHandler.class));
      if(failure instanceof InterruptedException)assertThat(Thread.interrupted()).isTrue();
    }
  }
}
