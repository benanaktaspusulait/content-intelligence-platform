FROM maven:3.9.9-amazoncorretto-21 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline
COPY src src
RUN mvn -q -Dmaven.test.skip=true package

FROM amazoncorretto:21-alpine
ARG TARGETARCH
ARG OPENART_VERSION=0.1.1
RUN apk add --no-cache ca-certificates curl ffmpeg tar \
    && case "${TARGETARCH:-amd64}" in \
         amd64) OPENART_ARCH=amd64 ;; \
         arm64) OPENART_ARCH=arm64 ;; \
         *) echo "Unsupported OpenArt target architecture: ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && OPENART_ARCHIVE="openart_${OPENART_VERSION}_linux_${OPENART_ARCH}.tar.gz" \
    && curl -fsSL -o "/tmp/${OPENART_ARCHIVE}" \
       "https://github.com/OpenArt-AI/cli/releases/download/v${OPENART_VERSION}/${OPENART_ARCHIVE}" \
    && curl -fsSL -o /tmp/openart-checksums.txt \
       "https://github.com/OpenArt-AI/cli/releases/download/v${OPENART_VERSION}/checksums.txt" \
    && cd /tmp \
    && grep "  ${OPENART_ARCHIVE}$" openart-checksums.txt | sha256sum -c - \
    && tar -xzf "/tmp/${OPENART_ARCHIVE}" \
    && install -m 0755 /tmp/openart /usr/local/bin/openart \
    && rm -f "/tmp/${OPENART_ARCHIVE}" /tmp/openart /tmp/openart-checksums.txt
WORKDIR /app
COPY --from=build /workspace/target/creative-render-service-*.jar app.jar
EXPOSE 8081
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=20 \
  CMD curl -f http://localhost:8081/actuator/health || exit 1
ENTRYPOINT ["java","-jar","/app/app.jar"]
