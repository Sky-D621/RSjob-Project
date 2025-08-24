from flask import Blueprint, request, jsonify
import os, cv2, uuid, json, numpy as np, shutil, pymysql
import traceback
from PIL import Image
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

    try:
        # 1. 模型预测，结果是包含多个字典的列表
        # 每个字典代表一个检测到的目标: {'category': '飞机', 'bbox': [x1, y1, x2, y2], 'score': 0.9}
        results = predictor_obj.predict(temp_path)

        # 2. 计算专属指标
        total_objects = len(results)
        count_by_class = {}
        for item in results:
            category = item['category']
            count_by_class[category] = count_by_class.get(category, 0) + 1

        metrics_data = { "检测总数": total_objects, "各类别数量": count_by_class }

        # 3. 在原图上绘制检测框和标签，生成结果图
        image = cv2.imread(temp_path)
        for item in results:
            x1, y1, w, h = [int(v) for v in item['bbox']]
            cv2.rectangle(image, (x1, y1), (x1 + w, y1 + h), (0, 255, 0), 2)
            cv2.putText(image, f"{item['category']}: {item['score']:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        result_filename = f"{uuid.uuid4()}.png"
        result_path_full = os.path.join(RESULT_FOLDER, result_filename)
        cv2.imwrite(result_path_full, image)

        # 4. 保存历史记录
        final_input_path = os.path.join(HISTORY_INPUT_FOLDER, os.path.basename(temp_path))
        shutil.copy(temp_path, final_input_path)

        db_conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', db='EndJob',
                                  charset='utf8')
        cursor = db_conn.cursor()
        metrics_str = json.dumps(metrics_data)

        sql = "INSERT INTO history_records (task_type, result_url, before_image_url, detection_metrics_json) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, ('目标检测', result_path_full.replace('\\', '/'), final_input_path.replace('\\', '/'),
                             metrics_str))

        db_conn.commit()
        cursor.close()
        db_conn.close()

        return jsonify({
            "result_url": request.host_url + result_path_full.replace('\\', '/'),
            "detection_metrics": metrics_data,
            "raw_results": results  # <-- 新增：返回原始检测框数据，用于高亮
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"检测过程中发生错误: {e}"}), 500