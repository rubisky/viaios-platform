# ---- Build stage ----
FROM eclipse-temurin:21-jdk AS builder
WORKDIR /workspace

COPY gradlew gradlew.bat settings.gradle ./
COPY gradle/ gradle/
RUN chmod +x gradlew

COPY build.gradle ./
COPY src/ src/

RUN ./gradlew bootJar --no-daemon -x test

# ---- Run stage ----
FROM eclipse-temurin:21-jre
WORKDIR /app

RUN groupadd --system viaios && useradd --system --gid viaios viaios
USER viaios

COPY --from=builder /workspace/build/libs/*.jar app.jar

EXPOSE 8083

ENTRYPOINT ["java", \
    "-XX:+UseZGC", \
    "-XX:MaxRAMPercentage=75.0", \
    "-Djava.security.egd=file:/dev/./urandom", \
    "-jar", "app.jar"]
