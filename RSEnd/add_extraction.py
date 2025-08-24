from flask import Flask, request, jsonify
from pathlib import Path
from flask_cors import CORS
import cv2
import numpy as np
import os
import time
import yaml  # 需要安装 PyYAML
import paddle.inference as paddle_infer

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文
CORS(app, resource={r'/*': {'origins': '*'}})

# ==================== 你需要修改和准备的部分 (开始) ====================

# --- 准备工作 1: 定义你的分割模型文件路径 ---
# !! 将这里的路径替换成你 PaddleSeg 模型导出的文件所在的文件夹
# !! 这个文件夹里应该有  和 model.pdiparams
MODEL_DIR = Path(r"C:\Users\ROG-PC\Desktop\RSJob\RSEnd\models\road_extraction")

# --- 准备工作 2: 准备文件夹 ---
# 这个文件夹用来存放用户上传的图片和分割结果
UPLOAD_FOLDER = './static/images/road_extraction_uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ==================== 你需要修改和准备的部分 (结束) ====================


# --- 核心修改 1: 创建一个通用的图像分割推理器类 ---
class ExtractionPredictor:
    def __init__(self, model_dir, use_gpu=True, device_id=0):
        # --- 全程使用 pathlib 来处理路径 ---

        # 确保 model_dir 是一个 Path 对象
        model_dir_path = Path(model_dir)

        # 1. 加载部署配置文件 deploy.yaml
        config_path = model_dir_path / 'deploy.yaml'  # pathlib 的拼接方式
        with open(config_path, 'r') as f:
            self.deploy_cfg = yaml.safe_load(f)

        # 2. 获取模型和参数的文件名
        model_file = self.deploy_cfg['Deploy']['model']
        params_file = self.deploy_cfg['Deploy']['params']

        # 3. 加载推理配置，注意这里要把 Path 对象转换回字符串
        config = paddle_infer.Config(
            str(model_dir_path / model_file),  # 使用 str() 转换
            str(model_dir_path / params_file)  # 使用 str() 转换
        )

        # 4. 设置 GPU / CPU
        if use_gpu:
            config.enable_use_gpu(100, device_id)
        else:
            config.disable_gpu()

        config.disable_glog_info()
        config.enable_memory_optim()

        # 5. 根据配置创建推理器
        self.predictor = paddle_infer.create_predictor(config)

        # 6. 获取模型的输入句柄
        self.input_names = self.predictor.get_input_names()
        self.input_handle = self.predictor.get_input_handle(self.input_names[0])

        print(f"✅ 道路提取模型加载成功，来自: {model_dir}")

    def preprocess(self, image):
        # 分割模型的预处理通常在  中定义
        # 这里我们只做一个标准的 Normalize
        # 注意：PaddleSeg 的 Normalize 是 HWC 格式的
        mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        std = np.array([0.5, 0.5, 0.5], dtype=np.float32)

        normalized_image = (image / 255.0 - mean) / std

        transposed_image = normalized_image.transpose((2, 0, 1))  # HWC to CHW
        input_data = np.expand_dims(transposed_image, axis=0)  # Add batch dimension
        return input_data.astype('float32')

    def postprocess(self, result_map, original_image):
        # 分割模型的后处理：将分割图谱上色并与原图融合
        # result_map 是一个 [H, W] 的二维数组，每个像素的值是类别ID

        # 创建一个调色板 (可以根据你的类别数自定义颜色)
        # 假设 0:背景(黑色), 1:道路(绿色) ...
        palette = np.array([
            [0, 0, 0],  # 背景 (类别 0)
            [0, 255, 0],  # 道路 (类别 1) - 绿色
            [255, 0, 0],  # 类别 2 - 红色
            [0, 0, 255],  # 类别 3 - 蓝色
            [255, 255, 0],  # 类别 4 - 黄色
            [0, 255, 255],  # 类别 5 - 青色
            [255, 0, 255]  # 类别 6 - 品红
            # ... 你可以继续添加更多颜色
        ], dtype=np.uint8)

        # 将类别ID映射到颜色
        color_map = palette[result_map]

        # 将上色后的图谱缩放回原始图片大小
        color_map_resized = cv2.resize(color_map, (original_image.shape[1], original_image.shape[0]),
                                       interpolation=cv2.INTER_NEAREST)

        # 与原图进行融合，产生半透明效果
        blended_image = cv2.addWeighted(original_image, 0.6, color_map_resized, 0.4, 0)

        return blended_image

    def predict(self, image):
        # 1. 预处理
        input_data = self.preprocess(image)

        # 2. 将数据喂给模型
        self.input_handle.copy_from_cpu(input_data)

        # 3. 执行推理
        self.predictor.run()

        # 4. 获取输出
        output_names = self.predictor.get_output_names()
        # 分割模型的输出通常只有一个，是分割图谱
        output_handle = self.predictor.get_output_handle(output_names[0])
        result_map = output_handle.copy_to_cpu()  # shape: [1, H, W]

        # 5. 后处理
        # 去掉 batch 和 channel 维度
        result_map_squeezed = np.squeeze(result_map)

        # 将分割图上色并与原图融合
        final_image = self.postprocess(result_map_squeezed, image)

        return final_image


# --- 在程序启动时，全局加载一次模型 ---
predictor = ExtractionPredictor(MODEL_DIR, use_gpu=True)


# --- 核心修改 2: 创建一个新的路由用于图像分割 ---
@app.route('/segment_image', methods=['POST'])
def extract_road():
    if 'file' not in request.files:
        return jsonify({"error": "没有文件部分"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "没有选择文件"}), 400

    timestamp = int(time.time())
    unique_filename = f"{timestamp}_{file.filename}"

    file_bytes = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify({"error": "无法解码图片"}), 400

    # 使用我们的推理器进行预测，直接返回处理好的图片
    result_image = predictor.predict(image)

    # 保存带有分割结果的图片
    output_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    cv2.imwrite(output_path, result_image)

    # 构建返回给前端的数据
    server_url = "http://127.0.0.1:5000"
    result_url = f"{server_url}/static/images/road_extraction_uploads/{unique_filename}"

    response_data = {
        "result_image_url": result_url
    }

    return jsonify(response_data)


if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host="127.0.0.1", port=5000, debug=True)