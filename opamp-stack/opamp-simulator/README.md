# OpAMP Agent Load Simulator

Simulador de carga para o servidor OpAMP. Cria agentes OpenTelemetry Collector simulados que conectam via WebSocket ao opamp-go, permitindo testar o desempenho do servidor e do backend com milhares de agentes simultâneos.

## O que foi implementado

### Agente simulado realista

Cada agente simulado reproduz o comportamento de um OpenTelemetry Collector real conectado via OpAMP:

- **Identidade**: UUID v7 único por agente, hostname no formato `otel-sim-00001`, atributos de serviço (`service.name`, `service.version`, `service.instance.id`)
- **Atributos do host**: `host.name`, `os.type`, `os.description`, `host.arch`
- **Health completo**: Status de saude com `ComponentHealthMap` contendo:
  - `extensions` (health_check, opamp)
  - `pipeline:traces` (receiver:otlp, processor:memory_limiter, processor:batch, exporter:otlp)
  - `pipeline:metrics` (receiver:otlp, receiver:hostmetrics, processor:memory_limiter, processor:batch, exporter:otlp)
  - `pipeline:logs` (receiver:otlp, processor:memory_limiter, processor:batch, exporter:otlp)
- **Effective config**: Configuracao YAML realista de OTel Collector (receivers, processors, exporters, extensions, pipelines)
- **Remote config**: Aceita configuracoes remotas enviadas pelo servidor e reporta status APPLIED
- **Health updates periodicos**: Cada agente envia updates de health no intervalo configurado
- **Reconexao automatica**: Backoff exponencial via biblioteca opamp-go (reconecta se o servidor cair)

### Controle de carga

- **Spawn rate**: Controle de quantos agentes sao criados por segundo (ramp-up gradual)
- **Unhealthy percent**: Porcentagem configuravel de agentes que reportam como nao-saudaveis
- **Duration**: Tempo de execucao configuravel ou infinito (ate Ctrl+C)
- **Graceful shutdown**: SIGINT/SIGTERM desconecta todos os agentes em paralelo

### Observabilidade

- Progress logging a cada N agentes spawned
- Stats reporter a cada 30 segundos (connected vs disconnected)
- Log level configuravel (debug, info, warn, error)

## Estrutura do projeto

```
opamp-simulator/
├── main.go                # Entry point, CLI flags, spawn loop, shutdown
├── simulator/
│   ├── config.go          # Loader e validacao do YAML de configuracao
│   └── agent.go           # Agente simulado usando a lib client opamp-go
├── config.yaml            # Configuracao padrao com todos os parametros
├── Dockerfile             # Build multi-stage para Docker
├── go.mod                 # Dependencias (usa opamp-go via replace local)
└── go.sum
```

## Pre-requisitos

- **Go 1.23+** instalado
- **OpAMP server** rodando (opamp-go na porta 4320)

## Build

```bash
cd opamp-simulator

# Build local (Linux)
go build -o opamp-simulator .
```

### Build para Windows

O Go suporta cross-compilation nativa. Para gerar o executavel `.exe` para Windows a partir do Linux:

```bash
cd opamp-simulator

# Windows 64-bit (AMD/Intel)
GOOS=windows GOARCH=amd64 go build -o opamp-simulator.exe .

# Windows ARM (Surface Pro X, etc.)
GOOS=windows GOARCH=arm64 go build -o opamp-simulator.exe .
```

O executavel gerado pode ser copiado e executado diretamente no Windows sem instalar Go:

```powershell
.\opamp-simulator.exe -agents 500 -rate 50
```

> **Nota**: O build precisa ser feito na maquina onde o repositorio esta clonado com o submodule `opamp-go` disponivel, pois o `go.mod` usa `replace` local.

## Uso

### Execucao basica

```bash
# Usar config.yaml padrao (100 agents, 50/sec)
./opamp-simulator

# Especificar arquivo de configuracao
./opamp-simulator -config /path/to/config.yaml
```

### Override via CLI

Os flags da CLI sobrescrevem os valores do arquivo de configuracao:

```bash
# 500 agents, spawn rate de 100/sec
./opamp-simulator -agents 500 -rate 100

# 8000 agents para teste de carga completo
./opamp-simulator -agents 8000 -rate 100

# Combinar com config customizado
./opamp-simulator -config prod-test.yaml -agents 10000 -rate 200
```

### Flags disponiveis

| Flag | Descricao | Default |
|------|-----------|---------|
| `-config` | Caminho do arquivo YAML de configuracao | `config.yaml` |
| `-agents` | Numero de agentes (sobrescreve config) | valor do config |
| `-rate` | Agentes criados por segundo (sobrescreve config) | valor do config |

## Configuracao

O arquivo `config.yaml` controla todos os parametros da simulacao.

### Conexao com servidor

```yaml
server:
  url: "ws://127.0.0.1:4320/v1/opamp"   # URL WebSocket do servidor OpAMP
  insecure_tls: true                      # InsecureSkipVerify para wss://
```

### Parametros da simulacao

```yaml
simulation:
  agent_count: 8000      # Total de agentes simulados
  spawn_rate: 100        # Agentes criados por segundo
  duration_seconds: 0    # 0 = infinito (ate Ctrl+C)
```

### Comportamento do agente

```yaml
agent:
  service_name: "io.opentelemetry.collector"
  service_version: "0.102.1"
  os_type: "linux"
  hostname_prefix: "otel-sim"        # Hostname: otel-sim-00001, otel-sim-00002, ...
  host_arch: "amd64"
  os_description: "Ubuntu 22.04.4 LTS"
  health_interval_seconds: 60        # Intervalo de health updates
  config_report_interval_seconds: 120
  unhealthy_percent: 5               # 5% dos agents reportam como unhealthy
  accept_remote_config: true         # Aceitar config remota do servidor
```

### Effective config dos agentes

O campo `effective_config` define o YAML que cada agente reporta como sua configuracao efetiva. Cada agente recebe uma variacao unica (com comentario contendo hostname e index).

```yaml
effective_config: |
  exporters:
    otlp:
      endpoint: otel-gateway:4317
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
  # ... (config completa no config.yaml)
```

### Logging

```yaml
logging:
  level: "info"              # debug, info, warn, error
  log_connections: true      # Log eventos de conexao
  progress_interval: 100     # Log a cada N agents spawned
```

## Cenarios de teste

### Teste rapido (verificacao)

```bash
./opamp-simulator -agents 10 -rate 10
```

Verifica se os agentes conectam e o servidor responde. Util apos mudancas no servidor.

### Teste medio (centenas)

```bash
./opamp-simulator -agents 500 -rate 50
```

Testa o comportamento do batch sync do backend (OPAMP_SYNC_BATCH_SIZE=100 = 5 batches).

### Teste de carga (milhares)

```bash
./opamp-simulator -agents 8000 -rate 100
```

Simula a carga de producao. 8000 agentes criados em ~80 segundos. Permite testar:

- Delta sync (skip quando nao ha mudancas)
- Pipeline health bulk upsert (8000 agents x ~15 componentes = ~120k registros)
- Config hash cache (evitar queries de config quando nao ha mudancas)
- Overlap protection no background sync

### Teste de estresse

```bash
./opamp-simulator -agents 15000 -rate 200
```

Vai alem da carga de producao para encontrar limites do sistema.

### Teste com duracao limitada

Edite o `config.yaml`:

```yaml
simulation:
  agent_count: 8000
  spawn_rate: 100
  duration_seconds: 300   # Rodar por 5 minutos apos todos conectados
```

## Docker

### Build

O Dockerfile deve ser executado a partir do diretorio raiz do projeto `opamp-stack/`, pois precisa acessar o submodulo `opamp-server/opamp-go`:

```bash
# A partir do diretorio raiz (opamp-stack/)
docker build -f opamp-simulator/Dockerfile -t opamp-simulator .
```

### Execucao

```bash
# Usar config padrao
docker run --network host opamp-simulator

# Override de agentes via CLI
docker run --network host opamp-simulator -agents 8000 -rate 100

# Config customizado via volume
docker run --network host \
  -v $(pwd)/my-config.yaml:/etc/opamp-simulator/config.yaml \
  opamp-simulator

# Apontar para servidor em outro host
docker run opamp-simulator \
  -config /etc/opamp-simulator/config.yaml \
  -agents 5000
```

> **Nota**: Use `--network host` quando o servidor OpAMP esta rodando em localhost.

## Saida esperada

```
=== OpAMP Agent Load Simulator ===
Server:      ws://127.0.0.1:4320/v1/opamp
Agents:      1000
Spawn rate:  100 agents/sec
Duration:    infinite (Ctrl+C to stop)
Hostname:    otel-sim-XXXXX
Unhealthy:   5%
==================================
Spawning 1000 agents at 100/sec...
Progress: 100/1000 spawned, 98 connected, 1.0s elapsed, 0 errors
Progress: 200/1000 spawned, 195 connected, 2.0s elapsed, 0 errors
...
Progress: 1000/1000 spawned, 993 connected, 10.0s elapsed, 0 errors
Spawn complete: 1000 agents in 10.0s (0 errors)
Status: 1000/1000 agents connected
[STATS] Connected: 1000 | Disconnected: 0 | Total: 1000
^C
Received interrupt, shutting down...
Stopping 1000 agents...
All agents stopped in 0.3s
=== Simulation ended ===
```

## Ajuste de recursos do sistema

Para simular milhares de conexoes WebSocket, pode ser necessario ajustar os limites do sistema operacional:

```bash
# Verificar limite atual de file descriptors
ulimit -n

# Aumentar para a sessao atual (necessario ~2 FDs por agent)
ulimit -n 65535

# Permanente: editar /etc/security/limits.conf
# * soft nofile 65535
# * hard nofile 65535
```

Para 8000+ agentes, recomenda-se pelo menos `ulimit -n 20000`.

## Relacao com o stack

```
                      WebSocket (porta 4320)
opamp-simulator ──────────────────────────────► opamp-go server
  (N agents)                                        │
                                                    │ HTTP API (porta 4321)
                                                    │
                                              backend (FastAPI)
                                                    │
                                              PostgreSQL
```

O simulador substitui os OTel Collectors reais para fins de teste. O fluxo e:

1. **opamp-simulator** cria N agentes que conectam via WebSocket ao **opamp-go**
2. **opamp-go** registra os agentes em memoria e expoe via API HTTP
3. **backend** (FastAPI) faz sync periodico via `/agents/status` e `/agents/full`
4. **backend** processa os dados e salva no **PostgreSQL**
