package com.viaios.gateway;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.HandlerMapping;
import org.springframework.web.reactive.handler.SimpleUrlHandlerMapping;
import org.springframework.web.reactive.socket.WebSocketHandler;
import org.springframework.web.reactive.socket.server.support.WebSocketHandlerAdapter;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;
import org.springframework.web.reactive.socket.WebSocketSession;
import org.springframework.web.reactive.socket.WebSocketMessage;

import java.time.Duration;
import java.util.Map;

@Configuration
public class WebSocketConfig {

    private final Sinks.Many<String> eventSink = Sinks.many().multicast().onBackpressureBuffer();

    @Bean
    public Sinks.Many<String> eventSink() { return eventSink; }

    @Bean
    public WebSocketHandlerAdapter handlerAdapter() { return new WebSocketHandlerAdapter(); }

    @Bean
    public HandlerMapping webSocketMapping() {
        SimpleUrlHandlerMapping mapping = new SimpleUrlHandlerMapping();
        mapping.setUrlMap(Map.of("/ws/events", wsHandler()));
        mapping.setOrder(-1);
        return mapping;
    }

    @Bean
    public WebSocketHandler wsHandler() {
        return session -> {
            Flux<String> events = eventSink.asFlux()
                .mergeWith(Flux.interval(Duration.ofSeconds(30))
                    .map(i -> "{\"type\":\"heartbeat\",\"ts\":" + System.currentTimeMillis() + "}"));

            return session.send(events.map(session::textMessage));
        };
    }

    public void publish(String event) { eventSink.tryEmitNext(event); }
}
