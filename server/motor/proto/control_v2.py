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

# ===== 电机引脚定义 =====
lf_in1, lf_in2, lf_en = 17, 18, 22
rf_in1, rf_in2, rf_en = 23, 24, 25
lb_in1, lb_in2, lb_en = 4, 14, 15
rb_in1, rb_in2, rb_en = 10, 9, 11

# ===== 舵机引脚定义 =====
servo1_pin = 2  # GPIO2 (物理针脚3)
servo2_pin = 3  # GPIO3 (物理针脚5)
servo_center = 7.5  # 舵机中位占空比(1ms-2ms脉宽对应50Hz PWM)

# 初始化所有GPIO
all_pins = [lf_in1, lf_in2, lf_en, rf_in1, rf_in2, rf_en,
            lb_in1, lb_in2, lb_en, rb_in1, rb_in2, rb_en,
            servo1_pin, servo2_pin]  # 添加舵机引脚

for pin in all_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, False)

# 初始化电机PWM
pwm_pins = [lf_en, rf_en, lb_en, rb_en]
pwms = [GPIO.PWM(pin, 1000) for pin in pwm_pins]  # 电机PWM频率1kHz
for pwm in pwms:
    pwm.start(0)

# 初始化舵机PWM
servo1 = GPIO.PWM(servo1_pin, 50)  # 舵机1，50Hz标准频率
servo2 = GPIO.PWM(servo2_pin, 50)  # 舵机2
servo1.start(0)
servo2.start(0)

# ===== 电机控制函数 =====
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

# ===== 舵机控制函数 =====
def set_servo(servo, angle, tracker):
    """设置舵机角度(0-180度)"""
    duty = angle / 18 + 2.5  # 角度转占空比(0°=2.5%, 180°=12.5%)
    servo.ChangeDutyCycle(duty)
    time.sleep(0.1)  # 稳定时间
    servo.ChangeDutyCycle(0)  # 防止抖舵
    time.sleep(0.1)  # 稳定时间
    if tracker:
        tracker.last_ang_time = time.time()

def center_servos(tracker=None):
    """舵机回中"""
    set_servo(servo1, 135, tracker)
    set_servo(servo2, 90, tracker)
    print("\r舵机已回中", end='')

def center_ang_servos(tracker=None, anglthed=0.2):
    delt = time.time() - tracker.last_ang_time
    if delt > anglthed:  
        center_servos(tracker)
        tracker.servo1_angle = 135 
        tracker.servo2_angle = 90 

def up_ang_servos(tracker, anglthed=0.2):
    delt = time.time() - tracker.last_ang_time
    if delt > anglthed:  
        angle = tracker.servo1_angle - 25 
        if angle >= 90:
            tracker.servo1_angle = angle
            set_servo(servo1, tracker.servo1_angle, tracker)

def down_ang_servos(tracker, anglthed=0.2):
    delt = time.time() - tracker.last_ang_time
    if delt > anglthed:  
        angle = tracker.servo1_angle + 25 
        if angle <= 180:
            tracker.servo1_angle = angle
            set_servo(servo1, tracker.servo1_angle, tracker)

def left_ang_servos(tracker, anglthed=0.2):
    delt = time.time() - tracker.last_ang_time
    if delt > anglthed:  
        angle = tracker.servo2_angle + 30 
        if angle <= 135:
            tracker.servo2_angle = angle
            set_servo(servo2, tracker.servo2_angle, tracker)

def right_ang_servos(tracker, anglthed=0.2):
    delt = time.time() - tracker.last_ang_time
    if delt > anglthed:  
        angle = tracker.servo2_angle - 30 
        if angle >= 45:
            tracker.servo2_angle = angle
            set_servo(servo2, tracker.servo2_angle, tracker)

# ===== 键盘控制类 =====
class KeyTracker:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        self.key_states = {
            'forward_move': False,
            'backward_move': False,
            'left_turn': False,
            'right_turn': False,
        }
        self.servo1_angle = 135 
        self.servo2_angle = 90 
        self.last_key_time = time.time()
        self.last_ang_time = time.time()
        self.combo_hits = 0

    def get_key_event(self):
        """检测按键按下/抬起事件"""
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            if ch.lower() in ['w', 's', 'a', 'd']:
                self.last_key_time = time.time()
                self.combo_hits += 1
                return self._handle_arrow_key(ch)
            elif ch.lower() in ['h', 'j', 'k', 'l']:
                self.last_key_time = time.time()
                self.combo_hits += 1
                return self._handle_cam_key(ch)
                return ch.lower()
            elif ch.lower() == 'q':
                return 'quit'
            elif ch.lower() == 'c':
                return 'center_ang'
            return None
        else:
            return self._check_key_release()

    def _handle_arrow_key(self, ch):
        if ch == 'w':
            self.key_states['forward_move'] = True
            return 'forward_move'
        elif ch == 's':
            self.key_states['backward_move'] = True
            return 'backward_move'
        elif ch == 'a':
            self.key_states['left_turn'] = True
            return 'left_turn'
        elif ch == 'd':
            self.key_states['right_turn'] = True
            return 'right_turn'
        return None

    def _handle_cam_key(self, ch):
        if ch == 'k':
            self.key_states['up_ang'] = True
            return 'up_ang'
        elif ch == 'j':
            self.key_states['down_ang'] = True
            return 'down_ang'
        elif ch == 'h':
            self.key_states['left_ang'] = True
            return 'left_ang'
        elif ch == 'l':
            self.key_states['right_ang'] = True
            return 'right_ang'
        return None

    def _check_key_release(self):
        """检查是否有按键抬起"""
        now = time.time()
        key_released = False
        if self.combo_hits > 0:
            if self.combo_hits == 1:
                if now - self.last_key_time > 0.5:
                    key_released = True
            else:
                if now - self.last_key_time > 0.1:
                    key_released = True
        if key_released:
            self.last_key_time = now
            for key in list(self.key_states.keys()):
                if self.key_states[key]:
                    self.key_states[key] = False
                    self.combo_hits = 0
                    return f"{key}_release"
        return None

    def cleanup(self):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def print_info(self, action):
        print(f"\r当前操作: {action} | 舵机1: {self.servo1_angle}° 舵机2: {self.servo2_angle}°", end='')

if __name__ == "__main__":
    tracker = KeyTracker()
    center_servos()  # 初始化舵机位置

    try:
        print("控制说明:")
        print("方向键: 移动小车 | WASD: 控制舵机 | C: 舵机回中 | Q: 退出")

        while True:
            event = tracker.get_key_event()

            if event == 'quit':
                break

            # 小车运动控制
            elif event == 'forward_move':
                forward()
                tracker.print_info('前进')
            elif event == 'backward_move':
                backward()
                tracker.print_info('后退')
            elif event == 'left_turn':
                left()
                tracker.print_info('左转')
            elif event == 'right_turn':
                right()
                tracker.print_info('右转')

            # 舵机控制
            elif event == 'up_ang':
                up_ang_servos(tracker)
                tracker.print_info('上看')
            elif event == 'down_ang':
                down_ang_servos(tracker)
                tracker.print_info('下看')
            elif event == 'left_ang':
                left_ang_servos(tracker)
                tracker.print_info('左看')
            elif event == 'right_ang':
                right_ang_servos(tracker)
                tracker.print_info('右看')
            elif event == 'center_ang':
                center_ang_servos(tracker)
                tracker.print_info('回中')

            # 停止检测
            elif event and event.endswith('_release'):
                stop()
                tracker.print_info('停止')

            time.sleep(0.01)

    finally:
        tracker.cleanup()
        stop()
        center_servos()
        GPIO.cleanup()
        print("\n程序安全退出")
