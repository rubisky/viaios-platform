# VIAIOS Video Service — Go 1.21 multi-stage build
FROM golang:1.21-alpine AS builder

RUN apk add --no-cache git ca-certificates

WORKDIR /build
COPY go/go.mod go/go.sum ./
RUN go mod download

COPY go/ .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /viaios-video ./cmd/viaios-video

FROM alpine:3.19
RUN apk add --no-cache ca-certificates ffmpeg
COPY --from=builder /viaios-video /usr/local/bin/viaios-video

EXPOSE 8093
HEALTHCHECK --interval=15s --timeout=5s CMD wget -qO- http://localhost:8093/health || exit 1

ENTRYPOINT ["viaios-video"]
