FROM eclipse-temurin:17-jre-alpine AS runtime

RUN addgroup -S viaios && adduser -S viaios -G viaios

WORKDIR /app

COPY build/libs/case-service-*.jar app.jar

RUN chown -R viaios:viaios /app

USER viaios

EXPOSE 8086

ENTRYPOINT ["java", "-XX:+UseContainerSupport", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]
