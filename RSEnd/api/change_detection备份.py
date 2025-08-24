from flask import Blueprint, Flask, json, request, jsonify
from flask_cors import CORS
from skimage.metrics import structural_similarity as ssim
import shutil
import pymysql
import cv2
import numpy as np
import os
import uuid
from PIL import Image
import imagehash
DEBUG = True
from PIL import Image
from paddlers.deploy import Predictor

change_detection_bf_bp = Blueprint('change_detection_bf', __name__)


predictor = Predictor("./models/rscd/", use_gpu=True)


RESULT_FOLDER = 'static/output'
TEMP_FOLDER = 'temp_uploads'
HISTORY_INPUT_FOLDER = 'static/history_inputs'
for folder in [TEMP_FOLDER, RESULT_FOLDER, HISTORY_INPUT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

def get_image_sharpness(image_path):
    """计算图像的清晰度"""
    try:
        img = cv2.imread(image_path)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 值越高，通常表示图片越清晰
        sharpness = cv2.Laplacian(gray_img, cv2.CV_64F).var()
        return round(sharpness, 2)
    except Exception:
        return "N/A"


def get_extended_image_info(image_path):
    try:

        pil_img = Image.open(image_path)

        # 使用OpenCV获取其他信息
        cv_img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

        height, width = cv_img.shape[:2]
        channels = cv_img.shape[2] if len(cv_img.shape) == 3 else 1

        info = {
            "文件名": os.path.basename(image_path),
            "尺寸": f"{width} x {height}",
            "通道数": channels,
            "数据类型": str(cv_img.dtype),
            "文件大小(KB)": round(os.path.getsize(image_path) / 1024, 2),
            "打印分辨率(DPI)": pil_img.info.get('dpi', ('N/A', 'N/A'))[0],  # 尝试获取DPI
            "图像哈希值": str(imagehash.phash(pil_img)),  # 计算感知哈希
            "清晰度评估": get_image_sharpness(image_path)  # 计算清晰度
        }
        return info
    except Exception as e:
        return {"错误": f"计算扩展信息时出错: {e}"}


def get_image_quality_metrics(image_path):
    """计算影像的质量指标"""
    try:
        img = cv2.imread(image_path)
        if img is None: return {"错误": "无法读取图片"}

        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        metrics = {
            "平均亮度": round(np.mean(gray_img), 2),
            "对比度": round(np.std(gray_img), 2)
        }
        return metrics
    except Exception as e:
        return {"错误": f"计算质量指标时出错: {e}"}


def get_image_difference_metrics(image_path_a, image_path_b):
    """计算两张影像的差异性指标"""
    try:
        img_a = cv2.imread(image_path_a)
        img_b = cv2.imread(image_path_b)
        if img_a is None or img_b is None: return {"错误": "无法读取其中一张或多张图片"}

        # 确保两张图片尺寸一致
        if img_a.shape != img_b.shape:
            img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))

        gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
        gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

        similarity_score, _ = ssim(gray_a, gray_b, full=True)

        metrics = {
            "结构相似度(SSIM)": round(similarity_score, 4)
        }
        return metrics
    except Exception as e:
        return {"错误": f"计算差异性指标时出错: {e}"}


@change_detection_bf_bp.route('/upload_and_analyze_metrics', methods=['POST'])
def upload_and_analyze_metrics():
    # 这个接口负责接收图片、保存、计算指标，并返回服务器路径和指标
    image_a_file = request.files.get('image_a')
    image_b_file = request.files.get('image_b')
    if not image_a_file or not image_b_file: return jsonify({"error": "需要上传两张图片"}), 400

    # 生成唯一路径并保存
    ext_a = os.path.splitext(image_a_file.filename)[1]
    path_a = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}{ext_a}")
    image_a_file.save(path_a)

    ext_b = os.path.splitext(image_b_file.filename)[1]
    path_b = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}{ext_b}")
    image_b_file.save(path_b)

    # 计算指标
    info_a, quality_a = get_extended_image_info(path_a), get_image_quality_metrics(path_a)
    info_b, quality_b = get_extended_image_info(path_b), get_image_quality_metrics(path_b)
    difference = get_image_difference_metrics(path_a, path_b)

    return jsonify({
        "metrics": { "imageA": {**info_a, **quality_a}, "imageB": {**info_b, **quality_b}, "differenceMetrics": difference },
        "paths": { "path_a": path_a, "path_b": path_b } # 把服务器路径返回给前端
    })


@change_detection_bf_bp.route('/predict', methods=['POST'])
def predict_change_detection():
    # 这个接口只负责一件事：根据前端传来的路径进行检测
    data = request.get_json()
    path_a = data.get('path_a')
    path_b = data.get('path_b')

    if not path_a or not path_b: return jsonify({"error": "缺少图片路径"}), 400
    if not predictor: return jsonify({"error": "模型未加载，无法检测"}), 500

    try:
        # 调用模型预测
        result = predictor.predict((path_a, path_b))
        label_map = result['label_map']

        final_path_a = os.path.join(HISTORY_INPUT_FOLDER, os.path.basename(path_a))
        final_path_b = os.path.join(HISTORY_INPUT_FOLDER, os.path.basename(path_b))
        shutil.copy(path_a, final_path_a)
        shutil.copy(path_b, final_path_b)

        # 将结果保存为图片
        result_filename = f"{uuid.uuid4()}.png"
        result_path = os.path.join(RESULT_FOLDER, result_filename)
        # 转换为二值图像并保存
        binary_map = (label_map > 0.5).astype(np.uint8) * 255
        Image.fromarray(binary_map).save(result_path)

        result_url = request.host_url + result_path.replace('\\', '/')

        db_conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', db='EndJob',
                                  charset='utf8')
        cursor = db_conn.cursor()

        # 将指标字典转换为JSON字符串以便存储
        metrics_data = {"change_area_km2": round((np.sum(label_map == 1) * 0.5 * 0.5) / 1_000_000, 4),
                        "change_rate": round((np.sum(label_map == 1) / label_map.size) * 100,
                                             2) if label_map.size > 0 else 0}
        metrics_str = json.dumps(metrics_data)

        sql = "INSERT INTO history_records (task_type, result_url, before_image_url, after_image_url, detection_metrics_json) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, ('变化检测', result_url, final_path_a.replace('\\', '/'), final_path_b.replace('\\', '/'), metrics_str))

        db_conn.commit()
        cursor.close()
        db_conn.close()

        # 返回结果图片的URL

        return jsonify({
            "result_url": result_url,
            "detection_metrics": {
            }
        })


    except Exception as e:
        return jsonify({"error": f"检测过程中发生错误: {e}"}), 500


