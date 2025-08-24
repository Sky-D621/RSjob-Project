from flask import Blueprint, request, jsonify
import os, uuid, json, numpy as np, shutil, pymysql,cv2
from PIL import Image
from skimage.morphology import skeletonize
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

    try:
        result = predictor_road.predict(temp_path)
        original_label_map = result['label_map']

        # --- 计算专属指标 ---
        binary_map = (original_label_map > 0).astype(np.uint8)
        skeleton = skeletonize(binary_map.astype(bool))

        road_pixel_length = np.sum(skeleton)
        total_road_length_km = round((road_pixel_length * 0.5) / 1000, 4)
        num_labels, _, _, _ = cv2.connectedComponentsWithStats(binary_map, connectivity=8)
        road_segment_count = num_labels - 1

        metrics_data = {
            "道路网络总长度(km)": total_road_length_km,
            "独立路段数量": road_segment_count,
            "道路覆盖率(%)": round((np.sum(binary_map) / binary_map.size) * 100, 2)
        }

        # --- 保存图片 ---
        result_filename = f"{uuid.uuid4()}.png"
        result_path_full = os.path.join(RESULT_FOLDER, result_filename)
        Image.fromarray(binary_map * 255).save(result_path_full)

        final_input_path = os.path.join(HISTORY_INPUT_FOLDER, os.path.basename(temp_path))
        shutil.copy(temp_path, final_input_path)

        # --- 【核心修改】补上保存历史记录到数据库的逻辑 ---
        db_conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', db='EndJob', charset='utf8')
        cursor = db_conn.cursor()
        metrics_str = json.dumps(metrics_data)

        # 对于单图任务，把原图路径存在 before_image_url 字段里
        sql = "INSERT INTO history_records (task_type, result_url, before_image_url, detection_metrics_json) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, ('道路提取', result_path_full.replace('\\','/'), final_input_path.replace('\\','/'), metrics_str))

        db_conn.commit()
        cursor.close()
        db_conn.close()


        return jsonify({
            "result_url": request.host_url + result_path_full.replace('\\', '/'),
            "detection_metrics": metrics_data,
            "raw_label_map": binary_map.tolist()
        })

    except Exception as e:
        print(f"!!! 道路提取检测出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"检测过程中发生错误: {e}"}), 500
