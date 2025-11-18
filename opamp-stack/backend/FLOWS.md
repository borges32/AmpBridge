# Diagramas de Fluxo - OpAMP Backend

Este documento apresenta os principais fluxos do sistema através de diagramas de sequência.

---

## 1. Fluxo de Sincronização Automática

```
┌──────────┐       ┌──────────────┐      ┌─────────────┐      ┌──────────┐
│ Background│       │ OpAMPService │      │ OpAMP Server│      │PostgreSQL│
│   Task    │       │              │      │             │      │          │
└─────┬────┘       └──────┬───────┘      └──────┬──────┘      └────┬─────┘
      │                   │                     │                   │
      │  [Every 60s]      │                     │                   │
      │───────────────────>                     │                   │
      │ sync_all_agents() │                     │                   │
      │                   │                     │                   │
      │                   │  GET /agents/full   │                   │
      │                   │────────────────────>│                   │
      │                   │                     │                   │
      │                   │<────────────────────│                   │
      │                   │ [agents list]       │                   │
      │                   │                     │                   │
      │                   │  FOR each agent     │                   │
      │                   │─┐                   │                   │
      │                   │ │ extract_agent_    │                   │
      │                   │ │ attributes()      │                   │
      │                   │<┘                   │                   │
      │                   │                     │                   │
      │                   │  UPSERT agent       │                   │
      │                   │────────────────────────────────────────>│
      │                   │                     │                   │
      │                   │  CREATE health      │                   │
      │                   │────────────────────────────────────────>│
      │                   │                     │                   │
      │                   │  compute_config_    │                   │
      │                   │─┐hash()             │                   │
      │                   │ │                   │                   │
      │                   │<┘                   │                   │
      │                   │                     │                   │
      │                   │  GET latest config  │                   │
      │                   │────────────────────────────────────────>│
      │                   │<────────────────────────────────────────│
      │                   │ [config or null]    │                   │
      │                   │                     │                   │
      │                   │─┐ hash changed?     │                   │
      │                   │ │                   │                   │
      │                   │<┘ YES               │                   │
      │                   │                     │                   │
      │                   │  CREATE new version │                   │
      │                   │────────────────────────────────────────>│
      │                   │                     │                   │
      │                   │  UPDATE agent:      │                   │
      │                   │  alert_config=true  │                   │
      │                   │  status_sync=       │                   │
      │                   │  OUT_OF_SYNC        │                   │
      │                   │────────────────────────────────────────>│
      │                   │                     │                   │
      │                   │  END FOR            │                   │
      │                   │                     │                   │
      │                   │  mark_disconnected()│                   │
      │                   │────────────────────────────────────────>│
      │                   │                     │                   │
      │<───────────────── │                     │                   │
      │ SyncResponse      │                     │                   │
      │ (stats)           │                     │                   │
      │                   │                     │                   │
      │  [Wait 60s]       │                     │                   │
      │                   │                     │                   │
```

---

## 2. Fluxo de Atualização de Configuração

```
┌──────┐    ┌────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────┐
│Client│    │ Router │    │ OpAMPService │    │ OpAMP Server│    │PostgreSQL│
└───┬──┘    └───┬────┘    └──────┬───────┘    └──────┬──────┘    └────┬─────┘
    │           │                │                   │                 │
    │ POST /config               │                   │                 │
    │ +Auth      │                │                   │                 │
    │───────────>│                │                   │                 │
    │           │                │                   │                 │
    │           │ Validate JWT   │                   │                 │
    │           │───┐            │                   │                 │
    │           │   │            │                   │                 │
    │           │<──┘            │                   │                 │
    │           │                │                   │                 │
    │           │ send_config_   │                   │                 │
    │           │ to_opamp()     │                   │                 │
    │           │───────────────>│                   │                 │
    │           │                │                   │                 │
    │           │                │ POST /save_config/│                 │
    │           │                │ json              │                 │
    │           │                │──────────────────>│                 │
    │           │                │                   │                 │
    │           │                │                   │ [Apply config   │
    │           │                │                   │  to agent]      │
    │           │                │                   │─┐               │
    │           │                │                   │ │               │
    │           │                │                   │<┘               │
    │           │                │                   │                 │
    │           │                │<──────────────────│                 │
    │           │                │ {success: true}   │                 │
    │           │                │                   │                 │
    │           │                │ compute_config_   │                 │
    │           │                │─┐hash()           │                 │
    │           │                │ │                 │                 │
    │           │                │<┘                 │                 │
    │           │                │                   │                 │
    │           │                │ get_next_version()│                 │
    │           │                │──────────────────────────────────────>│
    │           │                │<──────────────────────────────────────│
    │           │                │ [version N]       │                 │
    │           │                │                   │                 │
    │           │                │ CREATE config:    │                 │
    │           │                │ - version=N       │                 │
    │           │                │ - source=API_UPDATE                │
    │           │                │ - updated_by_user_id                │
    │           │                │──────────────────────────────────────>│
    │           │                │                   │                 │
    │           │                │ UPDATE agent:     │                 │
    │           │                │ - alert_config=false                │
    │           │                │ - status_sync=IN_SYNC               │
    │           │                │──────────────────────────────────────>│
    │           │                │                   │                 │
    │           │<───────────────│                   │                 │
    │           │ {success, version}                 │                 │
    │           │                │                   │                 │
    │<──────────│                │                   │                 │
    │ ConfigUpdateResponse       │                   │                 │
    │           │                │                   │                 │
```

---

## 3. Fluxo de Autenticação

```
┌──────┐    ┌────────┐    ┌────────────┐    ┌──────────────┐    ┌──────────┐
│Client│    │ Router │    │AuthService │    │UserRepository│    │PostgreSQL│
└───┬──┘    └───┬────┘    └─────┬──────┘    └──────┬───────┘    └────┬─────┘
    │           │               │                  │                  │
    │ POST /auth/register       │                  │                  │
    │───────────>│               │                  │                  │
    │           │               │                  │                  │
    │           │ create(user)  │                  │                  │
    │           │──────────────>│                  │                  │
    │           │               │                  │                  │
    │           │               │ get_password_    │                  │
    │           │               │─┐hash()          │                  │
    │           │               │ │                │                  │
    │           │               │<┘                │                  │
    │           │               │                  │                  │
    │           │               │ create()         │                  │
    │           │               │─────────────────>│                  │
    │           │               │                  │                  │
    │           │               │                  │ INSERT user      │
    │           │               │                  │─────────────────>│
    │           │               │                  │<─────────────────│
    │           │               │<─────────────────│                  │
    │           │<──────────────│ [User object]    │                  │
    │<──────────│               │                  │                  │
    │ UserResponse              │                  │                  │
    │           │               │                  │                  │
    │           │               │                  │                  │
    │ POST /auth/login          │                  │                  │
    │───────────>│               │                  │                  │
    │           │               │                  │                  │
    │           │ login()       │                  │                  │
    │           │──────────────>│                  │                  │
    │           │               │                  │                  │
    │           │               │ get_by_login()   │                  │
    │           │               │─────────────────>│                  │
    │           │               │                  │ SELECT user      │
    │           │               │                  │─────────────────>│
    │           │               │                  │<─────────────────│
    │           │               │<─────────────────│                  │
    │           │               │                  │                  │
    │           │               │ verify_password()│                  │
    │           │               │─┐                │                  │
    │           │               │ │                │                  │
    │           │               │<┘ OK             │                  │
    │           │               │                  │                  │
    │           │               │ create_access_   │                  │
    │           │               │─┐token()         │                  │
    │           │               │ │                │                  │
    │           │               │<┘                │                  │
    │           │<──────────────│                  │                  │
    │<──────────│ [JWT Token]   │                  │                  │
    │ Token     │               │                  │                  │
    │           │               │                  │                  │
    │           │               │                  │                  │
    │ GET /agents (with token)  │                  │                  │
    │───────────>│               │                  │                  │
    │           │               │                  │                  │
    │           │ get_current_  │                  │                  │
    │           │─┐user()       │                  │                  │
    │           │ │             │                  │                  │
    │           │ │ decode_token│                  │                  │
    │           │ │             │                  │                  │
    │           │ │ get_by_id() │                  │                  │
    │           │ │────────────────────────────────>│                  │
    │           │ │             │                  │ SELECT user      │
    │           │ │             │                  │─────────────────>│
    │           │ │             │                  │<─────────────────│
    │           │ │<────────────────────────────────│                  │
    │           │<┘             │                  │                  │
    │           │               │                  │                  │
    │           │ [Process request with user context]                 │
    │           │               │                  │                  │
    │<──────────│               │                  │                  │
    │ Response  │               │                  │                  │
    │           │               │                  │                  │
```

---

## 4. Fluxo de Consulta de Agent com Histórico

```
┌──────┐    ┌────────┐    ┌───────────────┐    ┌──────────┐
│Client│    │ Router │    │  Repository   │    │PostgreSQL│
└───┬──┘    └───┬────┘    └───────┬───────┘    └────┬─────┘
    │           │                 │                  │
    │ GET /agents/{id}            │                  │
    │───────────>│                 │                  │
    │           │                 │                  │
    │           │ get_by_instance_│                  │
    │           │ id()            │                  │
    │           │────────────────>│                  │
    │           │                 │                  │
    │           │                 │ SELECT FROM      │
    │           │                 │ agents WHERE...  │
    │           │                 │─────────────────>│
    │           │                 │<─────────────────│
    │           │<────────────────│                  │
    │<──────────│ [Agent]         │                  │
    │           │                 │                  │
    │           │                 │                  │
    │ GET /agents/{id}/health     │                  │
    │───────────>│                 │                  │
    │           │                 │                  │
    │           │ get_history_by_ │                  │
    │           │ instance_id()   │                  │
    │           │────────────────>│                  │
    │           │                 │                  │
    │           │                 │ SELECT FROM      │
    │           │                 │ agent_health     │
    │           │                 │ WHERE instance_id│
    │           │                 │ ORDER BY created │
    │           │                 │ DESC LIMIT N     │
    │           │                 │─────────────────>│
    │           │                 │<─────────────────│
    │           │<────────────────│                  │
    │<──────────│ [Health list]   │                  │
    │           │                 │                  │
    │           │                 │                  │
    │ GET /agents/{id}/configs    │                  │
    │───────────>│                 │                  │
    │           │                 │                  │
    │           │ get_history_by_ │                  │
    │           │ instance_id()   │                  │
    │           │────────────────>│                  │
    │           │                 │                  │
    │           │                 │ SELECT FROM      │
    │           │                 │ agent_configs    │
    │           │                 │ WHERE instance_id│
    │           │                 │ ORDER BY version │
    │           │                 │ DESC LIMIT N     │
    │           │                 │─────────────────>│
    │           │                 │<─────────────────│
    │           │<────────────────│                  │
    │<──────────│ [Config list]   │                  │
    │           │                 │                  │
    │           │                 │                  │
    │ GET /agents/{id}/config     │                  │
    │───────────>│                 │                  │
    │           │                 │                  │
    │           │ get_latest_by_  │                  │
    │           │ instance_id()   │                  │
    │           │────────────────>│                  │
    │           │                 │                  │
    │           │                 │ SELECT FROM      │
    │           │                 │ agent_configs    │
    │           │                 │ WHERE instance_id│
    │           │                 │ ORDER BY version │
    │           │                 │ DESC LIMIT 1     │
    │           │                 │─────────────────>│
    │           │                 │<─────────────────│
    │           │<────────────────│                  │
    │<──────────│ [YAML file]     │                  │
    │           │                 │                  │
```

---

## 5. Fluxo de Detecção de Divergência

```
┌──────────────┐       ┌──────────────┐       ┌──────────┐
│ OpAMPService │       │  Repository  │       │PostgreSQL│
└──────┬───────┘       └──────┬───────┘       └────┬─────┘
       │                      │                     │
       │  sync_agent()        │                     │
       │─┐                    │                     │
       │ │ [agent_data]       │                     │
       │<┘                    │                     │
       │                      │                     │
       │  compute_config_hash│                     │
       │─┐(effective_config) │                     │
       │ │                   │                     │
       │<┘ [new_hash]        │                     │
       │                      │                     │
       │  get_latest_config()│                     │
       │─────────────────────>│                     │
       │                      │ SELECT FROM         │
       │                      │ agent_configs       │
       │                      │ WHERE instance_id   │
       │                      │ ORDER BY version    │
       │                      │ DESC LIMIT 1        │
       │                      │────────────────────>│
       │                      │<────────────────────│
       │<─────────────────────│ [old_config or null]│
       │                      │                     │
       │─┐ Compare hashes     │                     │
       │ │                    │                     │
       │ │ new_hash !=        │                     │
       │ │ old_hash?          │                     │
       │ │                    │                     │
       │<┘ YES - DIVERGÊNCIA! │                     │
       │                      │                     │
       │  get_next_version()  │                     │
       │─────────────────────>│                     │
       │                      │ SELECT MAX(version) │
       │                      │────────────────────>│
       │                      │<────────────────────│
       │<─────────────────────│ [version N]         │
       │                      │                     │
       │  create_config()     │                     │
       │  - version = N+1     │                     │
       │  - hash = new_hash   │                     │
       │  - source = SYNC_JOB │                     │
       │─────────────────────>│                     │
       │                      │ INSERT INTO         │
       │                      │ agent_configs       │
       │                      │────────────────────>│
       │                      │<────────────────────│
       │<─────────────────────│                     │
       │                      │                     │
       │  UPDATE agent:       │                     │
       │  - alert_config=true │                     │
       │  - status_sync=      │                     │
       │    OUT_OF_SYNC       │                     │
       │─────────────────────>│                     │
       │                      │ UPDATE agents       │
       │                      │ SET alert_config=   │
       │                      │ true, status_sync=  │
       │                      │ 'OUT_OF_SYNC'       │
       │                      │────────────────────>│
       │                      │<────────────────────│
       │<─────────────────────│                     │
       │                      │                     │
       │  [Alert triggered!]  │                     │
       │                      │                     │
```

---

## Legenda

- `│` - Linha de vida do componente
- `───>` - Chamada síncrona
- `<───` - Resposta
- `─┐` e `<┘` - Processamento interno
- `[dados]` - Dados retornados
- `{objeto}` - Objeto/estrutura

---

## Notas

1. **Sincronização Automática**: Executa a cada 60s via background task
2. **Detecção de Divergência**: Usa SHA256 hash para comparação eficiente
3. **Versionamento**: Incremental por agent (cada agent tem sua sequência)
4. **Autenticação**: JWT stateless, validado em cada request protegido
5. **Histórico**: Mantido indefinidamente (considerar arquivamento futuro)

---

Para mais detalhes, consulte:
- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitetura completa
- [README.md](README.md) - Documentação da API
