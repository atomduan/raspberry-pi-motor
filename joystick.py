#!/usr/bin/env python3
import pygame
import time
import logging
import socket
import sys

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PygameController')


class PygameController:
    def __init__(self):
        # 初始化Pygame
        pygame.init()
        pygame.joystick.init()

        self.joystick = None
        self.connected = False
        self.left_stick_x = 0
        self.left_stick_y = 0
        self.right_stick_x = 0
        self.right_stick_y = 0
        self.buttons = {
            'b': False,
            'a': False,
            'x': False,
            'y': False,
            'plus': False,
            'minus': False,
            'l': False,
            'r': False,
            'zl': False,
            'zr': False,
            'left_stick_press': False,
            'right_stick_press': False,
            'dpad_up': False,
            'dpad_down': False,
            'dpad_left': False,
            'dpad_right': False
        }
        self.last_event_time = time.time()
        self.stick_deadzone = 0.1  # 摇杆死区
        self.clock = pygame.time.Clock()

        logger.info("PygameController初始化完成")

    def find_switch_controller(self):
        """查找Switch手柄设备"""
        logger.info("正在查找手柄...")

        joystick_count = pygame.joystick.get_count()
        if joystick_count == 0:
            logger.error("未找到任何游戏手柄")
            return False

        # 检查每个手柄
        for i in range(joystick_count):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            name = joystick.get_name().lower()

            # 常见的Switch手柄名称模式
            switch_patterns = [
                'pro controller',
                'nintendo switch',
                'joy-con',
                'switch left',
                'switch right'
            ]

            if any(pattern in name for pattern in switch_patterns):
                self.joystick = joystick
                self.connected = True
                logger.info(f"找到Switch手柄: {joystick.get_name()}")
                logger.info(f"轴数: {joystick.get_numaxes()}")
                logger.info(f"按钮数: {joystick.get_numbuttons()}")
                logger.info(f"方向键数: {joystick.get_numhats()}")
                return True
            else:
                # 不是Switch手柄，释放它
                joystick.quit()

        # 如果没有找到Switch手柄，使用第一个手柄
        if not self.connected and joystick_count > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.connected = True
            logger.info(f"使用默认手柄: {self.joystick.get_name()}")
            return True

        return False

    def connect(self):
        """连接手柄"""
        if self.connected:
            return True

        if self.find_switch_controller():
            logger.info("成功连接到手柄")
            return True
        return False

    def disconnect(self):
        """断开连接"""
        if self.joystick and self.connected:
            self.joystick.quit()
        self.connected = False
        logger.info("已断开手柄连接")

    def read_events(self):
        """读取手柄事件"""
        if not self.connected or not self.joystick:
            return False

        try:
            # 处理Pygame事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                elif event.type == pygame.JOYAXISMOTION:
                    self._process_axis_motion(event)
                elif event.type == pygame.JOYBUTTONDOWN:
                    self._process_button_down(event)
                elif event.type == pygame.JOYBUTTONUP:
                    self._process_button_up(event)
                elif event.type == pygame.JOYHATMOTION:
                    self._process_hat_motion(event)

            # 直接读取当前状态（用于连续输入）
            self._update_stick_positions()
            self._update_button_states()

            self.last_event_time = time.time()
            return True

        except Exception as e:
            logger.error(f"读取手柄事件失败: {str(e)}")
            self.connected = False
            return False

    def _update_stick_positions(self):
        """更新摇杆位置（直接读取）"""
        if not self.joystick:
            return

        # 左摇杆 (轴0=X, 轴1=Y)
        if self.joystick.get_numaxes() >= 2:
            self.left_stick_x = self._apply_deadzone(self.joystick.get_axis(0))
            # Y轴方向相反
            self.left_stick_y = self._apply_deadzone(-self.joystick.get_axis(1))

        # 右摇杆 (轴2=X, 轴3=Y) - Switch Pro Controller
        if self.joystick.get_numaxes() >= 4:
            self.right_stick_x = self._apply_deadzone(self.joystick.get_axis(2))
            # Y轴方向相反
            self.right_stick_y = self._apply_deadzone(-self.joystick.get_axis(3))

    def _update_button_states(self):
        """更新按钮状态（直接读取）"""
        if not self.joystick:
            return

        num_buttons = self.joystick.get_numbuttons()

        # 根据常见Switch手柄的按钮映射
        # 注意：不同手柄的按钮编号可能不同
        if num_buttons >= 1:
            # B键 (通常为按钮1)
            if num_buttons > 1:  # 确保有足够按钮
                self.buttons['b'] = self.joystick.get_button(1)

        if num_buttons >= 4:
            # A, X, Y键
            self.buttons['a'] = self.joystick.get_button(0)  # A键
            self.buttons['x'] = self.joystick.get_button(2)  # X键
            self.buttons['y'] = self.joystick.get_button(3)  # Y键

        if num_buttons >= 6:
            # L, R键
            self.buttons['l'] = self.joystick.get_button(4)  # L键
            self.buttons['r'] = self.joystick.get_button(5)  # R键

        if num_buttons >= 8:
            # ZL, ZR键
            self.buttons['zl'] = self.joystick.get_button(6)  # ZL键
            self.buttons['zr'] = self.joystick.get_button(7)  # ZR键

        # + 和 - 键 (通常为按钮9和8)
        if num_buttons >= 10:
            self.buttons['plus'] = self.joystick.get_button(9)  # +键
            self.buttons['minus'] = self.joystick.get_button(8)  # -键

        # 摇杆按下
        if num_buttons >= 11:
            self.buttons['left_stick_press'] = self.joystick.get_button(10)  # 左摇杆按下
        if num_buttons >= 12:
            self.buttons['right_stick_press'] = self.joystick.get_button(11)  # 右摇杆按下

    def _process_axis_motion(self, event):
        """处理摇杆移动事件"""
        if event.axis == 0:  # 左摇杆X轴
            self.left_stick_x = self._apply_deadzone(event.value)
            logger.debug(f"左摇杆X: {event.value:.3f} -> {self.left_stick_x:.3f}")
        elif event.axis == 1:  # 左摇杆Y轴
            self.left_stick_y = self._apply_deadzone(-event.value)  # Y轴方向相反
            logger.debug(f"左摇杆Y: {event.value:.3f} -> {self.left_stick_y:.3f}")
        elif event.axis == 2:  # 右摇杆X轴
            self.right_stick_x = self._apply_deadzone(event.value)
            logger.debug(f"右摇杆X: {event.value:.3f} -> {self.right_stick_x:.3f}")
        elif event.axis == 3:  # 右摇杆Y轴
            self.right_stick_y = self._apply_deadzone(-event.value)  # Y轴方向相反
            logger.debug(f"右摇杆Y: {event.value:.3f} -> {self.right_stick_y:.3f}")

    def _process_button_down(self, event):
        """处理按键按下事件"""
        button = event.button

        # 根据按钮编号设置状态
        if button == 1:  # B键
            self.buttons['b'] = True
            logger.info("B键 按下")
        elif button == 0:  # A键
            self.buttons['a'] = True
            logger.info("A键 按下")
        elif button == 2:  # X键
            self.buttons['x'] = True
            logger.info("X键 按下")
        elif button == 3:  # Y键
            self.buttons['y'] = True
            logger.info("Y键 按下")
        elif button == 4:  # L键
            self.buttons['l'] = True
            logger.info("L键 按下")
        elif button == 5:  # R键
            self.buttons['r'] = True
            logger.info("R键 按下")
        elif button == 6:  # ZL键
            self.buttons['zl'] = True
            logger.info("ZL键 按下")
        elif button == 7:  # ZR键
            self.buttons['zr'] = True
            logger.info("ZR键 按下")
        elif button == 8:  # -键
            self.buttons['minus'] = True
            logger.info("-键 按下")
        elif button == 9:  # +键
            self.buttons['plus'] = True
            logger.info("+键 按下")
        elif button == 10:  # 左摇杆按下
            self.buttons['left_stick_press'] = True
            logger.info("左摇杆按下 按下")
        elif button == 11:  # 右摇杆按下
            self.buttons['right_stick_press'] = True
            logger.info("右摇杆按下 按下")

    def _process_button_up(self, event):
        """处理按键释放事件"""
        button = event.button

        if button == 1:  # B键
            self.buttons['b'] = False
            logger.info("B键 释放")
        elif button == 0:  # A键
            self.buttons['a'] = False
            logger.info("A键 释放")
        elif button == 2:  # X键
            self.buttons['x'] = False
            logger.info("X键 释放")
        elif button == 3:  # Y键
            self.buttons['y'] = False
            logger.info("Y键 释放")
        elif button == 4:  # L键
            self.buttons['l'] = False
            logger.info("L键 释放")
        elif button == 5:  # R键
            self.buttons['r'] = False
            logger.info("R键 释放")
        elif button == 6:  # ZL键
            self.buttons['zl'] = False
            logger.info("ZL键 释放")
        elif button == 7:  # ZR键
            self.buttons['zr'] = False
            logger.info("ZR键 释放")
        elif button == 8:  # -键
            self.buttons['minus'] = False
            logger.info("-键 释放")
        elif button == 9:  # +键
            self.buttons['plus'] = False
            logger.info("+键 释放")
        elif button == 10:  # 左摇杆按下
            self.buttons['left_stick_press'] = False
            logger.info("左摇杆按下 释放")
        elif button == 11:  # 右摇杆按下
            self.buttons['right_stick_press'] = False
            logger.info("右摇杆按下 释放")

    def _process_hat_motion(self, event):
        """处理方向键事件"""
        hat = event.value

        # 更新dpad状态
        self.buttons['dpad_left'] = (hat[0] < 0)
        self.buttons['dpad_right'] = (hat[0] > 0)
        self.buttons['dpad_up'] = (hat[1] > 0)
        self.buttons['dpad_down'] = (hat[1] < 0)

        # 记录方向键状态变化
        if hat[0] < 0:
            logger.info("D-pad 左")
        elif hat[0] > 0:
            logger.info("D-pad 右")
        if hat[1] > 0:
            logger.info("D-pad 上")
        elif hat[1] < 0:
            logger.info("D-pad 下")

    def _apply_deadzone(self, value):
        """应用摇杆死区"""
        if abs(value) < self.stick_deadzone:
            return 0.0
        return value

    def get_movement_command(self):
        """根据左摇杆获取移动命令"""
        if abs(self.left_stick_x) < 0.1 and abs(self.left_stick_y) < 0.1:
            return "STOP"

        # 计算速度（0-100）
        speed = int(min(max(abs(self.left_stick_x), abs(self.left_stick_y)) * 100, 100))
        if abs(self.left_stick_y) > abs(self.left_stick_x):
            # 主要Y轴控制（前进/后退）
            if self.left_stick_y > 0:
                return f"MOVE:FORWARD:{speed}"
            else:
                return f"MOVE:BACKWARD:{speed}"
        else:
            print(self.left_stick_x, self.left_stick_y)
            # 主要X轴控制（转向）
            if self.left_stick_x > 0:
                return f"MOVE:RIGHT:{speed}"
            else:
                return f"MOVE:LEFT:{speed}"

    def get_camera_command(self):
        """根据右摇杆获取摄像头命令"""
        commands = []

        # 摄像头上下
        if self.right_stick_y > 0.5:
            commands.append("SERVO:UP")
        elif self.right_stick_y < -0.5:
            commands.append("SERVO:DOWN")

        # 摄像头左右
        if self.right_stick_x > 0.5:
            commands.append("SERVO:RIGHT")
        elif self.right_stick_x < -0.5:
            commands.append("SERVO:LEFT")

        if not commands:
            return None

        return ";".join(commands)  # 支持同时上下左右移动

    def get_bell_command(self):
        """根据B键获取铃音命令"""
        if self.buttons['b']:
            return "BELL:ON"
        else:
            return "BELL:OFF"

    def print_status(self):
        """打印当前状态"""
        print(f"\r左摇杆: X={self.left_stick_x:+.3f} Y={self.left_stick_y:+.3f} | "
              f"右摇杆: X={self.right_stick_x:+.3f} Y={self.right_stick_y:+.3f} | "
              f"B键: {'按下' if self.buttons['b'] else '释放'}", end='', flush=True)


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
    """主函数"""
    controller = PygameController()

    # 创建TCP连接
    sock = None
    connected_to_server = False

    try:
        # 连接手柄
        if not controller.connect():
            logger.error("无法连接手柄，请检查蓝牙连接")
            return

        # 连接服务器
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((server_host, server_port))
            connected_to_server = True
            logger.info(f"成功连接到小车服务端 {server_host}:{server_port}")
        except Exception as e:
            logger.warning(f"无法连接到小车服务端: {str(e)}")
            logger.info("将以离线模式运行，仅显示手柄输入")

        print("\nSwitch手柄测试程序 (Pygame版本)")
        print("功能映射:")
        print("  - 左摇杆: 小车移动")
        print("  - 右摇杆: 摄像头方向")
        print("  - B键: 铃音控制")
        print("  - Ctrl+C: 退出")
        print("\n正在读取手柄输入...\n")

        last_print_time = time.time()

        while True:
            # 读取手柄事件
            if not controller.read_events():
                logger.warning("手柄连接中断，尝试重新连接...")
                time.sleep(1)
                controller.disconnect()
                if not controller.connect():
                    continue

            # 打印状态（每秒一次）
            current_time = time.time()
            if current_time - last_print_time > 0.1:  # 每100ms更新一次
                controller.print_status()
                last_print_time = current_time

            # 获取控制命令
            move_cmd = controller.get_movement_command()
            cam_cmd = controller.get_camera_command()
            bell_cmd = controller.get_bell_command()

            # 发送命令到小车服务端
            if connected_to_server:
                if move_cmd:
                    send_command(sock, move_cmd)

                if cam_cmd:
                    send_command(sock, cam_cmd)

                if bell_cmd:
                    send_command(sock, bell_cmd)
            else:
                # 离线模式，仅显示
                if move_cmd:
                    logger.debug(f"移动命令: {move_cmd}")
                if cam_cmd:
                    logger.debug(f"摄像头命令: {cam_cmd}")
                if bell_cmd:
                    logger.debug(f"铃音命令: {bell_cmd}")

            # 限制帧率
            controller.clock.tick(60)

    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.exception(f"程序异常: {str(e)}")
    finally:
        controller.disconnect()
        if sock:
            sock.close()
        pygame.quit()
        print("\n程序结束")


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