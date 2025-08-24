from flask import Blueprint, request, jsonify
import os, cv2, uuid, json, numpy as np, shutil, pymysql
import traceback
from PIL import Image
from services.analysis_service import perform_object_detection
from .utils import CustomPaddleDetPredictor, get_extended_image_info, get_image_quality_metrics

object_detection_bp = Blueprint('object_detection', __name__)

TEMP_FOLDER = 'temp_uploads'
RESULT_FOLDER = 'static/output'
HISTORY_INPUT_FOLDER = 'static/history_inputs'

try:
    predictor_obj = CustomPaddleDetPredictor("models/object_detection/")
    print("目标检测模型加载成功！")
except Exception as e:
    print(f"加载目标检测模型失败: {e}")
    predictor_obj = None

@object_detection_bp.route('/upload_and_analyze_single', methods=['POST'])
def upload_and_analyze_single():
    if 'file' not in request.files: return jsonify({"error": "没有找到文件"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "没有选择文件"}), 400

    ext = os.path.splitext(file.filename)[1]
    temp_path = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}{ext}")
    file.save(temp_path)

    info = get_extended_image_info(temp_path)
    quality = get_image_quality_metrics(temp_path)

    return jsonify({ "metrics": {**info, **quality}, "path": temp_path })

@object_detection_bp.route('/predict', methods=['POST'])
def predict_object_detection():
    data = request.get_json()
    temp_path = data.get('path')
    if not temp_path: return jsonify({"error": "缺少图片路径"}), 400
    if not predictor_obj: return jsonify({"error": "目标检测模型未加载"}), 500

    analysis_result = perform_object_detection(temp_path, predictor_obj)

    # 3. 接口层：根据服务结果包装HTTP响应
    if analysis_result and analysis_result["success"]:
        return jsonify({
            "result_url": request.host_url + analysis_result["result_url_relative"],
            "detection_metrics": analysis_result["metrics"],
            "raw_results": analysis_result["raw_results"]
        })
    else:
        error_msg = analysis_result.get("error", "未知内部错误")
        return jsonify({"error": f"检测过程中发生错误: {error_msg}"}), 500