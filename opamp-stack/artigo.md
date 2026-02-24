# Como estruturamos um stack completo para gestão de agentes OpAMP com FastAPI, PostgreSQL e Docker

Nos últimos dias, implementei uma evolução importante no nosso ambiente de observabilidade: um **backend de gestão para OpAMP** totalmente containerizado, com sincronização automática, versionamento de configuração e API REST pronta para operação.

O objetivo era simples de explicar, mas desafiador de executar: sair de um servidor OpAMP isolado e entregar uma solução realmente utilizável por times de operação.

## O problema que queríamos resolver

Ter apenas o servidor OpAMP funcionando não era suficiente para o dia a dia. Faltavam alguns pilares:

- visão consolidada de agentes e saúde;
- histórico de configuração com rastreabilidade;
- detecção de divergência e alertas;
- autenticação para operações sensíveis;
- integração fácil para times e automações.

## A arquitetura da solução

A implementação ficou organizada em quatro serviços principais:

- **HAProxy (4320)**: ponto de entrada e balanceamento;
- **OpAMP Server (4321)**: comunicação com os agentes;
- **Backend FastAPI (8000)**: regras de negócio, API e sincronização;
- **PostgreSQL (5432)**: persistência e histórico.

Tudo orquestrado via `docker-compose`, com health checks e fluxo claro entre os componentes.

## O que foi implementado

### 1. Sincronização automática com OpAMP

Um job em background sincroniza dados a cada 60 segundos:

- atualiza estado dos agentes;
- registra health history;
- identifica agentes desconectados;
- compara configurações por hash SHA256.

### 2. Versionamento de configuração

Sempre que uma configuração muda, uma nova versão é criada automaticamente. Isso trouxe:

- histórico auditável;
- comparação de mudanças;
- rastreabilidade de alterações por usuário.

### 3. Sistema de alertas de divergência

Quando há diferença entre estado esperado e real, o agente é marcado como `OUT_OF_SYNC`, permitindo ação rápida do time.

### 4. API REST completa e documentada

Entregamos uma API com endpoints para:

- autenticação JWT (`/auth/register`, `/auth/login`, `/auth/me`);
- gestão e consulta de agentes;
- histórico de saúde e configuração;
- exportação CSV;
- envio de config para agentes via OpAMP;
- sincronização manual sob demanda.

A documentação está disponível em `/docs` e `/redoc`.

## Modelo de dados

O banco PostgreSQL foi desenhado com quatro tabelas centrais:

- `users`
- `agents`
- `agent_health`
- `agent_configs`

Esse desenho cobre autenticação, estado atual e histórico operacional.

## Ganhos práticos da implementação

- stack reproduzível com um único `docker compose up -d`;
- observabilidade operacional com histórico real;
- menor risco em mudanças de configuração;
- base pronta para expansão de produto (frontend e novas automações);
- desempenho esperado para cenários comuns:
  - listagem de 50 agentes em menos de 100ms;
  - sincronização de 100 agentes em menos de 5s.

## Lições aprendidas

- sincronização contínua reduz dívida operacional;
- versionamento de config deixa troubleshooting muito mais objetivo;
- documentação técnica completa acelera onboarding e suporte.

## Próximos passos

- evoluir com frontend dedicado;
- ampliar políticas de segurança para produção;
- adicionar métricas e dashboards de operação.

---

Se você também está estruturando gestão de agentes e configuração em escala, essa abordagem com **OpAMP + FastAPI + PostgreSQL + Docker** é uma base sólida para começar rápido sem abrir mão de governança.

#OpAMP #FastAPI #PostgreSQL #Docker #Observabilidade #DevOps #SRE #Backend
