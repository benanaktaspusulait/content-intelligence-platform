package com.pompom.creative;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.creative.notification.EmailNotificationService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Pins the production boot contract for mail autoconfiguration.
 *
 * <p>Every other {@code @SpringBootTest} in this module implicitly loads {@code
 * src/test/resources/application.yml}, which sets {@code spring.mail.host: localhost}. That
 * silently hides a gap in the real production config: {@code src/main/resources/application.yml}
 * never sets {@code spring.mail.host} at all. Without a host, Spring Boot's mail autoconfiguration
 * backs off entirely, no {@link org.springframework.mail.javamail.JavaMailSender} bean is created,
 * {@link EmailNotificationService} fails dependency injection, and the whole application context
 * fails to start - exactly what happened when the packaged image was run against the real
 * docker-compose stack.
 *
 * <p>This test overrides {@code spring.config.location} to boot from the real {@code
 * src/main/resources/application.yml} file instead of the test classpath copy (so the test-only
 * mail host override is not in effect), while supplying a disposable Postgres container via {@link
 * DynamicPropertySource} so Flyway/JPA can still start. It reproduces the production boot path
 * exactly except for the datasource target.
 */
@SpringBootTest(properties = "spring.config.location=file:src/main/resources/application.yml")
@Testcontainers(disabledWithoutDocker = true)
class ProductionMailAutoConfigurationTest {

  @Container
  static final PostgreSQLContainer<?> DB =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("creative_render_boot_check")
          .withUsername("render")
          .withPassword("render_test");

  @DynamicPropertySource
  static void datasourceProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DB::getJdbcUrl);
    registry.add("spring.datasource.username", DB::getUsername);
    registry.add("spring.datasource.password", DB::getPassword);
  }

  @Autowired ApplicationContext context;

  @Test
  void startsWithOnlyProductionApplicationYmlOnTheClasspath() {
    assertThat(context.getBeansOfType(EmailNotificationService.class)).hasSize(1);
  }
}
