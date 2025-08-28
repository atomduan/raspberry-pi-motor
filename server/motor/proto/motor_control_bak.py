#!/usr/bin/python
import RPi.GPIO as GPIO
import time
import sys
import tty
import termios

# 设置GPIO模式（BCM编号）
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# 定义电机控制引脚（BCM编码）
# 左前电机
lf_in1, lf_in2, lf_en = 17, 18, 22
# 右前电机
rf_in1, rf_in2, rf_en = 23, 24, 25
# 左后电机
lb_in1, lb_in2, lb_en = 4, 14, 15
# 右后电机
rb_in1, rb_in2, rb_en = 10, 9, 11

# 初始化所有GPIO（包括PWM引脚）
all_pins = [lf_in1, lf_in2, lf_en,
           rf_in1, rf_in2, rf_en,
           lb_in1, lb_in2, lb_en,
           rb_in1, rb_in2, rb_en]

for pin in all_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, False)  # 初始化为低电平

# 初始化PWM（必须在GPIO.setup之后）
lf_pwm = GPIO.PWM(lf_en, 1000)  # 频率1kHz
rf_pwm = GPIO.PWM(rf_en, 1000)
lb_pwm = GPIO.PWM(lb_en, 1000)
rb_pwm = GPIO.PWM(rb_en, 1000)

# 启动PWM（初始占空比0）
lf_pwm.start(0)
rf_pwm.start(0)
lb_pwm.start(0)
rb_pwm.start(0)

def set_motor_speed(pwm, in1, in2, speed):
    """设置单个电机速度和方向"""
    if speed > 0:  # 正转
        GPIO.output(in1, True)
        GPIO.output(in2, False)
        pwm.ChangeDutyCycle(speed)
    elif speed < 0:  # 反转
        GPIO.output(in1, False)
        GPIO.output(in2, True)
        pwm.ChangeDutyCycle(-speed)
    else:  # 停止
        GPIO.output(in1, False)
        GPIO.output(in2, False)
        pwm.ChangeDutyCycle(0)

def forward(speed=30):
    """前进"""
    set_motor_speed(lf_pwm, lf_in1, lf_in2, speed)
    set_motor_speed(rf_pwm, rf_in1, rf_in2, speed)
    set_motor_speed(lb_pwm, lb_in1, lb_in2, speed)
    set_motor_speed(rb_pwm, rb_in1, rb_in2, speed)

def backward(speed=30):
    """后退"""
    set_motor_speed(lf_pwm, lf_in1, lf_in2, -speed)
    set_motor_speed(rf_pwm, rf_in1, rf_in2, -speed)
    set_motor_speed(lb_pwm, lb_in1, lb_in2, -speed)
    set_motor_speed(rb_pwm, rb_in1, rb_in2, -speed)

def left(speed=50):
    """左转（差速转向）"""
    set_motor_speed(lf_pwm, lf_in1, lf_in2, -speed)
    set_motor_speed(rf_pwm, rf_in1, rf_in2, speed)
    set_motor_speed(lb_pwm, lb_in1, lb_in2, -speed)
    set_motor_speed(rb_pwm, rb_in1, rb_in2, speed)

def right(speed=50):
    """右转（差速转向）"""
    set_motor_speed(lf_pwm, lf_in1, lf_in2, speed)
    set_motor_speed(rf_pwm, rf_in1, rf_in2, -speed)
    set_motor_speed(lb_pwm, lb_in1, lb_in2, speed)
    set_motor_speed(rb_pwm, rb_in1, rb_in2, -speed)

def stop():
    """停止所有电机"""
    for pin in all_pins:
        GPIO.output(pin, False)
    lf_pwm.ChangeDutyCycle(0)
    rf_pwm.ChangeDutyCycle(0)
    lb_pwm.ChangeDutyCycle(0)
    rb_pwm.ChangeDutyCycle(0)

def get_key():
    """获取键盘按键（非阻塞）"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

if __name__ == "__main__":
    try:
        print("方向键控制：↑(前进) ↓(后退) ←(左转) →(右转) 松开按键停止 Q(退出)")
        current_key = None

        while True:
            key = get_key()

            # 处理退出命令
            if key.lower() == 'q':
                break

            # 方向键需要读取3个字符
            if key == '\x1b':
                key += get_key() + get_key()

            # 如果按键状态改变
            if key != current_key:
                # 先停止之前的动作
                stop()

                # 更新当前按键状态
                current_key = key

                # 执行新动作
                if key == '\x1b[A':  # 上箭头
                    forward()
                    print("前进")
                elif key == '\x1b[B':  # 下箭头
                    backward()
                    print("后退")
                elif key == '\x1b[D':  # 左箭头
                    left()
                    print("左转")
                elif key == '\x1b[C':  # 右箭头
                    right()
                    print("右转")
                elif key == ' ':  # 空格
                    stop()
                    print("停止")
                else:
                    # 其他按键则停止
                    stop()
                    current_key = None
            else:
                # 按键未改变，保持当前状态
                pass

            time.sleep(0.01)  # 更快的响应速度

    except KeyboardInterrupt:
        print("程序被中断")
    finally:
        stop()
        GPIO.cleanup()
        print("GPIO已清理，程序退出")
