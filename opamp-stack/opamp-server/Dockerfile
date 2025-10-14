# opamp-server/Dockerfile
FROM golang:1.23.2 AS builder
WORKDIR /opamp-go

# Copia todo o código fonte do opamp-go para dentro do container
COPY opamp-go/ .

# Muda para o diretório de examples (onde está o go.mod correto)
WORKDIR /opamp-go/internal/examples

# Compila o example server (com UI)
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /tmp/opamp-server ./server

FROM alpine:3.20
# Copia binário e a pasta de UI exatamente como o example server espera
WORKDIR /app
COPY --from=builder /tmp/opamp-server /usr/local/bin/opamp-server
COPY --from=builder /opamp-go/internal/examples/server/uisrv /app/uisrv
# (opcional) se quiser copiar exemplos de certs, ajuste este COPY:
# COPY --from=builder /src/opamp-go/internal/examples/certs /app/certs

EXPOSE 4320 4321
# Garanta que o processo rode no /app (onde está /app/uisrv/...)
WORKDIR /app
ENTRYPOINT ["/usr/local/bin/opamp-server"]
# ...


