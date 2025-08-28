#!/usr/bin/env python3
import sys
import select
import termios
import tty
import socket
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CarClient')

class KeyTracker:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        self.key_states = {
            'w_move': False,
            's_move': False,
            'a_move': False,
            'd_move': False,
            'bell_ring': False,
        }
        self.last_key_time = time.time()
        self.combo_hits = 0
        self.servo1_angle = 135
        self.servo2_angle = 90
        logger.info("KeyTracker initialized")

    def get_key_event(self):
        """检测按键按下/抬起事件"""
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            if ch.lower() in ['w', 's', 'a', 'd']:
                key = f"{ch.lower()}_move"
                self.last_key_time = time.time()
                # 仅当按键状态改变时增加combo_hits
                if not self.key_states.get(key, False):
                    self.key_states[key] = True
                    self.combo_hits += 1
                    return key
            elif ch.lower() in ['h', 'j', 'k', 'l']:
                # HJKL是瞬时动作，不增加combo_hits
                return f"{ch.lower()}_ang"
            elif ch.lower() == 'b':
                self.last_key_time = time.time()
                # 仅当按键状态改变时增加combo_hits
                if not self.key_states.get('bell_ring', False):
                    self.key_states['bell_ring'] = True
                    self.combo_hits += 1
                    return 'bell_ring'
            elif ch.lower() == 'q':
                return 'quit'
            elif ch.lower() == 'c':
                return 'center_ang'
            elif ch.lower() == 'i':
                return 'status_request'
            return None
        else:
            return self._check_key_release()

    def _check_key_release(self):
        """检查是否有按键抬起"""
        now = time.time()
        key_released = False
        if self.combo_hits > 0:
            # 单键按下时使用较长的超时
            if self.combo_hits == 1:
                if now - self.last_key_time > 0.5:
                    key_released = True
            # 多键按下时使用较短的超时
            else:
                if now - self.last_key_time > 0.1:
                    key_released = True

        if key_released:
            self.last_key_time = now
            released_keys = []

            # 检查方向键是否释放
            move_keys = ['w_move', 's_move', 'a_move', 'd_move']
            any_move_pressed = False
            for key in move_keys:
                if self.key_states.get(key, False):
                    self.key_states[key] = False
                    released_keys.append(key)
                    any_move_pressed = True

            # 检查鸣铃键是否释放
            bell_pressed = self.key_states.get('bell_ring', False)
            if bell_pressed:
                self.key_states['bell_ring'] = False
                released_keys.append('bell_ring')

            self.combo_hits = 0

            # 如果有方向键释放，需要检查是否还有方向键按下
            if any_move_pressed:
                # 检查是否还有方向键按下
                still_pressed = False
                for key in move_keys:
                    if self.key_states.get(key, False):
                        still_pressed = True
                        break

                # 如果没有方向键按下，返回STOP
                if not still_pressed:
                    return 'stop'

            # 如果鸣铃键释放
            if bell_pressed:
                return 'bell_off'

        return None

    def cleanup(self):
        """恢复终端设置"""
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
        logger.info("Terminal settings restored")

def send_command(sock, command):
    """发送命令到服务器"""
    try:
        sock.sendall((command + "\n").encode())
        logger.debug("Sent command: %s", command)
        return True
    except Exception as e:
        logger.error("Failed to send command: %s", str(e))
        return False

def main(server_host='localhost', server_port=5000):
    # 连接到服务器
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((server_host, server_port))
        logger.info("Connected to server at %s:%d", server_host, server_port)
    except Exception as e:
        logger.error("Failed to connect to server: %s", str(e))
        return

    tracker = KeyTracker()

    try:
        print("\n===== 小车控制客户端 =====")
        print("方向键 (WASD): 移动小车")
        print("HJKL: 控制摄像头方向 | B: 鸣铃 | C: 舵机回中")
        print("I: 查看状态 | Q: 退出")
        print("连接已建立，开始控制...\n")

        while True:
            # 发送心跳
            if time.time() % 5 < 0.1:  # 每5秒
                send_command(sock, "HEARTBEAT")

            # 处理按键
            event = tracker.get_key_event()
            if event == "quit":
                break
            elif event:
                # 转换事件为命令
                if event.endswith('_move'):
                    direction = event[0].upper()
                    cmd = f"MOVE:{'FORWARD' if direction == 'W' else 'BACKWARD' if direction == 'S' else 'LEFT' if direction == 'A' else 'RIGHT'}"
                    send_command(sock, cmd)
                elif event.endswith('_ang'):
                    action = event[0].upper()
                    print(action)
                    cmd = f"SERVO:{'LEFT' if action == 'H' else 'DOWN' if action == 'J' else 'UP' if action == 'K' else 'RIGHT'}"
                    send_command(sock, cmd)
                    print('llllllllllllllllllllll')
                elif event == "bell_ring":
                    send_command(sock, "BELL:ON")
                elif event == "bell_off":
                    send_command(sock, "BELL:OFF")
                elif event == "center_ang":
                    send_command(sock, "SERVO:CENTER")
                elif event == "stop":
                    send_command(sock, "STOP")
                elif event == "status_request":
                    send_command(sock, "STATUS:REQUEST")

            # 处理状态响应
            if select.select([sock], [], [], 0)[0]:
                try:
                    data = sock.recv(1024).decode().strip()
                    if data:
                        if data.startswith("STATUS:"):
                            print(f"\r{data} | 按I查看状态        ", end='')
                        else:
                            print(f"\r服务器响应: {data}        ", end='')
                except:
                    logger.error("Error receiving data from server")
                    break

            time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt, exiting")
    finally:
        tracker.cleanup()
        sock.close()
        print("\n客户端已退出")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = '192.168.102.22'

    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 5000

    main(host, port)
