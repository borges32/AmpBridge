#!/usr/bin/env bash
#
# start.sh - Inicia o backend OpAMP fora do container.
#
# Replica o comportamento do Dockerfile/entrypoint.sh:
#   1. Cria/usa um virtualenv local
#   2. Instala as dependencias do requirements.txt
#   3. Aguarda o banco de dados ficar disponivel
#   4. Executa as migrations (alembic upgrade head)
#   5. Sobe a aplicacao com uvicorn
#
# Uso:
#   ./start.sh                 # producao (sem reload)
#   ./start.sh --reload        # desenvolvimento (auto-reload)
#
# Variaveis de ambiente uteis (podem vir do .env):
#   HOST                 (default: 0.0.0.0)
#   PORT                 (default: 8000)
#   VENV_DIR             (default: .venv)
#   SKIP_DEPS=1          pula a instalacao de dependencias
#   SKIP_MIGRATIONS=1    pula o alembic upgrade head
#   SKIP_DB_WAIT=1       nao aguarda o banco de dados

set -euo pipefail

# Diretorio do script (raiz do backend)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Configuracoes
# ---------------------------------------------------------------------------
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

RELOAD_FLAG=""
if [[ "${1:-}" == "--reload" ]]; then
  RELOAD_FLAG="--reload"
fi

# ---------------------------------------------------------------------------
# Carrega variaveis do .env (se existir)
# ---------------------------------------------------------------------------
if [[ -f .env ]]; then
  echo ">> Carregando variaveis de ambiente do .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo ">> AVISO: arquivo .env nao encontrado. Copie .env.example para .env e ajuste."
  echo "   Atencao: ao rodar FORA do container, ajuste os hosts no DATABASE_URL e"
  echo "   OPAMP_SERVER_URL (ex.: 'postgres' -> 'localhost', 'opamp-server' -> 'localhost')."
fi

# ---------------------------------------------------------------------------
# Virtualenv
# ---------------------------------------------------------------------------
if [[ ! -d "$VENV_DIR" ]]; then
  echo ">> Criando virtualenv em $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ---------------------------------------------------------------------------
# Dependencias
# ---------------------------------------------------------------------------
if [[ "${SKIP_DEPS:-0}" != "1" ]]; then
  echo ">> Instalando dependencias (requirements.txt)"
  pip install --upgrade pip >/dev/null
  pip install -r requirements.txt
else
  echo ">> SKIP_DEPS=1 -> pulando instalacao de dependencias"
fi

# ---------------------------------------------------------------------------
# Aguarda o banco de dados
# ---------------------------------------------------------------------------
# Extrai host e porta do DATABASE_URL (formato: postgresql+asyncpg://user:pass@host:port/db)
parse_db_endpoint() {
  local url="${DATABASE_URL:-}"
  [[ -z "$url" ]] && return 1
  local hostport="${url##*@}"     # remove tudo ate o @
  hostport="${hostport%%/*}"      # remove /db em diante
  DB_HOST="${hostport%%:*}"
  DB_PORT="${hostport##*:}"
  [[ "$DB_PORT" == "$DB_HOST" ]] && DB_PORT="5432"
}

if [[ "${SKIP_DB_WAIT:-0}" != "1" ]]; then
  if parse_db_endpoint; then
    echo ">> Aguardando banco de dados em $DB_HOST:$DB_PORT ..."
    for i in $(seq 1 60); do
      if (exec 3<>"/dev/tcp/$DB_HOST/$DB_PORT") 2>/dev/null; then
        exec 3>&- 3<&-
        echo ">> Banco de dados disponivel."
        break
      fi
      if [[ "$i" == "60" ]]; then
        echo ">> ERRO: banco de dados nao respondeu apos 60 tentativas." >&2
        exit 1
      fi
      sleep 1
    done
  else
    echo ">> AVISO: DATABASE_URL nao definido; pulando espera do banco."
  fi
fi

# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------
if [[ "${SKIP_MIGRATIONS:-0}" != "1" ]]; then
  echo ">> Executando migrations (alembic upgrade head)"
  alembic upgrade head
else
  echo ">> SKIP_MIGRATIONS=1 -> pulando migrations"
fi

# ---------------------------------------------------------------------------
# Aplicacao
# ---------------------------------------------------------------------------
echo ">> Iniciando aplicacao em http://$HOST:$PORT"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
