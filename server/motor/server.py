#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
import socket
import threading
import logging
from collections import deque

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CarServer')

# ===== 电机引脚定义 =====
lf_in1, lf_in2, lf_en = 17, 18, 22
rf_in1, rf_in2, rf_en = 23, 24, 25
lb_in1, lb_in2, lb_en = 4, 14, 15
rb_in1, rb_in2, rb_en = 10, 9, 11

# ===== 舵机引脚定义 =====
servo1_pin = 2  # GPIO2 (物理针脚3)
servo2_pin = 3  # GPIO3 (物理针脚5)
servo_center = 7.5  # 舵机中位占空比(1ms-2ms脉宽对应50Hz PWM)

# ===== 闹铃引脚定义 =====
bell_in1, bell_in2 = 7, 8  # 接 L298N 的 IN1 和 IN2

class CarController:
    def __init__(self):
        # 初始化GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # 初始化所有GPIO
        all_pins = [lf_in1, lf_in2, lf_en, rf_in1, rf_in2, rf_en,
                    lb_in1, lb_in2, lb_en, rb_in1, rb_in2, rb_en,
                    servo1_pin, servo2_pin,
                    bell_in1, bell_in2]
        
        for pin in all_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)
        
        # 初始化电机PWM
        pwm_pins = [lf_en, rf_en, lb_en, rb_en]
        self.pwms = [GPIO.PWM(pin, 1000) for pin in pwm_pins]  # 1kHz PWM
        for pwm in self.pwms:
            pwm.start(0)
        
        # 初始化舵机PWM
        self.servo1 = GPIO.PWM(servo1_pin, 50)  # 50Hz
        self.servo2 = GPIO.PWM(servo2_pin, 50)
        self.servo1.start(0)
        self.servo2.start(0)
        
        # 舵机状态
        self.servo1_angle = 135
        self.servo2_angle = 90
        self.last_servo_time = time.time()
        # 使用RLock（可重入锁）代替Lock
        self.servo_lock = threading.RLock()
        
        # 回中舵机
        self.center_servos()
        logger.info("CarController initialized")
    
    def set_motor(self, pwm, in1, in2, speed):
        """设置单个电机速度和方向"""
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
    
    def forward(self, speed=50):
        """前进"""
        self.set_motor(self.pwms[0], lf_in1, lf_in2, speed)
        self.set_motor(self.pwms[1], rf_in1, rf_in2, speed)
        self.set_motor(self.pwms[2], lb_in1, lb_in2, speed)
        self.set_motor(self.pwms[3], rb_in1, rb_in2, speed)
        logger.debug("Moving forward at %d%%", speed)
    
    def backward(self, speed=50):
        """后退"""
        self.set_motor(self.pwms[0], lf_in1, lf_in2, -speed)
        self.set_motor(self.pwms[1], rf_in1, rf_in2, -speed)
        self.set_motor(self.pwms[2], lb_in1, lb_in2, -speed)
        self.set_motor(self.pwms[3], rb_in1, rb_in2, -speed)
        logger.debug("Moving backward at %d%%", speed)
    
    def left(self, speed=50):
        """左转"""
        self.set_motor(self.pwms[0], lf_in1, lf_in2, -speed)
        self.set_motor(self.pwms[1], rf_in1, rf_in2, speed)
        self.set_motor(self.pwms[2], lb_in1, lb_in2, -speed)
        self.set_motor(self.pwms[3], rb_in1, rb_in2, speed)
        logger.debug("Turning left at %d%%", speed)
    
    def right(self, speed=50):
        """右转"""
        self.set_motor(self.pwms[0], lf_in1, lf_in2, speed)
        self.set_motor(self.pwms[1], rf_in1, rf_in2, -speed)
        self.set_motor(self.pwms[2], lb_in1, lb_in2, speed)
        self.set_motor(self.pwms[3], rb_in1, rb_in2, -speed)
        logger.debug("Turning right at %d%%", speed)
    
    def stop(self):
        """停止所有电机"""
        for pwm in self.pwms:
            pwm.ChangeDutyCycle(0)
        logger.debug("All motors stopped")
    
    def bell_on(self):
        """打开闹铃"""
        GPIO.output(bell_in1, GPIO.HIGH)
        GPIO.output(bell_in2, GPIO.LOW)
        logger.debug("Bell ringing")
    
    def bell_off(self):
        """关闭闹铃"""
        GPIO.output(bell_in1, GPIO.LOW)
        GPIO.output(bell_in2, GPIO.LOW)
        logger.debug("Bell stopped")
    
    def set_servo(self, servo, angle):
        """设置舵机角度(0-180度)"""
        logger.debug("Setting servo to %d°", angle)
        
        # 尝试获取锁，设置1秒超时
        if not self.servo_lock.acquire(timeout=1.0):
            logger.error("Failed to acquire servo lock within timeout")
            return False
            
        try:
            logger.debug("Servo lock acquired for set_servo()")
            duty = angle / 18 + 2.5  # 角度转占空比
            servo.ChangeDutyCycle(duty)
            time.sleep(0.1)  # 稳定时间
            servo.ChangeDutyCycle(0)  # 防止抖舵
            self.last_servo_time = time.time()
            return True
        finally:
            self.servo_lock.release()
            logger.debug("Servo lock released from set_servo()")
    
    def center_servos(self):
        """舵机回中"""
        # 尝试获取锁，设置1秒超时
        if not self.servo_lock.acquire(timeout=1.0):
            logger.error("Failed to acquire servo lock within timeout for center_servos")
            return
            
        try:
            logger.debug("Servo lock acquired for center_servos()")
            # 直接调用set_servo，由于使用RLock，嵌套调用不会死锁
            self.set_servo(self.servo1, 135)
            self.set_servo(self.servo2, 90)
            self.servo1_angle = 135
            self.servo2_angle = 90
        finally:
            self.servo_lock.release()
            logger.info("Servos centered (lock released)")
    
    def move_servo_up(self):
        """摄像头向上"""
        # 尝试获取锁，设置1秒超时
        if not self.servo_lock.acquire(timeout=1.0):
            logger.error("Failed to acquire servo lock within timeout for move_servo_up")
            return
            
        try:
            logger.debug("Servo lock acquired for move_servo_up()")
            if time.time() - self.last_servo_time > 0.2:  # 防抖
                angle = self.servo1_angle - 25
                if 90 <= angle <= 180:
                    self.servo1_angle = angle
                    # 由于使用RLock，这里可以安全调用set_servo
                    self.set_servo(self.servo1, self.servo1_angle)
                    logger.info("Servo1 up to %d°", self.servo1_angle)
        finally:
            self.servo_lock.release()
            logger.debug("Servo lock released from move_servo_up()")
    
    def move_servo_down(self):
        """摄像头向下"""
        # 尝试获取锁，设置1秒超时
        if not self.servo_lock.acquire(timeout=1.0):
            logger.error("Failed to acquire servo lock within timeout for move_servo_down")
            return
            
        try:
            logger.debug("Servo lock acquired for move_servo_down()")
            if time.time() - self.last_servo_time > 0.2:  # 防抖
                angle = self.servo1_angle + 25
                if 90 <= angle <= 180:
                    self.servo1_angle = angle
                    # 由于使用RLock，这里可以安全调用set_servo
                    self.set_servo(self.servo1, self.servo1_angle)
                    logger.info("Servo1 down to %d°", self.servo1_angle)
        finally:
            self.servo_lock.release()
            logger.debug("Servo lock released from move_servo_down()")
    
    def move_servo_left(self):
        """摄像头向左"""
        # 尝试获取锁，设置1秒超时
        if not self.servo_lock.acquire(timeout=1.0):
            logger.error("Failed to acquire servo lock within timeout for move_servo_left")
            return
            
        try:
            logger.debug("Servo lock acquired for move_servo_left()")
            if time.time() - self.last_servo_time > 0.2:  # 防抖
                angle = self.servo2_angle + 30
                if 45 <= angle <= 135:
                    self.servo2_angle = angle
                    # 由于使用RLock，这里可以安全调用set_servo
                    self.set_servo(self.servo2, self.servo2_angle)
                    logger.info("Servo2 left to %d°", self.servo2_angle)
        finally:
            self.servo_lock.release()
            logger.debug("Servo lock released from move_servo_left()")
    
    def move_servo_right(self):
        """摄像头向右"""
        # 尝试获取锁，设置1秒超时
        if not self.servo_lock.acquire(timeout=1.0):
            logger.error("Failed to acquire servo lock within timeout for move_servo_right")
            return
            
        try:
            logger.debug("Servo lock acquired for move_servo_right()")
            if time.time() - self.last_servo_time > 0.2:  # 防抖
                angle = self.servo2_angle - 30
                if 45 <= angle <= 135:
                    self.servo2_angle = angle
                    # 由于使用RLock，这里可以安全调用set_servo
                    self.set_servo(self.servo2, self.servo2_angle)
                    logger.info("Servo2 right to %d°", self.servo2_angle)
        finally:
            self.servo_lock.release()
            logger.debug("Servo lock released from move_servo_right()")
    
    def get_status(self):
        """获取当前状态"""
        # 尝试获取锁，设置1秒超时
        if not self.servo_lock.acquire(timeout=1.0):
            logger.error("Failed to acquire servo lock within timeout for get_status")
            return "STATUS:ERROR=LOCK_TIMEOUT"
            
        try:
            logger.debug("Servo lock acquired for get_status()")
            return (
                f"STATUS:MOVE={self.get_current_move()}|"
                f"SERVO1={self.servo1_angle}|SERVO2={self.servo2_angle}|"
                f"BELL={'ON' if GPIO.input(bell_in1) else 'OFF'}"
            )
        finally:
            self.servo_lock.release()
            logger.debug("Servo lock released from get_status()")
    
    def get_current_move(self):
        """获取当前运动状态（简化版）"""
        # 实际应用中应检查GPIO状态
        return "STOPPED"
    
    def cleanup(self):
        """清理资源"""
        self.stop()
        self.bell_off()
        
        # 确保舵机回中，即使锁获取失败也继续
        try:
            if self.servo_lock.acquire(timeout=1.0):
                try:
                    self.center_servos()
                finally:
                    self.servo_lock.release()
        except Exception as e:
            logger.error("Error during servo cleanup: %s", str(e))
        
        GPIO.cleanup()
        logger.info("GPIO cleaned up")

class CarServer:
    def __init__(self, host='0.0.0.0', port=5000, heartbeat_interval=10):
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.controller = CarController()
        self.clients = []
        self.client_lock = threading.Lock()
        self.running = False
        self.heartbeat_thread = None
        logger.info("CarServer initialized on %s:%d", host, port)
    
    def start(self):
        """启动服务器"""
        self.running = True
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        # 创建TCP服务器
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            logger.info("Server started, listening on %s:%d", self.host, self.port)
            
            while self.running:
                try:
                    # 等待客户端连接
                    client_socket, addr = self.server_socket.accept()
                    logger.info("New client connected: %s", addr)
                    
                    # 添加客户端到列表
                    with self.client_lock:
                        # 断开之前的连接（只允许一个客户端）
                        for c in self.clients:
                            try:
                                c.close()
                            except:
                                pass
                        self.clients = [client_socket]
                    
                    # 启动客户端处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    logger.error("Error accepting connection: %s", str(e))
                    time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Server shutting down (keyboard interrupt)")
        finally:
            self.stop()
    
    def stop(self):
        """停止服务器"""
        self.running = False
        
        # 关闭所有客户端连接
        with self.client_lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients = []
        
        # 关闭服务器套接字
        try:
            self.server_socket.close()
        except:
            pass
        
        # 清理硬件
        self.controller.cleanup()
        logger.info("Server stopped")
    
    def _heartbeat_loop(self):
        """发送心跳包的循环"""
        while self.running:
            time.sleep(self.heartbeat_interval)
            with self.client_lock:
                for client in self.clients[:]:
                    try:
                        client.sendall(b"HEARTBEAT\n")
                        logger.debug("Sent heartbeat to client")
                    except:
                        # 客户端断开
                        try:
                            client.close()
                        except:
                            pass
                        self.clients.remove(client)
                        logger.info("Client disconnected (heartbeat)")
    
    def _handle_client(self, client_socket, addr):
        """处理客户端连接"""
        try:
            while self.running:
                # 接收数据
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                except ConnectionResetError:
                    logger.warning("Client %s disconnected abruptly", addr)
                    break
                
                # 处理接收到的命令
                commands = data.decode().strip().split('\n')
                for cmd in commands:
                    if not cmd:
                        continue
                    self._process_command(cmd, client_socket)
        
        except Exception as e:
            logger.error("Client %s error: %s", addr, str(e))
        finally:
            # 清理客户端连接
            try:
                client_socket.close()
            except:
                pass
            with self.client_lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            logger.info("Client %s disconnected", addr)
    
    def _process_command(self, cmd, client_socket):
        """处理单个命令"""
        logger.debug("Received command: %s", cmd)
        
        try:
            if cmd.startswith("MOVE:"):
                direction = cmd.split(":")[1].upper()
                if direction == "FORWARD":
                    self.controller.forward()
                elif direction == "BACKWARD":
                    self.controller.backward()
                elif direction == "LEFT":
                    self.controller.left()
                elif direction == "RIGHT":
                    self.controller.right()
            
            elif cmd == "STOP":
                self.controller.stop()
            
            elif cmd.startswith("SERVO:"):
                action = cmd.split(":")[1].upper()
                if action == "UP":
                    self.controller.move_servo_up()
                elif action == "DOWN":
                    self.controller.move_servo_down()
                elif action == "LEFT":
                    self.controller.move_servo_left()
                elif action == "RIGHT":
                    self.controller.move_servo_right()
                elif action == "CENTER":
                    self.controller.center_servos()
            
            elif cmd.startswith("BELL:"):
                state = cmd.split(":")[1].upper()
                if state == "ON":
                    self.controller.bell_on()
                elif state == "OFF":
                    self.controller.bell_off()
            
            elif cmd == "STATUS:REQUEST":
                status = self.controller.get_status()
                try:
                    client_socket.sendall((status + "\n").encode())
                    logger.debug("Sent status response: %s", status)
                except Exception as e:
                    logger.error("Failed to send status response: %s", str(e))
            
            elif cmd == "HEARTBEAT":
                # 客户端的心跳，不需要响应
                logger.debug("Received heartbeat from client")
            
            else:
                logger.warning("Unknown command: %s", cmd)
        
        except Exception as e:
            logger.error("Error processing command '%s': %s", cmd, str(e))

if __name__ == "__main__":
    server = CarServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        logger.exception("Unexpected error")
        server.stop()
