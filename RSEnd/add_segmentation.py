from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import os
import time
import yaml
from pathlib import Path  # 使用 pathlib 来处理路径，最安全
import paddle.inference as paddle_infer

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文
CORS(app, resource={r'/*': {'origins': '*'}})

# ==================== 你需要修改和准备的部分 (开始) ====================

# --- 准备工作 1: 定义你的第三个模型文件路径 ---
# !! 将这里的路径替换成你第三个模型导出的文件所在的文件夹
# !! 这个文件夹里应该有 deploy.yaml 和 model.pdiparams
MODEL_DIR = Path(r"C:\Users\ROG-PC\Desktop\RSJob\RSEnd\models\land_segmentation")  # 使用 Path 对象

# --- 准备工作 2: 准备文件夹 ---
UPLOAD_FOLDER = './static/images/landcover_uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ==================== 你需要修改和准备的部分 (结束) ====================


# --- 这个推理器类和上一个分割模型的完全相同 ---
class SegmentationPredictor:
    def __init__(self, model_dir, use_gpu=True, device_id=0):
        # --- 全程使用 pathlib 来处理路径 ---
        model_dir_path = Path(model_dir)

        # 1. 加载部署配置文件 deploy.yaml
        config_path = model_dir_path / 'deploy.yaml'
        # 在加载前，先创建一个空的 model.pdmodel (如果它不存在) 来绕过 bug
        model_placeholder_path = model_dir_path / 'model.pdmodel'
        if not model_placeholder_path.exists():
            print(f"⚠️ 'model.pdmodel' not found. Creating a placeholder file to bypass API bug.")
            model_placeholder_path.touch()

        with open(config_path, 'r') as f:
            self.deploy_cfg = yaml.safe_load(f)

        # 2. 获取模型和参数的文件名
        model_file = self.deploy_cfg['Deploy']['model']
        params_file = self.deploy_cfg['Deploy']['params']

        # 3. 加载推理配置
        config = paddle_infer.Config(
            str(model_dir_path / model_file),
            str(model_dir_path / params_file)
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

        print(f"✅ 地物分割模型加载成功，来自: {model_dir}")

    def preprocess(self, image):
        # ... (预处理部分和上一个分割模型相同)
        mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        normalized_image = (image / 255.0 - mean) / std
        transposed_image = normalized_image.transpose((2, 0, 1))
        input_data = np.expand_dims(transposed_image, axis=0)
        return input_data.astype('float32')

    def postprocess(self, result_map, original_image):
        # ... (后处理部分和上一个分割模型相同, 但调色板可能需要修改)
        # !! 你需要根据第三个模型的 7 个类别，定义你想要的颜色
        palette = np.array([
            [0, 0, 0],  # 类别 0: 背景 (黑色)
            [255, 0, 0],  # 类别 1: 建筑 (红色)
            [0, 255, 0],  # 类别 2: 农田 (绿色)
            [0, 0, 255],  # 类别 3: 水体 (蓝色)
            [255, 255, 0],  # 类别 4: 道路 (黄色)
            [128, 0, 128],  # 类别 5: 森林 (紫色)
            [255, 165, 0],  # 类别 6: 裸地 (橙色)
        ], dtype=np.uint8)

        color_map = palette[result_map]
        color_map_resized = cv2.resize(color_map, (original_image.shape[1], original_image.shape[0]),
                                       interpolation=cv2.INTER_NEAREST)
        blended_image = cv2.addWeighted(original_image, 0.6, color_map_resized, 0.4, 0)
        return blended_image

    def predict(self, image):
        # ... (预测流程和上一个分割模型完全相同)
        input_data = self.preprocess(image)
        self.input_handle.copy_from_cpu(input_data)
        self.predictor.run()
        output_names = self.predictor.get_output_names()
        output_handle = self.predictor.get_output_handle(output_names[0])
        result_map = output_handle.copy_to_cpu()
        result_map_squeezed = np.squeeze(result_map)
        final_image = self.postprocess(result_map_squeezed, image)
        return final_image


# --- 在程序启动时，全局加载一次模型 ---
try:
    predictor = SegmentationPredictor(MODEL_DIR, use_gpu=True)
except Exception as e:
    print(f"❌ 模型加载失败，请检查模型路径和文件。错误: {e}")
    predictor = None  # 标记为加载失败


# --- 新的路由用于地物分割 ---
@app.route('/classify_land', methods=['POST'])
def classify_land():
    if predictor is None:
        return jsonify({"error": "模型未能成功加载，无法提供服务。"}), 500

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

    result_image = predictor.predict(image)

    output_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    cv2.imwrite(output_path, result_image)

    server_url = "http://127.0.0.1:5000"
    result_url = f"{server_url}/static/images/landcover_uploads/{unique_filename}"

    response_data = {
        "result_image_url": result_url
    }

    return jsonify(response_data)


if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host="127.0.0.1", port=5000, debug=True)