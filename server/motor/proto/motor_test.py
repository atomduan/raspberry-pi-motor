#!/usr/bin/python

import RPi.GPIO as GPIO
import time

# 设置GPIO模式（BCM编号）
GPIO.setmode(GPIO.BCM)

# 定义引脚
IN1 = 17  # 方向控制1
IN2 = 18  # 方向控制2
EN1 = 22  # PWM调速（使能端）

# 初始化GPIO
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(EN1, GPIO.OUT)

# 创建PWM对象（频率1kHz）
pwm = GPIO.PWM(EN1, 1000)
pwm.start(50)  # 初始占空比50%

def motor_forward():
    """正转"""
    GPIO.output(IN1, True)
    GPIO.output(IN2, False)
    print("电机正转")

def motor_backward():
    """反转"""
    GPIO.output(IN1, False)
    GPIO.output(IN2, True)
    print("电机反转")

def motor_stop():
    """停止"""
    GPIO.output(IN1, False)
    GPIO.output(IN2, False)
    print("电机停止")

def set_speed(speed):
    """调速（0-100）"""
    pwm.ChangeDutyCycle(speed)
    print(f"速度设置为 {speed}%")

# 测试流程
try:
    print("测试开始！按Ctrl+C停止")
    set_speed(80)   # 高速正转

    for i in range(0, 10):
        if i % 2 == 0:
            set_speed(100)
        else:
            set_speed(70)
        motor_forward()
        time.sleep(5)
        motor_stop()
        time.sleep(1)
        motor_backward()
        time.sleep(5)
        motor_stop()
        time.sleep(1)
    
    motor_stop()    # 停止

except KeyboardInterrupt:
    print("用户中断")

finally:
    pwm.stop()      # 清理PWM
    GPIO.cleanup()  # 重置GPIO
    print("GPIO已清理")
