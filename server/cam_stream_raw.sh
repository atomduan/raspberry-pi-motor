#!/bin/bash
#raspivid -t 0 -w 640 -h 480 -fps 30 -hf -b 2000000 -o - | \
#nc -u -w 1 192.168.1.5 5000
#raspivid -t 0 -w 640 -h 480 -fps 30 -b 2000000 -o - | \
#gst-launch-1.0 fdsrc ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=192.168.1.5 port=5000
#raspivid -t 0 -w 640 -h 480 -fps 30 -b 2000000 -o - | \
#ncat --send-only --udp 192.168.1.5 5000

# 设置目标地址和端口
RECEIVER_IP="192.168.1.5"  # 替换为你的接收方 IP
PORT="33064"

# 分辨率、帧率、码率设置
WIDTH=640
HEIGHT=480
FPS=25
BITRATE=500000

echo "Starting auto-reconnecting video stream..."

while true; do
    echo "[$(date)] Starting stream to $RECEIVER_IP:$PORT..."
    # 开始推流
    raspivid -t 0 -w $WIDTH -h $HEIGHT -fps $FPS -b $BITRATE -o - | \
    # pv -L 1m | nc $RECEIVER_IP $PORT
    nc $RECEIVER_IP $PORT
    # nc -s 192.168.1.100 -u -w 1 $RECEIVER_IP $PORT
    # 如果退出状态不是正常退出（即出错），则等待重试
    if [ $? -ne 0 ]; then
        echo "[$(date)] Connection failed or closed. Retrying in 1 second..."
    fi
    sleep 1
done
