#!/bin/bash

# === CONFIGURATION ===
SRT_TARGET_IP="192.168.1.5"
SRT_PORT="9527"
SRT_URL="srt://${SRT_TARGET_IP}:${SRT_PORT}?pkt_size=256"

# 摄像头参数（极限优化配置）
WIDTH=480         # 分辨率进一步降低
HEIGHT=360        # 360P画质，大幅节省资源
FPS=25            # 帧率
BITRATE=1000000    # 比特率压缩到500kbps
GOP=15            # 更短的关键帧间隔
DISABLE_PREVIEW="-n" # 关闭摄像头本地预览

if ! command -v raspivid &> /dev/null || ! command -v ffmpeg &> /dev/null; then
    echo "错误：请先安装 raspivid 和 ffmpeg！"
    echo "安装命令：sudo apt install ffmpeg"
    exit 1
fi

raspivid $DISABLE_PREVIEW -o - -t 0 \
    -w $WIDTH -h $HEIGHT -fps $FPS -b $BITRATE -g $GOP \
    --codec H264 | \
ffmpeg -fflags nobuffer \
       -flags low_delay \
       -f h264 \
       -i - \
       -vcodec copy \
       -f mpegts \
       -flush_packets 1 \
       $SRT_URL &

# 降低进程优先级
PID=$!
renice -n 10 -p $PID

# 资源监控提示
echo "推流已启动（PID: $PID），资源监控："
echo "1. 实时CPU/内存：top -p $PID"
echo "2. 温度监测：vcgencmd measure_temp"
echo "3. 停止推流：kill $PID"
