import os
import cv2
import yaml
import numpy as np
import paddle.inference as paddle_infer
from PIL import Image
import imagehash


# 加载器一：专用于 PaddleDetection 导出的模型
class CustomPaddleDetPredictor:
    def __init__(self, model_dir):
        self.config_path = os.path.join(model_dir, 'model.yml')
        self.cfg = self.load_config(self.config_path)
        self.predictor = self.create_predictor(model_dir)

    def load_config(self, config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def create_predictor(self, model_dir):
        model_file = os.path.join(model_dir, 'model.pdmodel')
        params_file = os.path.join(model_dir, 'model.pdiparams')
        config = paddle_infer.Config(model_file, params_file)
        config.delete_pass("conv_bn_fuse_pass")
        return paddle_infer.create_predictor(config)

    def preprocess(self, image_path):
        img = cv2.imread(image_path)
        ori_shape = img.shape[:2]
        for op in self.cfg['Preprocess']:
            # 获取操作类型，并进行判断
            op_type = op.get('type')  # 使用 .get() 更安全，如果'type'不存在也不会报错

            if op_type == 'Resize':
                target_size = op['target_size']  # 从op中直接获取，而不是op['Resize']
                img = cv2.resize(img,
                                 (target_size, target_size) if isinstance(target_size, int) else tuple(target_size))
            elif op_type == 'NormalizeImage':
                mean = np.array(op['mean']).reshape(1, 1, -1)
                std = np.array(op['std']).reshape(1, 1, -1)
                if op.get('is_scale', True): img = img / 255.0
                img = (img - mean) / std
            elif op_type == 'Permute':  # <-- 正确的判断方式
                img = img.transpose((2, 0, 1))

        input_data = np.expand_dims(img, axis=0).astype('float32')
        im_shape = np.array([ori_shape]).astype('float32')
        # scale_factor 对于YOLO系列通常是必须的，但你的模型可能不需要。
        # 如果你的模型输入只有 image 和 im_shape，可以注释掉 scale_factor
        scale_factor = np.array([[1., 1.]]).astype('float32')
        return input_data, im_shape, scale_factor

    def postprocess(self, np_boxes):
        results = []
        if np_boxes.shape[0] > 0:
            for box in np_boxes:
                class_id, score, x1, y1, x2, y2 = box.tolist()
                if score < 0.5: continue
                results.append({'category_id': int(class_id), 'category': self.cfg['label_list'][int(class_id)],
                                'bbox': [x1, y1, x2 - x1, y2 - y1], 'score': score})
        return results

    def predict(self, image_path):
        # Preprocess step remains the same, it prepares our three "ingredients"
        input_data, im_shape, scale_factor = self.preprocess(image_path)

        # --- 【核心修改】按名字准备输入数据，而不是按顺序 ---
        inputs = {
            'image': input_data,
            'im_shape': im_shape,
            'scale_factor': scale_factor
        }

        input_names = self.predictor.get_input_names()
        for name in input_names:
            # 检查模型需要的输入名(name)，我们是否准备了对应的食材(inputs[name])
            if name in inputs:
                input_handle = self.predictor.get_input_handle(name)
                input_handle.copy_from_cpu(inputs[name])
        # --- 修改结束 ---

        # 运行推理
        self.predictor.run()

        # 获取输出的逻辑不变
        output_names = self.predictor.get_output_names()
        np_boxes = self.predictor.get_output_handle(output_names[0]).copy_to_cpu()

        return self.postprocess(np_boxes)


class CustomPaddleSegPredictorFromDetConfig:
    def __init__(self, model_dir):
        # 加载您的 model.yml 文件
        self.config_path = os.path.join(model_dir, 'model.yml')
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件未找到: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.cfg = yaml.safe_load(f)

        self.predictor = self.create_predictor(model_dir)
        print("分割模型（定制化yml配置）加载器初始化成功。")

    def create_predictor(self, model_dir):
        model_file = os.path.join(model_dir, 'model.pdmodel')
        params_file = os.path.join(model_dir, 'model.pdiparams')
        config = paddle_infer.Config(model_file, params_file)
        return paddle_infer.create_predictor(config)

    def preprocess(self, image_path):
        # --- 【核心修正】完全按照您的 model.yml 来进行预处理 ---
        img = cv2.imread(image_path)
        # 将数据类型转为 float32 用于计算
        img = img.astype('float32')

        # 保存原始图像尺寸，用于后处理时恢复
        self.ori_shape = img.shape[:2]

        # 检查 'Transforms' 键是否存在
        if 'Transforms' not in self.cfg:
            raise KeyError("在 model.yml 中没有找到 'Transforms' 键，请检查配置文件。")

        # 遍历 'Transforms' 中定义的所有操作
        for op in self.cfg['Transforms']:
            if op['type'] == 'Normalize':
                # 如果指定了 to_rgb: True，则进行 BGR -> RGB 的颜色空间转换
                if op.get('to_rgb', False):
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # 进行归一化
                mean = np.array(op['mean'], dtype=np.float32)
                std = np.array(op['std'], dtype=np.float32)
                img = (img / 255.0 - mean) / std

        # 将图像维度从 (H, W, C) 转换为 (C, H, W) 以符合模型输入要求
        img = img.transpose((2, 0, 1))
        # 增加一个批处理维度，变为 (1, C, H, W)
        input_data = np.expand_dims(img, axis=0)
        return input_data

    def postprocess(self, seg_map):
        # 将模型输出的分割图 (H, W) 恢复到原始图像的尺寸
        label_map = cv2.resize(seg_map.astype(np.uint8), (self.ori_shape[1], self.ori_shape[0]),
                               interpolation=cv2.INTER_NEAREST)
        return {'label_map': label_map}

    def predict(self, image_path):
        # 1. 调用我们新的、正确的预处理函数
        input_data = self.preprocess(image_path)

        # 2. 设置模型输入
        input_names = self.predictor.get_input_names()
        input_handle = self.predictor.get_input_handle(input_names[0])
        input_handle.copy_from_cpu(input_data)

        # 3. 运行推理
        self.predictor.run()

        # 4. 获取模型输出
        output_names = self.predictor.get_output_names()
        output_handle = self.predictor.get_output_handle(output_names[0])
        seg_map_output = output_handle.copy_to_cpu()

        # 输出通常是 (1, H, W)，我们需要去掉批处理维度
        seg_map = np.squeeze(seg_map_output, axis=0)

        # 5. 调用后处理函数，将结果图恢复至原始尺寸
        return self.postprocess(seg_map)

# 加载器二：专用于 PaddleSeg 导出的模型
class CustomPaddleSegPredictor:
    def __init__(self, model_dir):
        config_path = os.path.join(model_dir, 'model.yml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.cfg = yaml.safe_load(f)
        config = paddle_infer.Config(os.path.join(model_dir, 'model.json'), os.path.join(model_dir, 'model.pdiparams'))
        self.predictor = paddle_infer.create_predictor(config)

    def preprocess(self, image_path):
        img = cv2.imread(image_path).astype('float32')
        for op in self.cfg['Deploy']['transforms']:
            if op['type'] == 'Normalize':
                mean = np.array(op.get('mean', [0.5, 0.5, 0.5]), dtype=np.float32)
                std = np.array(op.get('std', [0.5, 0.5, 0.5]), dtype=np.float32)
                img = (img / 255.0 - mean) / std
        img = img.transpose((2, 0, 1))
        input_data = np.expand_dims(img, axis=0)
        return input_data.astype('float32')

    def predict(self, image_path):
        input_data = self.preprocess(image_path)
        input_names = self.predictor.get_input_names()
        input_handle = self.predictor.get_input_handle(input_names[0])
        input_handle.reshape(input_data.shape)
        input_handle.copy_from_cpu(input_data)
        self.predictor.run()
        output_names = self.predictor.get_output_names()
        output_handle = self.predictor.get_output_handle(output_names[0])
        output_data = output_handle.copy_to_cpu()
        return {'label_map': output_data[0]}


# 其他通用辅助函数
def get_image_sharpness(image_path):
    try:
        img = cv2.imread(image_path);
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return round(cv2.Laplacian(gray_img, cv2.CV_64F).var(), 2)
    except:
        return "N/A"


def get_extended_image_info(image_path):
    try:
        pil_img = Image.open(image_path);
        cv_img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        h, w = cv_img.shape[:2]
        return {"文件名": os.path.basename(image_path), "尺寸": f"{w} x {h}",
                "文件大小(KB)": round(os.path.getsize(image_path) / 1024, 2),
                "打印分辨率(DPI)": pil_img.info.get('dpi', ('N/A', 'N/A'))[0],
                "图像哈希值": str(imagehash.phash(pil_img)), "清晰度评估": get_image_sharpness(image_path)}
    except:
        return {"错误": "计算基础信息出错"}


def get_image_quality_metrics(image_path):
    try:
        img = cv2.imread(image_path);
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return {"平均亮度": round(np.mean(gray_img), 2), "对比度": round(np.std(gray_img), 2)}
    except:
        return {}