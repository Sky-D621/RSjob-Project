
import numpy as np
from PIL import Image
from paddlers.deploy import Predictor

# 实验路径。实验目录下保存输出的模型权重和结果
EXP_DIR = './models/rscd/'
# 数据集路径

predictor = Predictor("./models/rscd/", use_gpu=True)

fileA="./static/images/12345/A/train_9.png"
fileB="./static/images/12345/B/train_9.png"


res = predictor.predict((fileA, fileB))


label_map =res['label_map']
# 转换为二值图像：大于0.5的设置为255，否则为0
binary_map = (label_map > 0.5).astype(np.uint8) * 255

# 将numpy数组转换为PIL图像以便保存
binary_image = Image.fromarray(binary_map)
# 保存二值图像到本地，这里以'binary_image.png'为例，您可以自行修改文件名
binary_image.save('./output/out.png')

print("二值图像已成功保存至本地。")