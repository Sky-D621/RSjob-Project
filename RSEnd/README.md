# 遥感变化检测系统 - 后端部署指南

## 项目简介

本项目是一个基于深度学习的遥感变化检测系统，使用Flask框架构建后端API，可以接收前端上传的两个时期的遥感图像，并返回变化检测结果。

## 环境要求

- Python 3.7+
- PaddlePaddle 2.0+
- PaddleRS (PaddleSeg的遥感扩展)
- Flask
- OpenCV
- PIL

## 目录结构

```
RSEnd/
├── models/            # 模型文件夹
│   └── rscd/          # 变化检测模型
│       ├── deploy.yaml  # 部署配置
│       ├── model.json   # 模型结构
│       └── model.pdiparams # 模型参数
├── static/            # 静态文件
│   └── images/        # 图像存储
├── main.py            # 主应用程序
├── test_model.py      # 模型测试脚本
└── README.md          # 说明文档
```

## 安装依赖

```bash
pip install flask flask-cors opencv-python pillow paddlepaddle paddlers
```

如果需要GPU加速，请安装GPU版本的PaddlePaddle：

```bash
pip install paddlepaddle-gpu
```

## 模型部署

1. 确保`models/rscd/`目录下包含所有必要的模型文件
2. 运行测试脚本验证模型是否可以正常加载：

```bash
python test_model.py
```

3. 如果模型加载成功，您将看到"模型加载成功!"的提示

## 启动服务

```bash
python main.py
```

默认情况下，服务将在 http://127.0.0.1:5000 上运行

## API接口说明

### 1. 用户注册

- **URL**: `/adduser`
- **方法**: POST
- **参数**: 
  - username: 用户名
  - password: 密码
- **返回**: 文本消息

### 2. 上传前期图像

- **URL**: `/uploadbefore`
- **方法**: POST
- **参数**: 
  - username: 用户名
  - file: 图像文件
- **返回**: JSON对象，包含图像URL和路径

### 3. 上传后期图像

- **URL**: `/uploadafter`
- **方法**: POST
- **参数**: 
  - username: 用户名
  - file: 图像文件
- **返回**: JSON对象，包含图像URL和路径

### 4. 执行变化检测

- **URL**: `/detectrscd`
- **方法**: POST
- **参数**: 
  - username: 用户名
  - imgA: 前期图像路径
  - imgB: 后期图像路径
- **返回**: JSON对象，包含结果图像URL

## 故障排除

1. 如果模型加载失败，请检查模型文件是否完整，路径是否正确
2. 如果预测过程出错，请检查输入图像格式是否正确，路径是否存在
3. 如果需要使用GPU但报错，请确认PaddlePaddle GPU版本安装正确，并修改`main.py`中的`use_gpu`参数为`True`

## 自定义模型

如果您需要使用自己训练的模型，请确保：

1. 模型文件放置在`models/rscd/`目录下
2. 模型包含必要的文件：deploy.yaml, model.pdiparams等
3. 修改`main.py`中的模型加载部分以适应您的模型结构

## 注意事项

- 本系统默认使用CPU进行推理，如需使用GPU，请修改`main.py`中的`use_gpu`参数
- 上传的图像将保存在`static/images/用户名/A/`和`static/images/用户名/B/`目录下
- 检测结果将保存在`static/images/用户名/res/`目录下