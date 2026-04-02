#!/bin/bash

# Configuracoes
APP_SCRIPT="app_dash.py"
PORT=8051
VENV_ACTIVATE=".venv/bin/activate"
LOG_FILE="app_dash.log"

function start() {
    echo "Iniciando $APP_SCRIPT..."
    if lsof -ti :$PORT > /dev/null
    then
        echo "O $APP_SCRIPT ja esta rodando na porta $PORT."
    else
        if [ -f "$VENV_ACTIVATE" ]; then
            source "$VENV_ACTIVATE"
        fi
        nohup python "$APP_SCRIPT" > "$LOG_FILE" 2>&1 &
        echo "$APP_SCRIPT iniciado com sucesso na porta $PORT."
    fi
}

function stop() {
    echo "Parando $APP_SCRIPT..."
    if lsof -ti :$PORT > /dev/null
    then
        lsof -ti :$PORT | xargs kill -9
        echo "$APP_SCRIPT (Porta $PORT) parado."
    else
        echo "O $APP_SCRIPT nao esta rodando no momento na porta $PORT."
    fi
}

function status() {
    if lsof -ti :$PORT > /dev/null
    then
        echo "Status: $APP_SCRIPT ESTA RODANDO. (Processos: $(lsof -ti :$PORT | xargs))"
    else
        echo "Status: $APP_SCRIPT NAO esta rodando."
    fi
}

function restart() {
    stop
    sleep 2
    start
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
    *)
        echo "Uso: $0 {start|stop|restart|status}"
        exit 1
esac
