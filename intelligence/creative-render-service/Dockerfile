FROM maven:3.9.9-amazoncorretto-21 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline
COPY src src
RUN mvn -q -Dmaven.test.skip=true package

FROM amazoncorretto:21-alpine
RUN apk add --no-cache curl ffmpeg
WORKDIR /app
COPY --from=build /workspace/target/creative-render-service-*.jar app.jar
EXPOSE 8081
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=20 \
  CMD curl -f http://localhost:8081/actuator/health || exit 1
ENTRYPOINT ["java","-jar","/app/app.jar"]
