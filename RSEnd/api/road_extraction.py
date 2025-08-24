from flask import Blueprint, request, jsonify
import os, uuid
from services.analysis_service import perform_road_extraction_analysis
from .utils import get_extended_image_info, get_image_quality_metrics, CustomPaddleSegPredictor


road_extraction_bp = Blueprint('road_extraction', __name__)

TEMP_FOLDER = 'temp_uploads'
RESULT_FOLDER = 'static/output'
HISTORY_INPUT_FOLDER = 'static/history_inputs'

try:
    predictor_road = CustomPaddleSegPredictor("models/road_extraction/")
    print("道路提取模型（使用自定义引擎）加载成功！")
except Exception as e:
    print(f"加载道路提取模型失败: {e}")
    predictor_road = None

@road_extraction_bp.route('/upload_and_analyze_single', methods=['POST'])
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


@road_extraction_bp.route('/predict', methods=['POST'])
def predict_road_extraction():
    data = request.get_json()
    temp_path = data.get('path')
    if not temp_path: return jsonify({"error": "缺少图片路径"}), 400
    if not predictor_road: return jsonify({"error": "道路提取模型未加载"}), 500

    analysis_result = perform_road_extraction_analysis(temp_path, predictor_road)

    # --- 接口逻辑：根据服务函数的返回结果，包装成HTTP响应 ---
    if analysis_result and analysis_result["success"]:
        return jsonify({
            "result_url": request.host_url + analysis_result["result_url_relative"],
            "detection_metrics": analysis_result["metrics"],
            "raw_results": analysis_result["raw_results"]
        })
    else:
        error_msg = analysis_result.get("error", "未知内部错误")
        return jsonify({"error": f"检测过程中发生错误: {error_msg}"}), 500
