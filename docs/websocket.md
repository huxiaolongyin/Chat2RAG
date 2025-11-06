# Websocket 协议
## 版本：v0.0.1

## 建立连接
### 客户端发送内容
headers:
```
Authorization: Bearer <access_token>
```

content:
```json
{
    "type": "init",
    "device": {
        "vin": "vin0",              // string: 设备识别码
    },
    "input_audio": {
        "format": "opus",           // string: 输入的音频格式(opus、wav、pcm)
        "sample_rate": 16000,       // number: 输入的采样率
        "channels": 1,              // number: 输入的声道数
        "frame_duration": 60,       // number: 输入的帧长
    },
    "output_audio": {
        "format": "opus",           // string: 输出的音频格式(opus、wav、pcm)
        "sample_rate": 24000,       // number: 输出的采样率
        "channels": 1,              // number: 输出的声道数
        "frame_duration": 60,       // number: 输出的帧长
        "voice_type": "voice0",     // string: 输出的音色
        "speed": 1.3,               // number: 输出的语速
        "silence_duration": 1000,   // number: 句尾输出的静音时长(ms)
    }
}
```

### 服务端响应
```json
{
    "type": "init",
    "output_audio": {
        "format": "opus",           // string: 输出的音频格式(opus、wav、pcm)
        "sample_rate": 24000,       // number: 输出的采样率
        "channels": 1,              // number: 输出的声道数
        "frame_duration": 60,       // number: 输出的帧长
        "voice_type": "voice0",     // string: 输出的音色
        "speed": 1.3,               // number: 输出的语速
    }
}
```

## 数据传输
### 客户端发送
```json
{
    "type": "",
    "data": {
        "format": "opus",           // string: 音频格式(opus、wav、pcm)
        "sample_rate": 16000,       // number: 采样率
        "channels": 1,              // number: 声道数
        "frame_duration": 60,       // number: 帧长
        "data": "base64",           // string: 音频数据
    }
}
```

### 服务端响应
```json

```