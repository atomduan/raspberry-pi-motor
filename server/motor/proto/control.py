#!/usr/bin/python
import RPi.GPIO as GPIO
import time
import sys
import select
import termios
import tty
from collections import deque

# 初始化GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# 电机引脚定义
lf_in1, lf_in2, lf_en = 17, 18, 22
rf_in1, rf_in2, rf_en = 23, 24, 25
lb_in1, lb_in2, lb_en = 4, 14, 15
rb_in1, rb_in2, rb_en = 10, 9, 11

# 初始化所有GPIO
all_pins = [lf_in1, lf_in2, lf_en, rf_in1, rf_in2, rf_en,
            lb_in1, lb_in2, lb_en, rb_in1, rb_in2, rb_en]

for pin in all_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, False)

# 初始化PWM
pwm_pins = [lf_en, rf_en, lb_en, rb_en]
pwms = [GPIO.PWM(pin, 1000) for pin in pwm_pins]
for pwm in pwms:
    pwm.start(0)

def set_motor(pwm, in1, in2, speed):
    if speed > 0:
        GPIO.output(in1, True)
        GPIO.output(in2, False)
        pwm.ChangeDutyCycle(speed)
    elif speed < 0:
        GPIO.output(in1, False)
        GPIO.output(in2, True)
        pwm.ChangeDutyCycle(-speed)
    else:
        GPIO.output(in1, False)
        GPIO.output(in2, False)
        pwm.ChangeDutyCycle(0)

def forward(speed=50):
    set_motor(pwms[0], lf_in1, lf_in2, speed)
    set_motor(pwms[1], rf_in1, rf_in2, speed)
    set_motor(pwms[2], lb_in1, lb_in2, speed)
    set_motor(pwms[3], rb_in1, rb_in2, speed)

def backward(speed=50):
    set_motor(pwms[0], lf_in1, lf_in2, -speed)
    set_motor(pwms[1], rf_in1, rf_in2, -speed)
    set_motor(pwms[2], lb_in1, lb_in2, -speed)
    set_motor(pwms[3], rb_in1, rb_in2, -speed)

def left(speed=50):
    set_motor(pwms[0], lf_in1, lf_in2, -speed)
    set_motor(pwms[1], rf_in1, rf_in2, speed)
    set_motor(pwms[2], lb_in1, lb_in2, -speed)
    set_motor(pwms[3], rb_in1, rb_in2, speed)

def right(speed=50):
    set_motor(pwms[0], lf_in1, lf_in2, speed)
    set_motor(pwms[1], rf_in1, rf_in2, -speed)
    set_motor(pwms[2], lb_in1, lb_in2, speed)
    set_motor(pwms[3], rb_in1, rb_in2, -speed)

def stop():
    for pin in all_pins:
        GPIO.output(pin, False)
    for pwm in pwms:
        pwm.ChangeDutyCycle(0)

class KeyTracker:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        self.key_states = {
            'up': False,
            'down': False,
            'left': False,
            'right': False,
        }
        self.last_key_time = time.time()
        self.combo_hits = 0 

    def get_key_event(self):
        """检测按键按下/抬起事件"""
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            if ch == '\x1b':  # 可能是方向键
                ch += sys.stdin.read(2)  # 读取剩余两个字符
                self.last_key_time = time.time()
                self.combo_hits = self.combo_hits + 1
                return self._handle_arrow_key(ch, True)
            elif ch.lower() == 'q':
                return 'quit'
            return None
        else:
            return self._check_key_release()

    def _handle_arrow_key(self, ch, is_press):
        if ch == '\x1b[A':
            self.key_states['up'] = is_press
            return 'up_press' if is_press else 'up_release'
        elif ch == '\x1b[B':
            self.key_states['down'] = is_press
            return 'down_press' if is_press else 'down_release'
        elif ch == '\x1b[D':
            self.key_states['left'] = is_press
            return 'left_press' if is_press else 'left_release'
        elif ch == '\x1b[C':
            self.key_states['right'] = is_press
            return 'right_press' if is_press else 'right_release'
        return None

    def _check_key_release(self):
        """检查是否有按键抬起"""
        now = time.time()
        need_check = False
        if self.combo_hits > 0:
            if self.combo_hits == 1:
                if now - self.last_key_time > 0.5:
                    need_check = True
            else:
                if now - self.last_key_time > 0.1:
                    need_check = True
        if need_check:
            self.last_key_time = now
            for key in list(self.key_states.keys()):
                if self.key_states[key]:
                    self.key_states[key] = False
                    self.combo_hits = 0
                    return f"{key}_release"
        return None

    def cleanup(self):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
        pass

if __name__ == "__main__":
    tracker = KeyTracker()
    try:
        print("方向键控制：↑(前进) ↓(后退) ←(左转) →(右转) 松开自动停止 Q(退出)")
        while True:
            event = tracker.get_key_event()

            if event == 'quit':
                break
            elif event == 'up_press':
                forward()
                print(f"\r当前指令: 前进", end='')
            elif event == 'down_press':
                backward()
                print(f"\r当前指令: 后退", end='')
            elif event == 'left_press':
                left(speed=50)
                print(f"\r当前指令: 左转", end='')
            elif event == 'right_press':
                right(speed=50)
                print(f"\r当前指令: 右转", end='')
            elif event and event.endswith('_release'):
                stop()
                print(f"\r当前指令: 停止", end='')
            time.sleep(0.01)

    finally:
        tracker.cleanup()
        stop()
        GPIO.cleanup()
        print()
        print(f"程序安全退出")
