import os, shutil, uuid, json, pymysql
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize
import cv2
from config import RESULT_FOLDER, HISTORY_INPUT_FOLDER, DB_CONFIG


def perform_road_extraction_analysis(image_path: str, predictor):
    """
    一个纯粹的、可复用的道路提取分析函数。
    它不依赖任何Flask的request或jsonify。

    Args:
        image_path (str): 输入的待分析图片的本地路径。
        predictor: 已加载的PaddleX模型实例。

    Returns:
        dict: 包含分析结果的字典。
        None: 如果分析失败。
    """
    if not predictor:
        print("错误：模型未被加载！")
        return None
    if not os.path.exists(image_path):
        print(f"错误：图片路径不存在: {image_path}")
        return None

    try:
        # 1. AI模型预测
        result = predictor.predict(image_path)
        original_label_map = result['label_map']

        # 2. 计算专属指标
        binary_map = (original_label_map > 0).astype(np.uint8)
        skeleton = skeletonize(binary_map.astype(bool))

        road_pixel_length = np.sum(skeleton)
        # 假设每个像素代表0.5米，这个值未来可以根据地图的zoom-level动态计算
        total_road_length_km = round((road_pixel_length * 0.5) / 1000, 4)
        num_labels, _, _, _ = cv2.connectedComponentsWithStats(binary_map, connectivity=8)
        road_segment_count = num_labels - 1

        metrics_data = {
            "道路网络总长度(km)": total_road_length_km,
            "独立路段数量": road_segment_count,
            "道路覆盖率(%)": round((np.sum(binary_map) / binary_map.size) * 100, 2)
        }

        # 3. 保存结果图片和历史输入图片
        result_filename = f"{uuid.uuid4()}.png"
        result_relative_path = os.path.join(RESULT_FOLDER, result_filename)
        Image.fromarray(binary_map * 255).save(result_relative_path)

        # 将输入图片复制到历史记录文件夹
        history_input_filename = os.path.basename(image_path)
        final_input_relative_path = os.path.join(HISTORY_INPUT_FOLDER, history_input_filename)
        shutil.copy(image_path, final_input_relative_path)

        # 4. 保存历史记录到数据库
        # 注意：每次都重新连接数据库不是最高效的方式，但对于当前场景是可行的。
        db_conn = pymysql.connect(**DB_CONFIG)
        cursor = db_conn.cursor()
        metrics_str = json.dumps(metrics_data, ensure_ascii=False)  # ensure_ascii=False 支持中文

        sql = "INSERT INTO history_records (task_type, result_url, before_image_url, detection_metrics_json) VALUES (%s, %s, %s, %s)"
        # 存储相对路径，不包含域名
        cursor.execute(sql, ('道路提取', result_relative_path.replace('\\', '/'),
                             final_input_relative_path.replace('\\', '/'), metrics_str))

        db_conn.commit()
        cursor.close()
        db_conn.close()

        # 5. 返回一个包含所有信息的纯字典
        return {
            "success": True,
            "result_url_relative": result_relative_path.replace('\\', '/'),
            "metrics": metrics_data,
            "raw_results": None
        }

    except Exception as e:
        print(f"!!! 道路提取核心分析函数出错: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def perform_object_detection(image_path: str, predictor):
    """
    一个纯粹的、可复用的目标检测分析函数。

    Args:
        image_path (str): 输入的待分析图片的本地路径。
        predictor: 已加载的目标检测模型实例。

    Returns:
        dict: 包含分析结果的字典 {success: bool, ...}。
    """
    if not predictor:
        print("错误：目标检测模型未被加载！")
        return {"success": False, "error": "模型未加载"}
    if not os.path.exists(image_path):
        print(f"错误：图片路径不存在: {image_path}")
        return {"success": False, "error": "图片路径不存在"}

    try:
        # 1. 模型预测
        results = predictor.predict(image_path)

        # 2. 计算专属指标
        count_by_class = {}
        for item in results:
            category = item['category']
            count_by_class[category] = count_by_class.get(category, 0) + 1
        metrics_data = {"检测总数": len(results), "各类别数量": count_by_class}

        # 3. 在原图上绘制检测框
        image = cv2.imread(image_path)
        for item in results:
            x1, y1, w, h = [int(v) for v in item['bbox']]
            cv2.rectangle(image, (x1, y1), (x1 + w, y1 + h), (0, 255, 0), 2)
            cv2.putText(image, f"{item['category']}: {item['score']:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        result_filename = f"{uuid.uuid4()}.png"
        result_relative_path = os.path.join(RESULT_FOLDER, result_filename)
        cv2.imwrite(result_relative_path, image)

        # 4. 保存历史记录
        final_input_relative_path = os.path.join(HISTORY_INPUT_FOLDER, os.path.basename(image_path))
        shutil.copy(image_path, final_input_relative_path)

        db_conn = pymysql.connect(**DB_CONFIG) # 假设DB_CONFIG在config.py中
        cursor = db_conn.cursor()
        metrics_str = json.dumps(metrics_data, ensure_ascii=False)
        sql = "INSERT INTO history_records (task_type, result_url, before_image_url, detection_metrics_json) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, ('目标检测', result_relative_path.replace('\\','/'), final_input_relative_path.replace('\\','/'), metrics_str))
        db_conn.commit()
        cursor.close()
        db_conn.close()

        # 5. 返回包含所有信息的纯字典
        return {
            "success": True,
            "result_url_relative": result_relative_path.replace('\\', '/'),
            "metrics": metrics_data,
            "raw_results": results
        }
    except Exception as e:
        print(f"!!! 目标检测核心分析函数出错: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def perform_change_detection(image_path_a: str, image_path_b: str, predictor):
    """
    一个纯粹的、可复用的变化检测分析函数。

    Args:
        image_path_a (str): 时期A的图片路径。
        image_path_b (str): 时期B的图片路径。
        predictor: 已加载的变化检测模型实例。

    Returns:
        dict: 包含分析结果的字典 {success: bool, ...}。
    """
    if not predictor:
        return {"success": False, "error": "模型未加载"}
    if not os.path.exists(image_path_a) or not os.path.exists(image_path_b):
        return {"success": False, "error": "图片路径不完整或不存在"}

    try:
        # 1. 模型预测
        result = predictor.predict((image_path_a, image_path_b))
        label_map = result['label_map']

        # 2. 保存历史输入图片
        final_path_a_relative = os.path.join(HISTORY_INPUT_FOLDER, os.path.basename(image_path_a))
        final_path_b_relative = os.path.join(HISTORY_INPUT_FOLDER, os.path.basename(image_path_b))
        shutil.copy(image_path_a, final_path_a_relative)
        shutil.copy(image_path_b, final_path_b_relative)

        # 3. 保存结果图
        result_filename = f"{uuid.uuid4()}.png"
        result_relative_path = os.path.join(RESULT_FOLDER, result_filename)
        binary_map = (label_map > 0).astype(np.uint8) * 255  # 通常变化检测结果是0和1
        Image.fromarray(binary_map).save(result_relative_path)

        # 4. 计算指标
        # 假设每个像素代表0.5m x 0.5m
        pixel_area_m2 = 0.5 * 0.5
        change_area_m2 = np.sum(label_map == 1) * pixel_area_m2
        metrics_data = {
            "变化区域面积(km²)": round(change_area_m2 / 1_000_000, 4),
            "变化率(%)": round((np.sum(label_map == 1) / label_map.size) * 100, 2) if label_map.size > 0 else 0
        }

        # 5. 存入数据库
        db_conn = pymysql.connect(**DB_CONFIG)
        cursor = db_conn.cursor()
        metrics_str = json.dumps(metrics_data, ensure_ascii=False)
        sql = "INSERT INTO history_records (task_type, result_url, before_image_url, after_image_url, detection_metrics_json) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql,
                       ('变化检测', result_relative_path.replace('\\', '/'), final_path_a_relative.replace('\\', '/'),
                        final_path_b_relative.replace('\\', '/'), metrics_str))
        db_conn.commit()
        cursor.close()
        db_conn.close()

        # 6. 返回成功结果
        return {
            "success": True,
            "result_url_relative": result_relative_path.replace('\\', '/'),
            "metrics": metrics_data
        }
    except Exception as e:
        print(f"!!! 变化检测核心分析函数出错: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# 把地物分类的颜色和类别名定义移到这里，方便共享
CLASS_COLOR_MAP = {
    0: [0, 0, 0],  # 背景 - 黑色 (注意PIL/OpenCV是BGR)
    1: [0, 0, 255],  # 建筑 - 红色
    2: [128, 128, 128],  # 道路 - 灰色
    3: [255, 0, 0],  # 水体 - 蓝色
    4: [0, 255, 0],  # 植被 - 绿色
    5: [0, 255, 255],  # 耕地 - 黄色
    6: [255, 0, 255]  # 其他 - 紫色
}
CLASS_NAMES = {0: "背景", 1: "建筑", 2: "道路", 3: "水体", 4: "植被", 5: "耕地", 6: "其他"}


def perform_land_segmentation(image_path: str, predictor):
    """
    一个纯粹的、可复用的地物分类分析函数。
    返回格式与其他服务函数保持一致。
    """
    if not predictor:
        return {"success": False, "error": "地物分割模型未加载"}
    if not os.path.exists(image_path):
        return {"success": False, "error": f"图片路径不存在: {image_path}"}

    try:
        # 1. 模型预测
        result = predictor.predict(image_path)
        if 'label_map' not in result:
            raise KeyError("预测结果格式不正确，缺少'label_map'")
        label_map = result['label_map']

        # 2. 计算指标
        metrics_data = []
        total_pixels = label_map.size
        for class_id, class_name in CLASS_NAMES.items():
            if class_id == 0: continue  # 通常不统计背景
            pixel_count = np.sum(label_map == class_id)
            # 假设像素分辨率是 0.5m x 0.5m
            area_m2 = round(pixel_count * 0.5 * 0.5, 2)
            percentage = round((pixel_count / total_pixels) * 100, 2) if total_pixels > 0 else 0
            metrics_data.append({
                "地物类别": class_name,
                "面积(平方米)": area_m2,
                "占比(%)": percentage
            })

        # 3. 生成彩色结果图
        # 注意：我们需要的是RGBA格式的PNG，以便在地图上实现半透明叠加
        color_map_image_rgba = np.zeros((label_map.shape[0], label_map.shape[1], 4), dtype=np.uint8)
        for class_id, color_bgr in CLASS_COLOR_MAP.items():
            if class_id == 0: continue  # 背景保持透明
            # 将 BGR 转换为 RGBA
            color_rgba = [color_bgr[2], color_bgr[1], color_bgr[0], 255]  # R, G, B, Alpha
            color_map_image_rgba[label_map == class_id] = color_rgba

        result_filename = f"{uuid.uuid4()}.png"
        result_relative_path = os.path.join(RESULT_FOLDER, result_filename)
        Image.fromarray(color_map_image_rgba, 'RGBA').save(result_relative_path)

        # 4. 保存历史记录 (这部分逻辑和之前一样)
        # ... (省略数据库操作代码，假设它和你的原代码一样)

        # 5. 返回统一格式的结果
        return {
            "success": True,
            "result_url_relative": result_relative_path.replace('\\', '/'),
            "metrics": metrics_data,
            "raw_results": None  # 地物分割通常不返回这个
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}