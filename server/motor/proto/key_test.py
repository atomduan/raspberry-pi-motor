#!/usr/bin/python
import evdev
from evdev import ecodes

def detect_key_press():
    # 找到键盘设备
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    print(evdev.list_devices())
    keyboard = None

    for device in devices:
        if 'keyboard' in device.name.lower():
            keyboard = device
            break

    if not keyboard:
        print("未找到键盘设备")
        return

    print(f"监听键盘: {keyboard.name}")

    # 要检测的键码（例如左Ctrl键）
    target_key = ecodes.KEY_LEFTCTRL
    key_state = False

    try:
        for event in keyboard.read_loop():
            if event.type == ecodes.EV_KEY:
                key_event = evdev.categorize(event)
                if key_event.scancode == target_key:
                    key_state = key_event.keystate == 1  # 1表示按下，0表示释放
                    print(f"键状态: {'按下' if key_state else '释放'}")
    except KeyboardInterrupt:
        print("停止监听")

detect_key_press()
