# !/usr/bin/python3
import pygame
import sys


def main():
    # 初始化pygame
    pygame.init()
    pygame.joystick.init()

    # 检查手柄数量
    joystick_count = pygame.joystick.get_count()
    if joystick_count == 0:
        print("未找到游戏手柄")
        return

    print(f"找到 {joystick_count} 个游戏手柄")

    # 初始化第一个手柄
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    print(f"手柄名称: {joystick.get_name()}")
    print(f"轴数: {joystick.get_numaxes()}")
    print(f"按钮数: {joystick.get_numbuttons()}")
    print(f"方向键数: {joystick.get_numhats()}")

    print("\n开始监听输入 (按Ctrl+C退出)...")

    try:
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

                # 按钮事件
                elif event.type == pygame.JOYBUTTONDOWN:
                    print(f"按钮 {event.button} 按下")
                elif event.type == pygame.JOYBUTTONUP:
                    print(f"按钮 {event.button} 释放")

                # 轴事件（摇杆）
                elif event.type == pygame.JOYAXISMOTION:
                    print(f"轴 {event.axis}: {event.value:.3f}")

                # 方向键事件
                elif event.type == pygame.JOYHATMOTION:
                    print(f"方向键 {event.hat}: {event.value}")

            clock.tick(60)  # 60 FPS

    except KeyboardInterrupt:
        print("\n程序结束")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()