# raspberry-pi-motor
# Raspberry Pi 电机控制与视频流项目

## 项目简介
该项目基于树莓派实现了电机控制、游戏手柄输入、摄像头视频推流及客户端远程控制等功能，适用于移动机器人、智能小车等场景。

## 功能特点
- 电机控制：支持前进、后退、左转、右转及停止操作，通过PWM实现速度调节
- 输入设备支持：兼容游戏手柄/控制器（通过`inputs`和`pygame`库），可检测按键、摇杆事件
- 摄像头推流：支持RTMP、SRT、UDP等多种协议的视频流推送，可配置分辨率、帧率和比特率
- 远程控制：客户端-服务器架构，支持通过网络发送控制命令（移动、舵机控制、鸣铃等）

## 依赖安装
1. 安装Python依赖：
```bash
pip install -r requirements.txt
```
2. 安装额外工具（视频推流所需）：
```bash
sudo apt install ffmpeg
```
3. 手柄支持可能需要额外库：
```bash
pip install pygame
```

## 使用方法

### 1. 电机控制测试
```bash
# 基础电机测试
python server/motor/proto/motor_test.py

# 键盘控制电机
python server/motor/proto/control.py
```

### 2. 手柄测试
```bash
# 使用inputs库测试手柄
python test_controller.py

# 使用pygame测试手柄
python test_pygame.py
```

### 3. 摄像头推流
```bash
# RTMP推流
bash server/cam_stream.sh

# SRT推流
bash server/cam_stream_srt.sh

# UDP原始流推送
bash server/cam_stream_raw.sh
```
> 注意：推流前需在对应脚本中修改目标IP和端口

### 4. 远程控制
1. 启动服务器（需自行补充完整服务器启动命令）
2. 运行客户端：
```bash
python client.py --host <服务器IP> --port <端口>
```

## 核心文件说明
- `server/motor/proto/`：电机控制核心代码，包含电机驱动、按键跟踪等功能
- `test_controller.py`/`test_pygame.py`/`joystick.py`：手柄输入检测相关代码
- `server/cam_stream*.sh`：摄像头推流脚本，支持多种协议
- `client.py`：远程控制客户端，用于发送控制命令
- `requirements.txt`：项目依赖清单

## 控制说明
- 电机控制：支持方向键（↑前进、↓后退、←左转、→右转）或WASD按键
- 手柄控制：通过摇杆和按键实现电机控制（具体映射见代码）
- 摄像头控制：通过HJKL键调节摄像头角度，C键回中
- 鸣铃控制：B键触发鸣铃

## 注意事项
- 电机控制需正确连接GPIO引脚，参考代码中的引脚定义
- 推流参数（分辨率、帧率等）可根据网络情况调整
- 程序运行时需注意权限问题，可能需要`sudo`权限访问GPIO和部分设备
