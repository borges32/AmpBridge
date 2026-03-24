FROM golang:1.23-alpine AS builder

WORKDIR /app

# Copy opamp-go dependency (local replace)
COPY opamp-server/opamp-go /opamp-go

# Copy simulator source
COPY opamp-simulator/go.mod opamp-simulator/go.sum* ./

# Fix the replace directive for Docker context
RUN sed -i 's|../opamp-server/opamp-go|/opamp-go|' go.mod

RUN go mod download

COPY opamp-simulator/ ./

RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /opamp-simulator .

# ---
FROM alpine:3.19

RUN apk --no-cache add ca-certificates

COPY --from=builder /opamp-simulator /usr/local/bin/opamp-simulator
COPY opamp-simulator/config.yaml /etc/opamp-simulator/config.yaml

ENTRYPOINT ["opamp-simulator"]
CMD ["-config", "/etc/opamp-simulator/config.yaml"]
