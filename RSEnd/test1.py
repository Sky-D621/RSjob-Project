# 文件名: test1.py (最终验证版)

import paddlers as pdrs
from paddlers import transforms as T
import numpy as np
import random  # 确保导入 random

# 1. 创建包含我们新算子的数据变换组合
my_transforms = T.Compose([
    T.ToGrayScale(prob=1.0)
])
print("Compose with new operator created.")

# 2. 创建一个假的彩色图片（用Numpy数组模拟）
fake_color_image = np.random.randint(0, 256, size=(100, 100, 3), dtype=np.uint8)
print(f"\n创建了一张假的彩色图片，形状为: {fake_color_image.shape}")

# 3. 把假图片包装成paddlers期望的sample格式（一个字典）
sample = {'image': fake_color_image}

# 4. 调用新算子进行处理
print("\n正在用新算子处理图片...")
result_tuple = my_transforms(sample)
print("处理完成！")

# 从元组和字典中取出最终的图片
transformed_image = result_tuple[0]['image']

# 5. 检查结果 (使用CHW格式的尺子)
print(f"\n处理后图片的形状为: {transformed_image.shape}")

# ✅✅✅ 关键修正在这里！✅✅✅
# 我们现在按照 CHW 格式 (通道, 高, 宽) 来检查
if len(transformed_image.shape) == 3 and transformed_image.shape[0] == 3:
    print("✅ 形状符合CHW格式 (3, H, W)。正在检查内容...")

    # 检查灰度图特性：三个通道的内容应该完全一样
    channel1, channel2, channel3 = transformed_image[0], transformed_image[1], transformed_image[2]
    if np.all(channel1 == channel2) and np.all(channel1 == channel3):
        print("✅✅✅ 最终验证成功！图片已被正确转换为CHW格式的三通道灰度图。")
    else:
        print("❌ 验证失败！图片虽然是CHW格式，但内容不是灰度图。")
else:
    print(f"❌ 验证失败！处理后的图片形状 {transformed_image.shape} 不符合期望的CHW格式(3, H, W)。")