#!/usr/bin/python

import RPi.GPIO as GPIO
import time

# 设置引脚
IN1 = 7   # 接 L298N IN1
IN2 = 8   # 接 L298N IN2

# 使用 BCM 编号
GPIO.setmode(GPIO.BCM)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)

def bell_on():
    """打开闹铃（正向通电）"""
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    print("🔔 闹铃已开启！")

def bell_off():
    """关闭闹铃"""
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    print("🔕 闹铃已关闭。")

def bell_ring_brief(duration=0.5):
    """短暂鸣响一次（模拟“叮”一声）"""
    bell_on()
    time.sleep(duration)
    bell_off()

try:
    # 示例：响3秒，停1秒，再响2次短铃
    bell_on()
    time.sleep(3)
    bell_off()
    time.sleep(1)

    for i in range(2):
        bell_ring_brief(0.3)
        time.sleep(0.3)

except KeyboardInterrupt:
    pass
finally:
    bell_off()  # 确保关闭
    GPIO.cleanup()
