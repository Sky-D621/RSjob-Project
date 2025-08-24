from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import os
import time

# --- 核心修改 1: 导入正确的推理库 ---
# 我们不再使用 paddlers，而是使用 paddle.inference，这是官方推荐的、更底层的推理库
import paddle.inference as paddle_infer

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文
CORS(app, resource={r'/*': {'origins': '*'}})

# ==================== 你需要修改和准备的部分 (开始) ====================

# --- 准备工作 1: 定义你的模型文件路径 ---
# 将这里的路径替换成你第一个模型导出的文件所在的文件夹
MODEL_DIR = r"C:\Users\ROG-PC\Desktop\RSJob\RSEnd\models\object_detection"

# --- 准备工作 2: 定义你的类别名称 ---
# !!非常重要!!
# 例如，如果 0 是飞机, 1 是操场...
# 注意：第一个通常是背景，如果你没有背景类，就从你的第一个目标开始
CLASS_NAMES = ['aircraft', 'oiltank', 'overpass', 'playground']  # 这是一个例子，请务必修改成你自己的！

# --- 准备工作 3: 准备文件夹 ---
# 这个文件夹用来存放用户上传的图片和检测结果
UPLOAD_FOLDER = './static/images/detection_uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ==================== 你需要修改和准备的部分 (结束) ====================


# --- 核心修改 2: 创建一个通用的目标检测推理器类 ---
class DetectionPredictor:
    def __init__(self, model_dir, class_names, use_gpu=True, device_id=0):
        self.class_names = class_names

        # 1. 加载推理配置
        config = paddle_infer.Config(
            os.path.join(model_dir, "model.pdmodel"),
            os.path.join(model_dir, "model.pdiparams")
        )

        # 2. 设置 GPU / CPU
        if use_gpu:
            config.enable_use_gpu(100, device_id)  # 预分配100M显存
        else:
            config.disable_gpu()

        # 3. 关闭日志，让输出干净点
        config.disable_glog_info()

        # 4. 启用内存优化
        config.enable_memory_optim()

        # 5. 根据配置创建推理器
        self.predictor = paddle_infer.create_predictor(config)

        # 6. 获取模型的输入句柄
        self.input_names = self.predictor.get_input_names()
        self.input_handle = self.predictor.get_input_handle(self.input_names[0])

        print(f"✅ 目标检测模型加载成功，来自: {model_dir}")

    def preprocess(self, image):
        # 预处理：将图片缩放到 640x640，并进行归一化
        # 这是 PP-YOLO 系列模型的标准预处理流程
        input_image = cv2.resize(image, (640, 640))
        input_image = input_image / 255.0
        input_image = input_image.transpose((2, 0, 1))  # HWC to CHW
        input_image = np.expand_dims(input_image, axis=0)  # Add batch dimension
        return input_image.astype('float32')

    def predict(self, image):
        # 1. 预处理
        input_data = self.preprocess(image)

        # 2. 将数据喂给模型
        self.input_handle.copy_from_cpu(input_data)

        # 3. 执行推理
        self.predictor.run()

        # 4. 获取输出
        output_names = self.predictor.get_output_names()
        # 通常目标检测的输出有两个: 'multiclass_nms3_0.tmp_0' (检测框信息) 和 'multiclass_nms3_0.tmp_1' (检测框数量)
        boxes_handle = self.predictor.get_output_handle(output_names[0])
        boxes_num_handle = self.predictor.get_output_handle(output_names[1])

        boxes_result = boxes_handle.copy_to_cpu()
        boxes_num_result = boxes_num_handle.copy_to_cpu()

        # 5. 解析结果
        results = []
        if boxes_num_result[0] > 0:
            for i in range(boxes_num_result[0]):
                box_info = boxes_result[i]
                class_id = int(box_info[0])
                score = float(box_info[1])
                # 将坐标从 0-1 范围转换回原始图片尺寸
                x_min = int(box_info[2] * image.shape[1])
                y_min = int(box_info[3] * image.shape[0])
                x_max = int(box_info[4] * image.shape[1])
                y_max = int(box_info[5] * image.shape[0])

                results.append({
                    "class_name": self.class_names[class_id],
                    "score": score,
                    "box": [x_min, y_min, x_max, y_max]
                })
        return results


# --- 在程序启动时，全局加载一次模型 ---
predictor = DetectionPredictor(MODEL_DIR, CLASS_NAMES, use_gpu=True)


# --- 核心修改 3: 创建一个新的路由用于目标检测 ---
@app.route('/detect_object', methods=['POST'])
def detect_object():
    # 1. 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({"error": "没有文件部分"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "没有选择文件"}), 400

    # 2. 读取图片
    # 生成一个基于时间戳的唯一文件名，避免重名
    timestamp = int(time.time())
    unique_filename = f"{timestamp}_{file.filename}"

    # 将图片数据解码为 OpenCV 格式
    file_bytes = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify({"error": "无法解码图片"}), 400

    # 3. 使用我们的推理器进行预测
    detection_results = predictor.predict(image)

    # 4. (可选) 在图片上画出检测框和标签
    for result in detection_results:
        if result['score'] > 0.5:  # 只画出置信度大于 0.5 的框
            box = result['box']
            cv2.rectangle(image, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
            label = f"{result['class_name']}: {result['score']:.2f}"
            cv2.putText(image, label, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # 5. 保存带有检测框的图片
    output_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    cv2.imwrite(output_path, image)

    # 6. 构建返回给前端的数据
    # 将 http://127.0.0.1:5000 替换成你的实际服务器地址
    # 如果部署在云端，需要是公网 IP 或域名
    server_url = "http://127.0.0.1:5000"
    result_url = f"{server_url}/static/images/detection_uploads/{unique_filename}"

    response_data = {
        "result_image_url": result_url,
        "detections": detection_results
    }

    return jsonify(response_data)


if __name__ == '__main__':
    # 确保 static 文件夹是存在的，Flask 会自动从这里提供静态文件服务
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host="127.0.0.1", port=5000, debug=True)