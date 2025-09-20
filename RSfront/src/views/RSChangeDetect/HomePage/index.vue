<template>
  <div class="app-container">
    <!-- 顶部导航栏 (样式来自第二个模板) -->
    <div class="header">
      <div class="header-left">
        <div class="logo">
          <el-icon class="logo-icon"><Picture /></el-icon>
          <span class="logo-text">遥感变化检测系统</span>
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
        <div class="panel stat-panel">
          <div class="panel-title">
            <el-icon><DataAnalysis /></el-icon>
            检测统计
          </div>
          <div class="statistics-cards">
            <div class="stat-card">
              <div>
                <div class="stat-value">{{ metrics.detectionMetrics?.change_area_km2 || '0.00' }}</div>
                <div class="stat-label">变化面积 (km²)</div>
              </div>
            </div>
            <div class="stat-card">
              <div>
                <div class="stat-value">{{ metrics.detectionMetrics?.change_rate || '0.00' }}%</div>
                <div class="stat-label">变化率</div>
              </div>
            </div>
          </div>
        </div>
        <div class="panel history-panel">
          <div class="panel-title">
            <el-icon><Histogram /></el-icon>
            历史记录
          </div>
          <div class="history-list">
            <div v-if="historyList.length > 0">
              <div v-for="(record, index) in historyList" :key="record.id" class="history-item">
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
          <div class="toptool">
            <div class="upload-area before">
              <h4 class="h4t"><el-icon><Picture /></el-icon>前时相影像</h4>
              <el-upload list-type="picture-card" :limit="1" :on-change="handleChangesbefore" :file-list="fileListbefore" :auto-upload="false">
                <el-icon><Plus /></el-icon>
              </el-upload>
            </div>
            <div class="upload-area after">
              <h4 class="h4t"><el-icon><Picture /></el-icon>后时相影像</h4>
              <el-upload list-type="picture-card" :limit="1" :on-change="handleChangesafter" :file-list="fileListafter" :auto-upload="false">
                <el-icon><Plus /></el-icon>
              </el-upload>
            </div>
          </div>
          <div class="detectchange">
            <el-button class="uploadimg" @click="startDetection" :loading="isDetecting" :disabled="isDetecting || !fileListbefore.length || !fileListafter.length">
              <el-icon v-if="!isDetecting"><CaretRight /></el-icon>
              {{ isDetecting ? '检测中...' : '开始检测' }}
            </el-button>
          </div>
          <div class="detectmain compare-slider">
            <div v-if="srcbefore && srcafter" class="compare-container full-width">
               <VueCompareImage
                  :leftImage="srcbefore"
                  :rightImage="srcafter"
                  leftImageLabel="前时相"
                  rightImageLabel="后时相"
                />
            </div>
            <div v-else class="detect-result-placeholder-block">
                请上传前后时相影像并开始检测
            </div>
            <div v-if="srcdetect" class="detect-result-block">
              <h4>检测结果</h4>
              <div @click="handleDetectResultPreview" class="detect-result-clickable">
                <el-image :src="srcdetect" class="detect-result-img-block" fit="contain" :preview-src-list="resultPreviewList" :initial-index="2" />
                <div class="detect-result-overlay">
                  <el-icon class="zoom-icon"><ZoomIn /></el-icon>
                  <span>点击放大</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧面板 (样式来自第二个模板, 逻辑来自第一个) -->
      <div class="side-col right-col">
        <div class="panel settings-panel">
            <div class="panel-title">
                <el-icon><Setting /></el-icon>
                检测设置
            </div>
            <div class="settings-form">
                <el-form label-position="top" size="small">
                <el-form-item label="算法选择">
                    <el-select placeholder="选择模型" style="width: 100%"><el-option label="BIT模型" value="bit"></el-option></el-select>
                </el-form-item>
                </el-form>
            </div>
        </div>
        <div class="panel metrics-panel">
            <div class="panel-title">
                <el-icon><DataLine /></el-icon>
                量化指标
            </div>
            <div v-if="metrics.imageA" class="metrics-display">
              <el-descriptions title="影像A指标" :column="1" border size="small">
                <el-descriptions-item v-for="(value, key) in metrics.imageA" :key="key" :label="key">{{ value }}</el-descriptions-item>
              </el-descriptions>
              <el-descriptions title="影像B指标" :column="1" border size="small">
                <el-descriptions-item v-for="(value, key) in metrics.imageB" :key="key" :label="key">{{ value }}</el-descriptions-item>
              </el-descriptions>
              <el-descriptions title="差异性指标" :column="1" border size="small">
                 <el-descriptions-item v-for="(value, key) in metrics.differenceMetrics" :key="key" :label="key">{{ value }}</el-descriptions-item>
              </el-descriptions>
           </div>
           <el-empty v-else description="暂无量化指标" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import type { UploadFile } from 'element-plus';
import { Plus, Picture, CaretRight, DataAnalysis, Histogram, Setting, ZoomIn, DataLine } from '@element-plus/icons-vue';
import axios from 'axios';
import { VueCompareImage } from 'vue3-compare-image'; // 使用第二个模板的对比组件

// --- 状态变量定义 (逻辑来自第一个) ---
const fileListbefore = ref<UploadFile[]>([]);
const fileListafter = ref<UploadFile[]>([]);
const srcbefore = ref('');
const srcafter = ref('');
const srcdetect = ref('');
const historyList = ref<any[]>([]); // 明确类型
const resultPreviewList = computed(() => {
  return [srcbefore.value, srcafter.value, srcdetect.value].filter(url => url);
});
const detectResultDialogVisible = ref(false);

const metrics = reactive<{
  imageA: Record<string, any> | null;
  imageB: Record<string, any> | null;
  differenceMetrics: Record<string, any> | null;
  detectionMetrics: Record<string, any> | null;
}>({ imageA: null, imageB: null, differenceMetrics: null, detectionMetrics: null });

const serverPaths = reactive({ path_a: '', path_b: '' });
const isLoadingMetrics = ref(false);
const isDetecting = ref(false);

// --- 核心功能函数 (逻辑来自第一个) ---
const handleFileUploadAndAnalysis = async () => {
  if (fileListbefore.value.length === 0 || fileListafter.value.length === 0) return;
  
  // 重置状态
  Object.assign(metrics, { imageA: null, imageB: null, differenceMetrics: null, detectionMetrics: null });
  Object.assign(serverPaths, { path_a: '', path_b: '' });
  srcdetect.value = '';

  isLoadingMetrics.value = true;
  const formData = new FormData();
  formData.append('image_a', fileListbefore.value[0].raw!);
  formData.append('image_b', fileListafter.value[0].raw!);

  try {
    const response = await axios.post('http://127.0.0.1:5000/api/change_detection/upload_and_analyze_metrics', formData);
    Object.assign(metrics, response.data.metrics);
    Object.assign(serverPaths, response.data.paths);
    ElMessage.success('图片上传并分析成功!');
  } catch (error) {
    ElMessage.error('图片上传或分析失败!');
  } finally {
    isLoadingMetrics.value = false;
  }
};

const startDetection = async () => {
  if (!serverPaths.path_a || !serverPaths.path_b) {
    return ElMessage.warning('请先成功上传两张图片。');
  }
  isDetecting.value = true;
  srcbefore.value = URL.createObjectURL(fileListbefore.value[0].raw!);
  srcafter.value = URL.createObjectURL(fileListafter.value[0].raw!);

  try {
    const response = await axios.post('http://127.0.0.1:5000/api/change_detection/predict', {
      path_a: serverPaths.path_a,
      path_b: serverPaths.path_b
    });
    srcdetect.value = response.data.result_url;
    metrics.detectionMetrics = response.data.detection_metrics;
    fetchHistory();
    ElMessage.success('变化检测完成!');
  } catch (error) {
    ElMessage.error('检测失败!');
  } finally {
    isDetecting.value = false;
  }
};

const handleChangesbefore = (file: UploadFile) => {
  fileListbefore.value = [file];
  handleFileUploadAndAnalysis();
};
const handleChangesafter = (file: UploadFile) => {
  fileListafter.value = [file];
  handleFileUploadAndAnalysis();
};

const fetchHistory = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:5000/api/history/');
    // 将最新的记录放在最前面
    historyList.value = response.data.reverse();
  } catch (error) {
    ElMessage.error('获取历史记录失败');
  }
};

const deleteRecord = async (id: number) => {
  try {
    await axios.delete(`http://127.0.0.1:5000/api/history/${id}`);
    ElMessage.success('删除成功');
    fetchHistory();
  } catch (error) {
    ElMessage.error('删除失败');
  }
};

const viewRecord = (record: any) => {
  if (!record) return;

  const host = 'http://127.0.0.1:5000/';
  srcbefore.value = host + record.before_image_url;
  srcafter.value = host + record.after_image_url;
  srcdetect.value = record.result_url;

  if (record.detection_metrics_json) {
    metrics.detectionMetrics = JSON.parse(record.detection_metrics_json);
  } else {
    metrics.detectionMetrics = null; // 清空旧数据
  }
  
  // 清空量化指标，因为历史记录里没有这项
  metrics.imageA = null;
  metrics.imageB = null;
  metrics.differenceMetrics = null;


  ElMessage.success(`已加载历史记录`);
};

// 新增功能：点击检测结果图片时的处理函数 (来自第二个模板)
const handleDetectResultPreview = () => {
    // 使用 El-Image 的 preview-src-list 功能，此函数可留空或用于其他逻辑
    // 例如：detectResultDialogVisible.value = true;
};

onMounted(() => {
  fetchHistory();
});
</script>
  
<style scoped>
/* --- 样式完全来自第二个模板，并做微调 --- */
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.header {
  height: 60px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid #e1e8ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.header-left .logo {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo-icon {
  font-size: 24px;
  color: #409eff;
}
.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}
.header-right .user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.main-3col-layout {
  flex: 1;
  display: flex;
  flex-direction: row;
  justify-content: center;
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
  align-items: center;
}

.panel {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
}
.history-panel, .metrics-panel {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
.history-list, .metrics-display {
    overflow-y: auto;
    margin-right: -16px;
    padding-right: 16px;
}


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
}
.stat-card {
  display: flex;
  align-items: center;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.stat-value {
  font-size: 22px;
  font-weight: bold;
  color: #409eff;
}
.stat-label {
  font-size: 13px;
  color: #606266;
  margin-top: 4px;
}

/* 左侧-历史记录 */
.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border-radius: 6px;
  transition: all 0.2s ease;
}
.history-item:hover {
  background: #f0f2f5;
}
.history-desc {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}
.history-time {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.history-actions {
    display: flex;
    gap: 8px;
}

/* 中间 */
.maindetect {
  width: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}
.toptool {
  width: 100%;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  gap: 20px;
}
.upload-area {
    flex: 1;
    text-align: center;
}
.h4t {
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #2c3e50;
  font-weight: 600;
}
.detectchange {
    width: 100%;
}
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

.compare-slider {
  width: 100%;
}
.compare-container.full-width {
  width: 100%;
  aspect-ratio: 1/1; /* 保持1:1的比例 */
  background: #f5f7fa;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: center;
}
.detect-result-block {
  width: 100%;
  margin-top: 18px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.detect-result-block h4 {
  margin: 0 0 12px 0;
  color: #409eff;
  font-size: 16px;
  font-weight: 600;
}
.detect-result-img-block {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 6px;
}
.detect-result-placeholder-block {
  width: 100%;
  aspect-ratio: 1/1;
  color: #909399;
  text-align: center;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}
.detect-result-clickable {
  position: relative;
  cursor: pointer;
}
.detect-result-clickable:hover .detect-result-overlay {
  opacity: 1;
}
.detect-result-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
  color: white;
}
.zoom-icon {
  font-size: 24px;
  margin-bottom: 4px;
}

/* 右侧 */
.settings-form {
  padding-top: 10px;
}
.metrics-display .el-descriptions {
    margin-bottom: 16px;
}
.metrics-display .el-descriptions:last-child {
    margin-bottom: 0;
}
</style>