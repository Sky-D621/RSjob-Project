<template>
  <div class="app-container">
    <!-- 顶部导航栏 (样式来自第二个模板) -->
    <div class="header">
      <div class="header-left">
        <div class="logo">
          <el-icon class="logo-icon"><Picture /></el-icon>
          <span class="logo-text">遥感目标检测系统</span>
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
            检测统计
          </div>
          <div class="statistics-cards">
             <div class="stat-card">
                <div>
                    <div class="stat-value">{{ detectionMetrics?.['检测总数'] || '0' }}</div>
                    <div class="stat-label">检测总数</div>
                </div>
            </div>
          </div>
           <div v-if="detectionMetrics?.['各类别数量']" class="class-types-list">
            <div 
              v-for="(count, category) in detectionMetrics['各类别数量']" 
              :key="category" 
              class="class-type-item"
              :class="{'is-highlighted': highlightedCategory === category}"
              @click="toggleHighlight(category)"
            >
              <div class="class-type-info">
                <div class="class-type-name">{{ category }}</div>
              </div>
              <div class="class-type-count">{{ count }} 个</div>
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
                <figure class="image-figure result-image-figure" ref="resultFigureRef">
                    <el-image v-if="resultImageUrl" :src="resultImageUrl" fit="contain" class="result-image" :preview-src-list="[resultImageUrl]"/>
                    <!-- Canvas 用于高亮显示 -->
                    <canvas ref="highlightCanvas" class="highlight-canvas"></canvas>
                    <figcaption>检测结果</figcaption>
                    <el-empty v-if="!resultImageUrl" description="暂无检测结果" class="result-empty"/>
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
                    <el-form-item label="叠加显示检测框">
                         <el-switch v-model="showOverlay" :disabled="!resultImageUrl" />
                    </el-form-item>
                </el-form>
                 <el-button class="uploadimg" @click="startDetection" :loading="isLoading" :disabled="isLoading || !fileList.length">
                    <el-icon v-if="!isLoading"><CaretRight /></el-icon>
                    {{ isLoading ? '检测中...' : '开始检测' }}
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
const detectionMetrics = ref<Record<string, any> | null>(null);
const historyList = ref<any[]>([]);
const showOverlay = ref(true); // 默认开启叠加

const rawResults = ref<any[] | null>(null);
const highlightedCategory = ref<string | null>(null);
const highlightCanvas = ref<HTMLCanvasElement | null>(null);
const resultFigureRef = ref<HTMLElement | null>(null); // Ref for the result image container

// --- 核心功能函数 (逻辑来自第一个) ---

const handleFileChange = async (file: UploadFile) => {
  fileList.value = [file];
  originalImageUrl.value = URL.createObjectURL(file.raw!);
  resultImageUrl.value = '';
  detectionMetrics.value = null;
  uploadMetrics.value = null;
  rawResults.value = null;
  highlightedCategory.value = null;

  const formData = new FormData();
  formData.append('file', file.raw!);
  try {
    const response = await axios.post('http://127.0.0.1:5000/api/object_detection/upload_and_analyze_single', formData);
    uploadMetrics.value = response.data.metrics;
    serverPath.value = response.data.path;
  } catch (error) { ElMessage.error('量化指标分析失败!'); }
};

const startDetection = async () => {
  if (!serverPath.value) {
    return ElMessage.warning('请先上传图片并等待指标分析完成。');
  }
  isLoading.value = true;
  try {
    const response = await axios.post(
      'http://127.0.0.1:5000/api/object_detection/predict',
      { path: serverPath.value },
      { headers: { 'Content-Type': 'application/json' } }
    );
    resultImageUrl.value = response.data.result_url;
    detectionMetrics.value = response.data.detection_metrics;
    rawResults.value = response.data.raw_results;
    fetchHistory();
    ElMessage.success('目标检测成功!');
  } catch (error) { 
    ElMessage.error('检测失败!'); 
  } finally { 
    isLoading.value = false; 
  }
};

const fetchHistory = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:5000/api/history/');
    historyList.value = response.data.filter(r => r.task_type === '目标检测').reverse();
  } catch (error) { ElMessage.error('获取历史记录失败'); }
};

const viewRecord = (record: any) => {
  if (!record) return;
  const host = 'http://127.0.0.1:5000/';
  originalImageUrl.value = host + record.before_image_url;
  resultImageUrl.value = record.result_url;
  rawResults.value = null; // 历史记录不包含高亮信息
  highlightedCategory.value = null;

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

const toggleHighlight = (category: string) => {
    highlightedCategory.value = (highlightedCategory.value === category) ? null : category;
};

const drawHighlight = () => {
    const canvas = highlightCanvas.value;
    const results = rawResults.value;
    const container = resultFigureRef.value;
    if (!container) return;
    
    // 使用容器内的 el-image 元素来获取尺寸
    const imgEle = container.querySelector('.el-image__inner') as HTMLImageElement;

    if (!canvas || !results || !imgEle || !imgEle.complete || imgEle.naturalWidth === 0) {
        if(canvas) canvas.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 按图片在容器中的实际显示尺寸来设置 canvas 尺寸
    canvas.width = imgEle.width;
    canvas.height = imgEle.height;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!highlightedCategory.value) return;

    // 计算缩放比例
    const scaleX = imgEle.width / imgEle.naturalWidth;
    const scaleY = imgEle.height / imgEle.naturalHeight;

    // 绘制半透明黑色蒙版
    ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 将高亮的类别区域“抠”出来
    results.forEach(item => {
        if (item.category === highlightedCategory.value) {
            const [x, y, w, h] = item.bbox;
            // 应用缩放
            ctx.clearRect(x * scaleX, y * scaleY, w * scaleX, h * scaleY);
        }
    });
};

watch(highlightedCategory, drawHighlight);
// 当结果图 URL 变化时，等待图片加载完毕再绘制
watch(resultImageUrl, (newUrl) => {
  if (newUrl) {
    const img = new Image();
    img.src = newUrl;
    img.onload = () => {
      // 使用 requestAnimationFrame 确保在下一次浏览器重绘前执行
      requestAnimationFrame(drawHighlight);
    };
  } else {
     drawHighlight(); // 清空画布
  }
});

onMounted(() => {
    fetchHistory();
    // 监听窗口大小变化，重新绘制高亮，以保证响应式
    window.addEventListener('resize', drawHighlight);
});

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

/* 左侧-统计 */
.statistics-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  display: flex;
  align-items: center;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.stat-value { font-size: 22px; font-weight: bold; color: #409eff; }
.stat-label { font-size: 13px; color: #606266; margin-top: 4px; }

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

.class-type-info { flex-grow: 1; }
.class-type-name { font-size: 14px; font-weight: 500; color: #303133; }
.class-type-count { font-size: 14px; color: #606266; }


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
.upload-metrics-display { flex: 1; }

.result-image-grid {
  flex-grow: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
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
.highlight-canvas, .result-image {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
}
.result-image { z-index: 1; pointer-events: none; }
.highlight-canvas { z-index: 2; pointer-events: none; }


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
    opacity: 1; /* 叠加时检测结果图不透明 */
}

/* 右侧 */
.settings-panel { display: flex; flex-direction: column; }
.settings-form {
    padding-top: 10px;
    display: flex;
    flex-direction: column;
    flex: 1;
}
.settings-form .el-form { flex-grow: 1; }
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
  margin-top: auto; /* 将按钮推到底部 */
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