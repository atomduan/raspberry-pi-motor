#!/bin/bash

# 小车服务端管理脚本（无需sudo）
# 用法: ./start_server.sh [start|stop|restart|status]

# 配置参数
SCRIPT_DIR="/home/pi/motor"
SCRIPT_NAME="server.py"
LOG_FILE="$SCRIPT_DIR/server.log"
PID_FILE="$SCRIPT_DIR/server.pid"
PORT=5000

# 检查服务是否正在运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# 启动服务
start() {
    if is_running; then
        echo "服务已经在运行 (PID: $(cat $PID_FILE))"
        exit 0
    fi

    echo "启动小车服务端..."
    cd "$SCRIPT_DIR" || exit 1
    
    # 清理旧日志（保留最近1000行）
    if [ -f "$LOG_FILE" ]; then
        tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp"
        mv "${LOG_FILE}.tmp" "$LOG_FILE"
        echo "[$(date)] --- 服务重启 ---" >> "$LOG_FILE"
    fi
    
    # 使用nohup启动服务
    nohup python3 "$SCRIPT_NAME" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    # 等待服务启动
    sleep 1
    if is_running; then
        echo "服务已启动，PID: $(cat $PID_FILE)"
        echo "日志文件: $LOG_FILE"
        echo "查看实时日志: tail -f $LOG_FILE"
    else
        echo "服务启动失败，请检查日志文件: $LOG_FILE"
        exit 1
    fi
}

# 停止服务
stop() {
    if ! is_running; then
        echo "服务未运行"
        exit 0
    fi

    echo "正在停止服务 (PID: $(cat $PID_FILE))..."
    PID=$(cat "$PID_FILE")
    
    # 尝试优雅关闭
    kill "$PID" 2>/dev/null
    
    # 等待服务停止
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "服务已停止"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # 强制终止
    echo "服务未在10秒内停止，强制终止..."
    kill -9 "$PID" 2>/dev/null
    rm -f "$PID_FILE"
    echo "服务已强制停止"
}

# 显示状态
status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo "服务正在运行，PID: $PID"
        echo "监听端口: $PORT"
        echo "日志文件: $LOG_FILE"
        echo "最近日志:"
        tail -n 5 "$LOG_FILE"
    else
        echo "服务未运行"
    fi
}

# 主逻辑
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    status)
        status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0
