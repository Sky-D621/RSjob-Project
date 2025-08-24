from flask import Blueprint, request, jsonify
from pydantic import BaseModel, ValidationError, Field
from typing import Optional
import math, requests, io, os, uuid
from PIL import Image
from config import TEMP_FOLDER
from services.analysis_service import perform_road_extraction_analysis, perform_object_detection, perform_change_detection, perform_land_segmentation
from .road_extraction import predictor_road
from .object_detection import predictor_obj # 导入其他模块的函数
from .change_detection import predictor
from .land_segmentation import predictor_ls

map_analysis_bp = Blueprint('map_analysis', __name__)


# --- Pydantic 输入验证模型 ---
class Coordinate(BaseModel):
    lat: float
    lng: float

class SingleImagePayload(BaseModel):
    task_type: str
    southWest: Coordinate
    northEast: Coordinate
    zoom: int
    tileUrlTemplate: str

class ChangeDetectionPayload(BaseModel):
    task_type: str
    southWest: Coordinate
    northEast: Coordinate
    zoom: int
    beforeTileUrl: str
    afterTileUrl: str


# --- 瓦片计算与拼接核心函数 ---

def deg2num(lat_deg, lon_deg, zoom):
    """将经纬度转换为瓦片编号"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def fetch_and_stitch_tiles(sw, ne, zoom, url_template):
    """根据边界坐标和缩放等级，下载并拼接瓦片"""

    # 1. 计算需要下载的瓦片范围
    xtile_sw, ytile_sw = deg2num(sw.lat, sw.lng, zoom)
    xtile_ne, ytile_ne = deg2num(ne.lat, ne.lng, zoom)

    # 确保范围正确
    min_x, max_x = sorted((xtile_sw, xtile_ne))
    min_y, max_y = sorted((ytile_sw, ytile_ne))

    # 2. 下载所有瓦片
    tile_images = {}
    gaode_url_template = "https://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}"

    print(f"准备下载 {max_x - min_x + 1} x {max_y - min_y + 1} 个瓦片...")
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            url = url_template.format(s=2, x=x, y=y, z=zoom)
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    tile_images[(x, y)] = Image.open(io.BytesIO(response.content))
            except Exception as e:
                print(f"下载瓦片 (x={x}, y={y}, z={zoom}) 失败: {e}")
                return None

    if not tile_images:
        return None

    # 3. 拼接瓦片
    tile_size = 256  # 高德瓦片是256x256
    width = (max_x - min_x + 1) * tile_size
    height = (max_y - min_y + 1) * tile_size

    stitched_image = Image.new('RGB', (width, height))

    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            if (x, y) in tile_images:
                paste_x = (x - min_x) * tile_size
                paste_y = (y - min_y) * tile_size
                stitched_image.paste(tile_images[(x, y)], (paste_x, paste_y))

    return stitched_image


@map_analysis_bp.route('/predict_from_coords', methods=['POST'])
def predict_from_coords():
    data = request.get_json()
    if not data or 'task_type' not in data:
        return jsonify({"error": "请求缺少 task_type"}), 400

    task_type = data['task_type']

    try:
        # 使用不同的模型验证请求体
        if task_type == 'change_detection':
            payload = ChangeDetectionPayload.model_validate(data)
        else:
            payload = SingleImagePayload.model_validate(data)
    except ValidationError as e:
        return jsonify({"error": "请求数据格式错误", "details": e.errors()}), 400

    analysis_result = None

    try:
        if task_type == 'change_detection':
            # 下载两张影像并保存临时文件
            image_a = fetch_and_stitch_tiles(payload.southWest, payload.northEast, payload.zoom, payload.beforeTileUrl)
            image_b = fetch_and_stitch_tiles(payload.southWest, payload.northEast, payload.zoom, payload.afterTileUrl)

            if image_a is None or image_b is None:
                return jsonify({"error": "从地图服务获取影像失败"}), 500

            temp_path_a = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}_a.png")
            temp_path_b = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}_b.png")
            image_a.save(temp_path_a)
            image_b.save(temp_path_b)

            # 注意这里是两个路径传入

            try:
                image_a.save(temp_path_a)
                image_b.save(temp_path_b)
                analysis_result = perform_change_detection(temp_path_a, temp_path_b, predictor)
            finally:
                if os.path.exists(temp_path_a):
                    os.remove(temp_path_a)
                if os.path.exists(temp_path_b):
                    os.remove(temp_path_b)

        else:
            # 单图分析（道路或目标检测）
            stitched_image = fetch_and_stitch_tiles(payload.southWest, payload.northEast, payload.zoom,
                                                    payload.tileUrlTemplate)
            if stitched_image is None:
                return jsonify({"error": "从地图服务获取影像失败"}), 500

            temp_path = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}.png")

            try:
                stitched_image.save(temp_path)
                if payload.task_type == 'road_extraction':
                    analysis_result = perform_road_extraction_analysis(temp_path, predictor_road)
                elif payload.task_type == 'object_detection':
                    analysis_result = perform_object_detection(temp_path, predictor_obj)
                elif task_type == 'land_segmentation':
                    analysis_result = perform_land_segmentation(temp_path, predictor_ls)
            finally:
                # 确保单图分析的临时文件也被清理
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # --- 统一结果返回逻辑 ---
        if analysis_result and analysis_result.get("success"):
            relative_url = analysis_result.get("result_url_relative")
            full_result_url = request.host_url + relative_url if relative_url else None

            final_response = {
                "message": f"{task_type} 分析成功！",
                "result_url": full_result_url,
                "detection_metrics": analysis_result.get("metrics"),
                "raw_results": analysis_result.get("raw_results")
            }
            return jsonify(final_response)
        else:
            error_msg = analysis_result.get("error", "未知错误") if analysis_result else "服务函数未返回任何结果"
            return jsonify({"error": f"执行分析任务时发生错误: {error_msg}"}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"后端发生严重错误: {str(e)}"}), 500
