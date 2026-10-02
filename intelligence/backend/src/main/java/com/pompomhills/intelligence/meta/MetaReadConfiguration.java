package com.pompomhills.intelligence.meta;

import java.net.http.HttpClient;
import java.util.ArrayList;
import java.util.List;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.http.converter.AbstractHttpMessageConverter;
import org.springframework.http.converter.AbstractSmartHttpMessageConverter;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.web.client.RestClient;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties({MetaReadProperties.class, MetaOAuthProperties.class})
public class MetaReadConfiguration {
  private static final String META_GRAPH_BASE_URL = "https://graph.facebook.com";

  @Bean
  @Qualifier("metaReadRestClient") RestClient metaReadRestClient(MetaReadProperties properties) {
    HttpClient httpClient =
        HttpClient.newBuilder()
            .connectTimeout(properties.connectTimeout())
            .followRedirects(HttpClient.Redirect.NEVER)
            .version(HttpClient.Version.HTTP_1_1)
            .build();
    var requestFactory = new JdkClientHttpRequestFactory(httpClient);
    requestFactory.setReadTimeout(properties.readTimeout());

    var builder = RestClient.builder().baseUrl(META_GRAPH_BASE_URL).requestFactory(requestFactory);
    // Authorization is set per-request by MetaGraphReadClient (and OAuth flows that supply their
    // own user/page token), not as a static default header, so the effective token can change at
    // runtime after an OAuth authorization completes.
    // The Graph API returns JSON bodies with a text/javascript (and sometimes text/plain)
    // Content-Type. Widen the JSON converters so these responses can be deserialized.
    builder.messageConverters(MetaReadConfiguration::allowGraphJsonContentTypes);
    return builder.build();
  }

  private static void allowGraphJsonContentTypes(List<HttpMessageConverter<?>> converters) {
    for (var converter : converters) {
      if (converter instanceof AbstractHttpMessageConverter<?> jsonConverter) {
        widenJson(jsonConverter.getSupportedMediaTypes(), jsonConverter::setSupportedMediaTypes);
      } else if (converter instanceof AbstractSmartHttpMessageConverter<?> smartConverter) {
        widenJson(smartConverter.getSupportedMediaTypes(), smartConverter::setSupportedMediaTypes);
      }
    }
  }

  private static void widenJson(
      List<MediaType> current, java.util.function.Consumer<List<MediaType>> apply) {
    boolean handlesJson =
        current.stream().anyMatch(type -> type.isCompatibleWith(MediaType.APPLICATION_JSON));
    if (!handlesJson) {
      return;
    }
    MediaType textJavascript = new MediaType("text", "javascript");
    List<MediaType> extended = new ArrayList<>(current);
    if (!extended.contains(textJavascript)) {
      extended.add(textJavascript);
    }
    if (!extended.contains(MediaType.TEXT_PLAIN)) {
      extended.add(MediaType.TEXT_PLAIN);
    }
    apply.accept(extended);
  }
}
