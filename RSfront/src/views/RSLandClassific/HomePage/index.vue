<template>
  <div class="app-container">
    <!-- 顶部导航栏 (样式来自第二个模板) -->
    <div class="header">
      <div class="header-left">
        <div class="logo">
          <el-icon class="logo-icon"><Picture /></el-icon>
          <span class="logo-text">遥感地物分割系统</span>
        </div>
      </div>
      <div class="header-right">
        <el-dropdown>
          <span class="user-info">
            <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
            <span>管理员</span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>个人设置</el-dropdown-item>
              <el-dropdown-item>帮助文档</el-dropdown-item>
              <el-dropdown-item divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 主体三栏布局 (样式来自第二个模板) -->
    <div class="main-3col-layout">
      <!-- 左侧面板 (样式来自第二个模板, 逻辑来自第一个) -->
      <div class="side-col left-col">
        <div class="panel type-panel">
          <div class="panel-title">
            <el-icon><DataAnalysis /></el-icon>
            分类统计
          </div>
          <div v-if="detectionMetrics && detectionMetrics.length > 0" class="class-types-list">
            <div 
              v-for="item in detectionMetrics" 
              :key="item.class_name" 
              class="class-type-item"
              :class="{'is-highlighted': highlightedClassId === item.class_id}"
              @click="toggleHighlight(item.class_id)"
            >
              <div class="class-type-color" :style="{ backgroundColor: item.color }"></div>
              <div class="class-type-info">
                <div class="class-type-name">{{ item.class_name }}</div>
                <div class="class-type-area">{{ item.area_m2 }} m²</div>
              </div>
              <div class="class-type-percent">{{ item.percentage }}%</div>
            </div>
          </div>
          <el-empty v-else description="暂无分类统计" />
        </div>

        <div class="panel history-panel">
          <div class="panel-title"><el-icon><Histogram /></el-icon>历史记录</div>
          <div class="history-list">
            <div v-if="historyList.length > 0">
              <div class="history-item" v-for="(record, index) in historyList" :key="record.id">
                <div class="history-info">
                  <div class="history-desc">{{ record.task_type }} - #{{ historyList.length - index }}</div>
                  <div class="history-time">{{ record.created_at }}</div>
                </div>
                <div class="history-actions">
                  <el-button size="small" type="primary" plain @click="viewRecord(record)">查看</el-button>
                  <el-button size="small" type="danger" plain @click="deleteRecord(record.id)">删除</el-button>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无历史记录" />
          </div>
        </div>
      </div>

      <!-- 中间主检测区 (样式来自第二个模板, 逻辑来自第一个) -->
      <div class="center-col">
        <div class="maindetect">
            <div class="upload-wrapper">
                <div class="upload-box">
                    <h4 class="h4t"><el-icon><Picture /></el-icon>遥感影像上传</h4>
                    <el-upload list-type="picture-card" :limit="1" :on-change="handleFileChange" :file-list="fileList" :auto-upload="false">
                        <el-icon><Plus /></el-icon>
                    </el-upload>
                </div>
                <div v-if="uploadMetrics" class="upload-metrics-display">
                    <el-descriptions title="影像基础指标" :column="1" border size="small">
                    <el-descriptions-item v-for="(value, key) in uploadMetrics" :key="key" :label="key">{{ value }}</el-descriptions-item>
                    </el-descriptions>
                </div>
            </div>
          
            <div class="result-image-grid" :class="{ 'is-overlay-mode': showOverlay }">
                <figure class="image-figure base-image-figure">
                    <el-image :src="originalImageUrl" fit="contain" class="base-image" :preview-src-list="[originalImageUrl]"/>
                    <figcaption>原图</figcaption>
                </figure>
                <figure class="image-figure result-image-figure">
                    <el-image v-if="resultImageUrl" :src="resultImageUrl" fit="contain" class="result-image" :preview-src-list="[resultImageUrl]"/>
                    <!-- Canvas 用于高亮显示 -->
                    <canvas ref="highlightCanvas" class="highlight-canvas"></canvas>
                    <figcaption>分割结果</figcaption>
                    <el-empty v-if="!resultImageUrl" description="暂无分割结果" class="result-empty"/>
                </figure>
            </div>
        </div>
      </div>

      <!-- 右侧面板 (样式来自第二个模板, 逻辑来自第一个) -->
      <div class="side-col right-col">
        <div class="panel settings-panel">
            <div class="panel-title">
                <el-icon><Setting /></el-icon>
                操作与设置
            </div>
            <div class="settings-form">
                <el-form label-position="top" size="small">
                    <el-form-item label="算法选择">
                        <el-select v-model="modelSelection" placeholder="选择模型" style="width: 100%"><el-option label="PP-LiteSeg" value="ppliteseg"></el-option></el-select>
                    </el-form-item>
                    <el-form-item label="置信度阈值">
                        <el-slider v-model="confidenceThreshold" :min="0" :max="1" :step="0.1" show-input />
                    </el-form-item>
                    <el-form-item label="结果叠加模式">
                         <el-switch v-model="showOverlay" :disabled="!resultImageUrl" />
                    </el-form-item>
                </el-form>
                 <el-button class="uploadimg" @click="startClassification" :loading="isLoading" :disabled="isLoading || !fileList.length">
                    <el-icon v-if="!isLoading"><CaretRight /></el-icon>
                    {{ isLoading ? '分割中...' : '开始分割' }}
                </el-button>
            </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
import type { UploadFile } from 'element-plus';
import { Plus, Picture, DataAnalysis, Histogram, Setting, CaretRight } from '@element-plus/icons-vue';
import axios from 'axios';

// --- 状态变量定义 (逻辑来自第一个) ---
const fileList = ref<UploadFile[]>([]);
const originalImageUrl = ref('');
const resultImageUrl = ref('');
const isLoading = ref(false);
const serverPath = ref('');
const uploadMetrics = ref<Record<string, any> | null>(null);
const detectionMetrics = ref<any[] | null>(null);
const historyList = ref<any[]>([]);
const showOverlay = ref(false);
const modelSelection = ref('ppliteseg');
const confidenceThreshold = ref(0.5);

const rawLabelMap = ref<{ data: number[][], width: number, height: number } | null>(null);
const highlightedClassId = ref<number | null>(null);
const highlightCanvas = ref<HTMLCanvasElement | null>(null);

// --- 核心功能函数 (逻辑来自第一个) ---

const toggleHighlight = (classId: number) => {
    highlightedClassId.value = highlightedClassId.value === classId ? null : classId;
};

const drawHighlight = () => {
    const canvas = highlightCanvas.value;
    const mapData = rawLabelMap.value;
    if (!canvas || !mapData || !mapData.data) {
        if(canvas) {
            const ctx = canvas.getContext('2d');
            ctx?.clearRect(0, 0, canvas.width, canvas.height);
        }
        return;
    };

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { data, width, height } = mapData;
    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    if (highlightedClassId.value === null) return;

    // 创建一个图像数据对象，这样可以一次性操作所有像素，性能远高于循环调用fillRect
    const imageData = ctx.createImageData(width, height);
    const pixels = imageData.data; // pixels 是一个一维数组 [R,G,B,A, R,G,B,A, ...]

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const index = (y * width + x) * 4;
            if (data[y][x] === highlightedClassId.value) {
                // 半透明黄色
                pixels[index] = 255;     // R
                pixels[index + 1] = 255; // G
                pixels[index + 2] = 0;   // B
                pixels[index + 3] = 128; // A (0-255)
            } else {
                // 半透明黑色
                pixels[index] = 0;       // R
                pixels[index + 1] = 0;   // G
                pixels[index + 2] = 0;   // B
                pixels[index + 3] = 153; // A
            }
        }
    }
    // 将修改后的像素数据一次性绘制回canvas
    ctx.putImageData(imageData, 0, 0);
};

watch(highlightedClassId, drawHighlight);
watch(rawLabelMap, drawHighlight);

const handleFileChange = async (file: UploadFile) => {
  fileList.value = [file];
  originalImageUrl.value = URL.createObjectURL(file.raw!);
  resultImageUrl.value = '';
  detectionMetrics.value = null;
  uploadMetrics.value = null;
  highlightedClassId.value = null;
  rawLabelMap.value = null;

  const formData = new FormData();
  formData.append('file', file.raw!);
  try {
    const response = await axios.post('http://127.0.0.1:5000/api/land_segmentation/upload_and_analyze_single', formData);
    uploadMetrics.value = response.data.metrics;
    serverPath.value = response.data.path;
  } catch (error) { ElMessage.error('量化指标分析失败!'); }
};

const startClassification = async () => {
  if (!fileList.value[0]) return ElMessage.warning('请先上传一张图片。');
  isLoading.value = true;
  highlightedClassId.value = null;
  rawLabelMap.value = null;

  const formData = new FormData();
  formData.append('file', fileList.value[0].raw!);
  formData.append('threshold', confidenceThreshold.value.toString());
  formData.append('model', modelSelection.value);
  try {
    const response = await axios.post('http://127.0.0.1:5000/api/land_segmentation/predict', formData, {
        headers: {'Content-Type': 'multipart/form-data'}
    });
    resultImageUrl.value = response.data.result_url;
    detectionMetrics.value = response.data.detection_metrics;
    rawLabelMap.value = response.data.raw_label_map;
    fetchHistory();
    ElMessage.success('地物分割成功!');
  } catch (error) {
    ElMessage.error('分割失败!');
  } finally {
    isLoading.value = false;
  }
};

const fetchHistory = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:5000/api/history/');
    historyList.value = response.data.filter(r => r.task_type === '地物分割').reverse();
  } catch (error) { ElMessage.error('获取历史记录失败'); }
};

const viewRecord = (record: any) => {
  if (!record) return;
  const host = 'http://127.0.0.1:5000/';
  originalImageUrl.value = host + record.before_image_url;
  resultImageUrl.value = record.result_url;
  highlightedClassId.value = null;
  rawLabelMap.value = null; // 历史记录不包含高亮信息

  if (record.detection_metrics_json) {
    detectionMetrics.value = JSON.parse(record.detection_metrics_json);
  }
  ElMessage.success(`已加载历史记录`);
};

const deleteRecord = async (id: number) => {
  try {
    await axios.delete(`http://127.0.0.1:5000/api/history/${id}`);
    ElMessage.success('删除成功');
    fetchHistory();
  } catch (error) { ElMessage.error('删除失败'); }
};

onMounted(fetchHistory);

</script>

<style scoped>
/* --- 样式来自第二个模板，并为第一个模板的功能做了适配 --- */
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.header {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e1e8ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.header-left .logo { display: flex; align-items: center; gap: 10px; }
.logo-icon { font-size: 24px; color: #409eff; }
.logo-text { font-size: 18px; font-weight: 600; color: #2c3e50; }
.header-right .user-info { display: flex; align-items: center; gap: 8px; cursor: pointer; }

.main-3col-layout {
  flex: 1;
  display: flex;
  gap: 24px;
  padding: 24px;
  overflow: hidden;
}

.side-col {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 22%;
  min-width: 280px;
  flex-shrink: 0;
}
.center-col {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}
.panel {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
}

.type-panel, .history-panel {
    flex-shrink: 0;
    overflow: hidden;
}
.history-panel { flex: 1; }

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e1e8ed;
}

/* 左侧-分类统计 */
.class-types-list {
  overflow-y: auto;
  margin-right: -16px;
  padding-right: 16px;
}
.class-type-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.class-type-item:hover { background-color: #f5f7fa; }
.class-type-item.is-highlighted { background-color: #ecf5ff; }

.class-type-color {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  flex-shrink: 0;
}
.class-type-info { flex-grow: 1; }
.class-type-name { font-size: 14px; color: #303133; }
.class-type-area { font-size: 12px; color: #909399; }
.class-type-percent { font-size: 14px; font-weight: 500; color: #409eff; }

/* 左侧-历史记录 */
.history-list {
    flex: 1;
    overflow-y: auto;
    margin-right: -16px;
    padding-right: 16px;
}
.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border-radius: 6px;
}
.history-desc { font-size: 14px; font-weight: 500; color: #303133; }
.history-time { font-size: 12px; color: #909399; margin-top: 4px; }
.history-actions { display: flex; gap: 8px; }

/* 中间 */
.maindetect {
  width: 100%;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.upload-wrapper {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  flex-shrink: 0;
}
.upload-box { text-align: center; }
.h4t {
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #2c3e50;
  font-weight: 600;
}
.upload-metrics-display {
    flex: 1;
}

.result-image-grid {
  flex-grow: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  height: 100%;
  min-height: 300px;
}
.image-figure {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background-color: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  position: relative;
  overflow: hidden;
}
.image-figure figcaption {
    text-align: center;
    font-size: 14px;
    color: #606266;
    padding-bottom: 8px;
}
.el-image, .highlight-canvas, .result-empty {
    width: 100%;
    flex-grow: 1;
}

/* 高亮和叠加的核心样式 */
.result-image-figure { position: relative; }
.highlight-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    pointer-events: none; /* 允许鼠标事件穿透 */
    z-index: 2;
}
.result-image-figure .result-image {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    z-index: 1;
}

/* 叠加模式 */
.result-image-grid.is-overlay-mode {
  grid-template-columns: 1fr; /* 变成单列 */
}
.result-image-grid.is-overlay-mode .base-image-figure {
    grid-row: 1;
    grid-column: 1;
    z-index: 0;
}
.result-image-grid.is-overlay-mode .result-image-figure {
    grid-row: 1;
    grid-column: 1;
    z-index: 1;
    background: transparent;
    border: none;
}
.result-image-grid.is-overlay-mode .result-image {
    opacity: 0.6; /* 让分割结果半透明 */
}


/* 右侧 */
.settings-panel {
    display: flex;
    flex-direction: column;
}
.settings-form {
    padding-top: 10px;
    display: flex;
    flex-direction: column;
    flex: 1;
}
.settings-form .el-form {
    flex-grow: 1;
}
.el-form-item { margin-bottom: 20px; }

.uploadimg {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff 0%, #79bbff 100%);
  border: none;
  color: white;
  font-weight: 600;
  transition: all 0.3s ease;
  margin-top: auto; /* 关键：将按钮推到底部 */
}
.uploadimg:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(64, 158, 255, 0.3);
}
.uploadimg:disabled {
    background: #c8c9cc;
    box-shadow: none;
    transform: none;
    cursor: not-allowed;
}

</style>