#!/bin/bash

# Configuracoes
APP_SCRIPT="app_dash.py"
PORT=8051
VENV_ACTIVATE=".venv/bin/activate"
LOG_FILE="app_dash.log"
PID_FILE="app_dash.pid"

function start() {
    echo "Iniciando $APP_SCRIPT..."

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "O $APP_SCRIPT ja esta rodando (PID $PID)."
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi

    if [ -f "$VENV_ACTIVATE" ]; then
        source "$VENV_ACTIVATE"
    fi

    nohup python "$APP_SCRIPT" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"

    # Aguarda ate 5s para confirmar que o processo se manteve vivo
    for i in $(seq 1 10); do
        sleep 0.5
        if ! kill -0 "$PID" 2>/dev/null; then
            rm -f "$PID_FILE"
            echo "ERRO: $APP_SCRIPT falhou ao iniciar. Veja $LOG_FILE para detalhes."
            return 1
        fi
    done

    echo "$APP_SCRIPT iniciado com sucesso na porta $PORT (PID $PID)."
}

function _kill_and_wait() {
    local PID=$1
    kill "$PID" 2>/dev/null
    for i in $(seq 1 10); do
        sleep 0.5
        if ! kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    done
    kill -9 "$PID" 2>/dev/null
}

function stop() {
    echo "Parando $APP_SCRIPT..."

    # Tenta parar pelo PID file
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            _kill_and_wait "$PID"
            rm -f "$PID_FILE"
            echo "$APP_SCRIPT (PID $PID) parado."
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi

    # Fallback: busca processo pela porta (cobre inicializacoes sem PID file)
    PIDS=$(lsof -ti ":$PORT" 2>/dev/null)
    if [ -n "$PIDS" ]; then
        echo "PID file ausente, parando pelo processo na porta $PORT (PID $PIDS)..."
        for PID in $PIDS; do
            _kill_and_wait "$PID"
        done
        echo "$APP_SCRIPT parado."
        return 0
    fi

    echo "O $APP_SCRIPT nao esta rodando no momento."
}

function status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Status: $APP_SCRIPT ESTA RODANDO (PID $PID, porta $PORT)."
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    echo "Status: $APP_SCRIPT NAO esta rodando."
}

function restart() {
    stop
    sleep 2
    start
}

function log() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "Nenhum log encontrado em '$LOG_FILE'. Inicie o app primeiro."
        exit 1
    fi

    LINES=${2:-50}

    case "$2" in
        -f|--follow)
            echo "==> Acompanhando $LOG_FILE em tempo real (Ctrl+C para sair) <=="
            tail -f "$LOG_FILE"
            ;;
        -n)
            LINES=${3:-50}
            echo "==> Ultimas $LINES linhas de $LOG_FILE <=="
            tail -n "$LINES" "$LOG_FILE"
            ;;
        "")
            echo "==> Ultimas 50 linhas de $LOG_FILE <=="
            tail -n 50 "$LOG_FILE"
            ;;
        *)
            echo "Uso: $0 log [-f | -n <linhas>]"
            exit 1
            ;;
    esac
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    log)
        log "$@"
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|log [-f | -n <linhas>]}"
        exit 1
esac
