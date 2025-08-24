from flask import Blueprint, request, jsonify
import os, cv2, uuid, json, numpy as np, shutil, pymysql
from PIL import Image
from .utils import CustomPaddleSegPredictorFromDetConfig, get_extended_image_info, get_image_quality_metrics

land_segmentation_bp = Blueprint('land_segmentation', __name__)

TEMP_FOLDER = 'temp_uploads'
RESULT_FOLDER = 'static/output'
HISTORY_INPUT_FOLDER = 'static/history_inputs'

# 为地物类别定义颜色 (BGR格式)
CLASS_COLOR_MAP = {
    0: [0, 0, 0],       # 背景 - 黑色
    1: [255, 0, 0],     # 建筑 - 红色
    2: [128, 128, 128], # 道路 - 灰色
    3: [0, 0, 255],     # 水体 - 蓝色
    4: [0, 255, 0],     # 植被 - 绿色
    5: [0, 255, 255],   # 耕地 - 黄色
    6: [255, 0, 255]    # 其他 - 紫色
}
CLASS_NAMES = {0: "背景", 1: "建筑", 2: "道路", 3: "水体", 4: "植被", 5: "耕地", 6: "其他"}

try:
    # !!注意：请确保 "models/land_segmentation_model/" 是您地物分割模型的正确路径
    predictor_ls = CustomPaddleSegPredictorFromDetConfig("models/land_segmentation/")
    print("地物分割模型加载成功！")
except Exception as e:
    print(f"加载地物分割模型失败: {e}")
    predictor_ls = None

@land_segmentation_bp.route('/upload_and_analyze_single', methods=['POST'])
def upload_and_analyze_single():
    # 这个接口与道路提取的完全一样，直接复用
    if 'file' not in request.files: return jsonify({"error": "没有找到文件"}), 400
    file = request.files['file'];
    if file.filename == '': return jsonify({"error": "没有选择文件"}), 400
    ext = os.path.splitext(file.filename)[1]
    temp_path = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}{ext}")
    file.save(temp_path)
    info = get_extended_image_info(temp_path)
    quality = get_image_quality_metrics(temp_path)
    return jsonify({ "metrics": {**info, **quality}, "path": temp_path })


@land_segmentation_bp.route('/predict', methods=['POST'])
def predict_land_segmentation():
    print("\n--- [DEBUG] 进入 predict_land_segmentation 接口 ---")
    temp_path = None  # 初始化变量
    try:
        if 'file' not in request.files:
            print("[DEBUG] 错误: 请求中没有找到 'file'")
            return jsonify({"error": "没有找到文件"}), 400
        file = request.files['file']
        if file.filename == '':
            print("[DEBUG] 错误: 没有选择文件")
            return jsonify({"error": "没有选择文件"}), 400

        print(f"[DEBUG] 接收到文件: {file.filename}")

        threshold = request.form.get('threshold', 0.5, type=float)
        model_name = request.form.get('model', 'ppliteseg')
        print(f"[DEBUG] 参数: threshold={threshold}, model={model_name}")

        ext = os.path.splitext(file.filename)[1]
        temp_path = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}{ext}")
        file.save(temp_path)
        print(f"[DEBUG] 文件已保存到临时路径: {temp_path}")

        if not predictor_ls:
            print("[DEBUG] 致命错误: 模型未加载")
            return jsonify({"error": "地物分割模型未加载"}), 500

        print("[DEBUG] 开始调用模型进行预测...")
        result = predictor_ls.predict(temp_path)
        print("[DEBUG] 模型预测完成。")

        # 检查预测结果是否符合预期
        if 'label_map' not in result:
            print(f"[DEBUG] 错误: 预测结果中没有 'label_map' 键。结果为: {result}")
            raise KeyError("预测结果格式不正确，缺少'label_map'")

        label_map = result['label_map']
        print(f"[DEBUG] 成功获取 label_map, 形状: {label_map.shape}")

        # --- 计算指标 ---
        print("[DEBUG] 开始计算指标...")
        metrics_data = []
        total_pixels = label_map.size
        for class_id, class_name in CLASS_NAMES.items():
            if class_id == 0: continue
            pixel_count = np.sum(label_map == class_id)
            area_m2 = round(pixel_count * 0.5 * 0.5, 2)
            percentage = round((pixel_count / total_pixels) * 100, 2) if total_pixels > 0 else 0
            metrics_data.append({"class_name": class_name, "area_m2": area_m2, "percentage": percentage})
        print("[DEBUG] 指标计算完成。")

        # --- 生成结果图 ---
        print("[DEBUG] 开始生成彩色结果图...")
        color_map_image = np.zeros((label_map.shape[0], label_map.shape[1], 3), dtype=np.uint8)
        for class_id, color in CLASS_COLOR_MAP.items():
            color_map_image[label_map == class_id] = color
        result_filename = f"{uuid.uuid4()}.png"
        result_path_full = os.path.join(RESULT_FOLDER, result_filename)
        cv2.imwrite(result_path_full, color_map_image)
        print(f"[DEBUG] 结果图已保存到: {result_path_full}")

        # --- 保存历史记录 ---
        print("[DEBUG] 开始保存历史记录到数据库...")
        final_input_path = os.path.join(HISTORY_INPUT_FOLDER, os.path.basename(temp_path))
        shutil.copy(temp_path, final_input_path)
        db_conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', db='EndJob',
                                  charset='utf8')
        cursor = db_conn.cursor()
        metrics_str = json.dumps(metrics_data)
        sql = "INSERT INTO history_records (task_type, result_url, before_image_url, detection_metrics_json) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, ('地物分割', result_path_full.replace('\\', '/'), final_input_path.replace('\\', '/'),
                             metrics_str))
        db_conn.commit()
        cursor.close()
        db_conn.close()
        print("[DEBUG] 历史记录保存成功。")

        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"[DEBUG] 临时文件 {temp_path} 已删除。")

        print("[DEBUG] 接口处理成功，准备返回结果。")
        return jsonify({
            "result_url": request.host_url + result_path_full.replace('\\', '/'),
            "detection_metrics": metrics_data,
            "raw_label_map": label_map.tolist()
        })
    except Exception as e:
        print(f"\n !!! [DEBUG] 发生严重错误 !!!")
        import traceback
        traceback.print_exc()  # 这会打印出完整的错误堆栈信息

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"[DEBUG] 发生错误后，临时文件 {temp_path} 已删除。")

        return jsonify({"error": f"分割过程中发生错误: {str(e)}"}), 500