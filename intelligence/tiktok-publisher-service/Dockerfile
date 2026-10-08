# Build from the repository root:
# docker build -f intelligence/tiktok-publisher-service/Dockerfile .
FROM maven:3.9.9-amazoncorretto-21 AS build
WORKDIR /workspace
COPY intelligence/publisher-contract/pom.xml intelligence/publisher-contract/pom.xml
COPY intelligence/publisher-contract/src intelligence/publisher-contract/src
COPY intelligence/publisher-service-support/pom.xml intelligence/publisher-service-support/pom.xml
COPY intelligence/publisher-service-support/src intelligence/publisher-service-support/src
COPY intelligence/tiktok-publisher-service/pom.xml intelligence/tiktok-publisher-service/pom.xml
COPY intelligence/tiktok-publisher-service/src intelligence/tiktok-publisher-service/src
RUN mvn -q -f intelligence/publisher-contract/pom.xml -DskipTests install \
    && mvn -q -f intelligence/publisher-service-support/pom.xml -DskipTests install \
    && mvn -q -f intelligence/tiktok-publisher-service/pom.xml -Dmaven.test.skip=true package

FROM amazoncorretto:21-alpine
RUN addgroup -S pompom && adduser -S -G pompom pompom
WORKDIR /app
COPY --from=build /workspace/intelligence/tiktok-publisher-service/target/tiktok-publisher-service-*.jar app.jar
RUN chown -R pompom:pompom /app
USER pompom
EXPOSE 8083
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=20 \
  CMD wget -q -O - http://127.0.0.1:8083/actuator/health || exit 1
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
