import os
import numpy as np
from PIL import Image
from paddlers.deploy import Predictor

def test_model_loading():
    """
    测试模型加载功能
    """
    try:
        # 获取模型绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_dir = os.path.join(current_dir, "models", "rscd")
        
        print(f"尝试加载模型，路径: {model_dir}")
        predictor = Predictor(model_dir, use_gpu=False)  # 默认使用CPU
        print("模型加载成功!")
        return predictor
    except Exception as e:
        print(f"模型加载失败: {str(e)}")
        return None

def test_prediction(predictor, image_a_path, image_b_path):
    """
    测试模型预测功能
    """
    if predictor is None:
        print("预测器未初始化，无法进行预测")
        return
    
    try:
        # 检查文件是否存在
        if not os.path.exists(image_a_path):
            print(f"图像A不存在: {image_a_path}")
            return
        if not os.path.exists(image_b_path):
            print(f"图像B不存在: {image_b_path}")
            return
            
        print(f"开始预测，输入图像A: {image_a_path}")
        print(f"开始预测，输入图像B: {image_b_path}")
        
        # 执行预测
        result = predictor.predict((image_a_path, image_b_path))
        
        # 处理预测结果
        label_map = result['label_map']
        print(f"预测完成，结果形状: {label_map.shape}")
        
        # 保存结果为图像
        binary_map = (label_map > 0.5).astype(np.uint8) * 255
        binary_image = Image.fromarray(binary_map)
        
        # 保存结果
        output_path = "test_result.png"
        binary_image.save(output_path)
        print(f"结果已保存至: {output_path}")
        
    except Exception as e:
        print(f"预测过程发生错误: {str(e)}")

if __name__ == "__main__":
    # 测试模型加载
    predictor = test_model_loading()
    
    # 如果有测试图像，可以取消下面的注释进行测试
    # 请将路径替换为实际的测试图像路径
    '''
    test_image_a = "./static/images/test/A/test_image.jpg"
    test_image_b = "./static/images/test/B/test_image.jpg"
    test_prediction(predictor, test_image_a, test_image_b)
    '''
    
    print("\n如需测试预测功能，请修改脚本中的测试图像路径并取消注释")