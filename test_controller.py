#!/usr/bin/python3
import inputs


def test():
    print("正在查找输入设备...")

    # 获取所有游戏控制器
    devices = inputs.devices.gamepads
    if not devices:
        print("未找到游戏控制器")
        return

    print(f"找到 {len(devices)} 个游戏控制器:")
    for i, device in enumerate(devices):
        print(f"  {i + 1}. {device.name}")

    print("\n开始监听输入 (按Ctrl+C退出)...")

    try:
        while True:
            events = inputs.get_gamepad()
            for event in events:
                print(f"{event.ev_type} - {event.code} = {event.state}")
    except KeyboardInterrupt:
        print("\n程序结束")


if __name__ == "__main__":
    test()