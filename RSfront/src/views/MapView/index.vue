<template>
  <div class="map-page-container">
    <div class="map-wrapper">
      <!-- 【最终版】ref 的名字和 script 中保持一致 -->
      <l-map
        ref="mapRef"
        v-model:zoom="zoom"
        v-model:center="center"
        :use-global-leaflet="false"
        @ready="onMapReady"
      >
        <l-control-layers position="topright" @baselayerchange="onLayerChange"></l-control-layers>
        <l-tile-layer 
          :url="activeTimeLapse.before.url" 
          :subdomains="activeTimeLapse.before.subdomains || []"
        ></l-tile-layer>
        <l-tile-layer 
          :url="activeTimeLapse.after.url" 
          :opacity="afterLayerOpacity"
          :subdomains="activeTimeLapse.after.subdomains || []"
        ></l-tile-layer>
        <l-tile-layer
          v-if="labelLayer.visible"
          :url="labelLayer.url"
          :subdomains="labelLayer.subdomains"
          :options="{ zIndex: 500 }" 
        ></l-tile-layer>
      </l-map>
    </div>

    <div class="map-control-panel">
      <!-- 时序影像对比 -->
      <el-card>
        <template #header><h4>时序影像对比</h4></template>
        <div class="timelapse-control">
          <div class="select-row">
            <span class="label">变化前:</span>
            <el-select v-model="activeTimeLapse.before" value-key="name" placeholder="选择影像">
              <el-option v-for="item in timeLapseOptions" :key="item.name" :label="item.name" :value="item" />
            </el-select>
          </div>
          <div class="select-row">
            <span class="label">变化后:</span>
            <el-select v-model="activeTimeLapse.after" value-key="name" placeholder="选择影像">
              <el-option v-for="item in timeLapseOptions" :key="item.name" :label="item.name" :value="item" />
            </el-select>
          </div>
          <div class="slider-row">
            <span class="label">混合预览:</span>
            <el-slider v-model="afterLayerOpacity" :min="0" :max="1" :step="0.05" />
          </div>
        </div>
      </el-card>

      <!-- 分析工具 -->
      <el-card style="margin-top: 20px;">
        <template #header><h4>分析工具</h4></template>
        <p>1. 拉动“混合预览”滑块切换地图。</p>
        <p>2.请在地图上框选感兴趣的区域后，点击下方按钮开始分析。</p>
        <div class="analysis-buttons">
          <el-button @click="triggerAnalysis('road_extraction')" :disabled="!selectedBounds" type="primary">道路提取</el-button>
          <el-button @click="triggerAnalysis('object_detection')" :disabled="!selectedBounds" color="#626aef">目标检测</el-button>
          <el-button @click="triggerAnalysis('land_segmentation')" :disabled="!selectedBounds" color="#E6A23C">地物分类</el-button>
          <el-button @click="triggerAnalysis('change_detection')" :disabled="!selectedBounds" type="danger">变化检测</el-button>
        </div>
        <el-divider />
        
        <!-- 结果展示 -->
        <div v-loading="mapAnalysisState.isLoading">
          <h4>分析结果</h4>
          <div v-if="!selectedBounds && !mapAnalysisState.isLoading && !mapAnalysisState.success">
            <el-alert title="等待操作" type="info" :closable="false" show-icon>请先在地图上框选一个区域。</el-alert>
          </div>
          <div v-if="mapAnalysisState.success">
            <!-- 1. 提示信息：el-alert 只负责显示文字 -->
            <el-alert 
              :title="`${getTaskDisplayName(mapAnalysisState.taskType)} 分析成功`" 
              type="success" 
              :closable="false" 
              :description="mapAnalysisState.taskType === 'land_segmentation' ? '分类结果已叠加在地图上，详情如下。' : '分析结果图如下，详情如下。'"
              show-icon
            ></el-alert>

            <!-- 2. 结果图：el-image 作为 alert 的兄弟元素，独立渲染 -->
            <el-image 
              v-if="mapAnalysisState.taskType !== 'land_segmentation' && mapAnalysisState.result_image_url"
              :src="mapAnalysisState.result_image_url" 
              :preview-src-list="[mapAnalysisState.result_image_url]"
              fit="contain" 
              style="width: 100%; margin-top: 15px; border: 1px solid #eee; border-radius: 4px; background-color: #f9f9f9;"
              lazy
            >
              <template #placeholder>
                <div class="image-slot">加载中<span class="dot">...</span></div>
              </template>
            </el-image>

            <!-- 3. 指标展示：同样作为 alert 的兄弟元素 -->
            <div style="margin-top: 15px;">
              <p><strong>分析指标:</strong></p>
              <el-table 
                v-if="mapAnalysisState.taskType === 'land_segmentation'" 
                :data="mapAnalysisState.metrics" 
                stripe 
                style="width: 100%; margin-top: 10px;"
              >
                <el-table-column prop="地物类别" label="类别" />
                <el-table-column prop="面积(平方米)" label="面积(㎡)" />
                <el-table-column prop="占比(%)" label="占比(%)" />
              </el-table>
              <ul v-else style="margin-top: 10px;">
               <li v-for="(value, key) in mapAnalysisState.metrics" :key="key">
                <template v-if="typeof value === 'object' && value !== null">
                  {{ key }}:
                  <ul><li v-for="(count, category) in value" :key="category">{{ category }}: {{ count }}</li></ul>
                </template>
                <template v-else>{{ key }}: {{ value }}</template>
               </li>
              </ul>
            </div>
          </div>
          <div v-if="mapAnalysisState.error"><el-alert title="分析失败" type="error" :closable="false" show-icon>{{ mapAnalysisState.error }}</el-alert></div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from "vue";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import { LMap, LTileLayer, LControlLayers } from "@vue-leaflet/vue-leaflet";
import L from "leaflet";
import "leaflet-draw";
import { ElMessage } from 'element-plus';
import { MapAnalysisAPI } from '@/services/api';

// --- 1. 图标修复 ---
type D = L.Icon.Default & { _getIconUrl?: string; };
delete (L.Icon.Default.prototype as D)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
});

// --- 2. Refs 和状态 ---
const mapRef = ref<any>(null);
const zoom = ref(13);
const center = ref<[number, number]>([39.9042, 116.4074]);
const selectedBounds = ref<L.LatLngBounds | null>(null);
const currentTileUrl = ref<string>("");

const mapAnalysisState = reactive({
  isLoading: false, success: false, taskType: '', result_image_url: null as string | null,
  metrics: null as any, rawResults: [] as any[], error: null as string | null,
});
const tileLayers = ref([
  { name: "高德街道图", url: "https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}", subdomains: ['1','2','3','4'], visible: true },
  { name: "高德卫星图", url: "https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}", subdomains: ['1','2','3','4'], visible: false },
]);

// --- 3. 地图对象 ---
let leafletMapInstance: L.Map | null = null;
let userDrawLayer: L.FeatureGroup | null = null;
let analysisResultLayer: L.FeatureGroup | null = null;
let segmentationOverlay: L.ImageOverlay | null = null;

// --- 4. onMapReady ---
const onMapReady = (mapObject: L.Map) => {
  leafletMapInstance = mapObject;
  userDrawLayer = new L.FeatureGroup().addTo(leafletMapInstance);
  analysisResultLayer = new L.FeatureGroup().addTo(leafletMapInstance);

  L.Draw.SimpleShape.prototype._getTooltipText = function () {
    return { text: this._endLabelText, subtext: L.drawLocal.draw.handlers.simpleshape.tooltip.end };
  };
  L.Draw.Rectangle.prototype._getTooltipText = L.Draw.SimpleShape.prototype._getTooltipText;

  L.drawLocal.draw.handlers.rectangle.tooltip.start = 'Click and drag to draw a rectangle.';
  L.drawLocal.draw.handlers.simpleshape.tooltip.end = 'Release mouse to finish drawing.';

  const drawControl = new L.Control.Draw({
    edit: { featureGroup: userDrawLayer, remove: true },
    draw: { polygon: false, polyline: false, circle: false, circlemarker: false, marker: false,
      rectangle: { shapeOptions: { color: '#007BFF', weight: 2 } } },
  });
  leafletMapInstance.addControl(drawControl);

  leafletMapInstance.on(L.Draw.Event.CREATED, (event: any) => {
    if (!userDrawLayer) return;
    userDrawLayer.clearLayers();
    analysisResultLayer?.clearLayers();
    userDrawLayer.addLayer(event.layer);
    selectedBounds.value = event.layer.getBounds();
    clearMapAnalysisState();
    ElMessage.info('已选择区域，请点击右侧按钮开始分析。');
  });

  leafletMapInstance.on(L.Draw.Event.DELETED, () => {
    selectedBounds.value = null;
    clearMapAnalysisState();
    userDrawLayer?.clearLayers();
    analysisResultLayer?.clearLayers();
    ElMessage.info('已清除所选区域。');
  });

  currentTileUrl.value = tileLayers.value.find(l => l.visible)?.url || "";
};

// --- 5. 工具函数 ---
const getTaskDisplayName = (taskType: string) => {
  const names: { [key: string]: string } = {
    road_extraction: '道路提取',
    object_detection: '目标检测',
    change_detection: '变化检测',
    land_segmentation: '地物分类',
  };
  return names[taskType] || '分析';
};

const onLayerChange = (event: any) => {
  currentTileUrl.value = tileLayers.value.find(l => l.name === event.name)?.url || "";
};

const clearMapAnalysisState = () => {
  mapAnalysisState.isLoading = false;
  mapAnalysisState.success = false;
  mapAnalysisState.taskType = '';
  mapAnalysisState.result_image_url = null;
  mapAnalysisState.metrics = null;
  mapAnalysisState.rawResults = [];
  mapAnalysisState.error = null;
  analysisResultLayer?.clearLayers();

  if (segmentationOverlay && leafletMapInstance?.hasLayer(segmentationOverlay)) {
    leafletMapInstance.removeLayer(segmentationOverlay);
  }
  segmentationOverlay = null;
};

const timeLapseOptions = ref([
  { name: '高德卫星图', url: 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}', subdomains: ['1','2','3','4'], isLabelLayer: false},
  { name: '天地图卫星图', url: 'https://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=8beef225dfcebca802abe42e58707380', 
  subdomains: ['1','2','3','4', '5', '6', '7'], isLabelLayer: false },
]);

const labelLayer = reactive({
  url: 'https://t{s}.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=你的天地图密钥',
  subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
  visible: true // 默认显示
});

const activeTimeLapse = reactive({ 
  before: timeLapseOptions.value[0], 
  after: timeLapseOptions.value[1] });
const afterLayerOpacity = ref(0.5);

// --- 6. triggerAnalysis ---
const triggerAnalysis = async (task_type: string) => {
  if (!selectedBounds.value) { ElMessage.warning("请先在地图上框选一个区域！"); return; }
  clearMapAnalysisState();
  mapAnalysisState.isLoading = true;
  mapAnalysisState.taskType = task_type;

  try {
    let payload: any;
    if (task_type === 'change_detection') {
      payload = {
        task_type: 'change_detection',
        southWest: selectedBounds.value.getSouthWest(),
        northEast: selectedBounds.value.getNorthEast(),
        zoom: zoom.value,
        beforeTileUrl: activeTimeLapse.before.url,
        afterTileUrl: activeTimeLapse.after.url,
      };
    } else {
      payload = {
        task_type,
        southWest: selectedBounds.value.getSouthWest(),
        northEast: selectedBounds.value.getNorthEast(),
        zoom: zoom.value,
        tileUrlTemplate: activeTimeLapse.before.url,
      };
    }
    const responseData = await MapAnalysisAPI.predictFromCoords(payload);
    mapAnalysisState.success = true;
    mapAnalysisState.result_image_url = responseData.result_url;
    mapAnalysisState.metrics = responseData.detection_metrics;

    if (task_type === 'land_segmentation') {
      if (segmentationOverlay && leafletMapInstance?.hasLayer(segmentationOverlay)) {
        leafletMapInstance.removeLayer(segmentationOverlay);
      }
      segmentationOverlay = L.imageOverlay(
        responseData.result_url, 
        selectedBounds.value!, 
        { opacity: 0.7 }
      ).addTo(leafletMapInstance!);
      ElMessage.success('地物分类结果已叠加到地图！');
    } else if (task_type === 'object_detection' && responseData.raw_results) {
      mapAnalysisState.rawResults = responseData.raw_results;
    }

    ElMessage.success(responseData.message || '分析成功！');
  } catch (e: any) {
    mapAnalysisState.error = e.response?.data?.error || e.message || "分析请求失败";
  } finally {
    mapAnalysisState.isLoading = false;
  }
};

// --- 7. watch ---
watch(() => mapAnalysisState.rawResults, (newResults) => {
  if (!analysisResultLayer || !selectedBounds.value) return;
  analysisResultLayer.clearLayers();
  if (newResults && newResults.length > 0) {
    const tileCalculator = {
      deg2num(lat: number, lon: number, zoom: number) {
        const lat_rad = lat * (Math.PI / 180);
        const n = Math.pow(2, zoom);
        return { 
          x: (lon + 180) / 360 * n, 
          y: (1 - Math.asinh(Math.tan(lat_rad)) / Math.PI) / 2 * n 
        };
      },
      num2deg(x: number, y: number, zoom: number) {
        const n = Math.pow(2, zoom);
        const lon = x / n * 360 - 180;
        const lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)));
        return L.latLng(lat * (180 / Math.PI), lon);
      }
    };
    const sw = selectedBounds.value.getSouthWest();
    const ne = selectedBounds.value.getNorthEast();
    const tileSW = tileCalculator.deg2num(sw.lat, sw.lng, zoom.value);
    const tileNE = tileCalculator.deg2num(ne.lat, ne.lng, zoom.value);
    const startTileX = Math.floor(Math.min(tileSW.x, tileNE.x));
    const startTileY = Math.floor(Math.min(tileSW.y, tileNE.y));
    
    newResults.forEach(item => {
      const [x1, y1, w, h] = item.bbox;
      const corner1 = tileCalculator.num2deg(startTileX + (x1+w)/256, startTileY + y1/256, zoom.value);
      const corner2 = tileCalculator.num2deg(startTileX + x1/256, startTileY + (y1+h)/256, zoom.value);
      const bounds = L.latLngBounds(corner1, corner2);
      L.rectangle(bounds, { color: "#ff0000", weight: 2 })
        .addTo(analysisResultLayer!)
        .bindPopup(`<b>${item.category}</b><br>置信度: ${item.score.toFixed(2)}`);
    });
    ElMessage.success(`在地图上绘制了 ${newResults.length} 个目标！`);
  }
});
</script>

<style scoped>
.map-page-container { display: flex; width: 100%; height: 92vh; }
.map-wrapper { flex-grow: 1; height: 100%; }
.map-control-panel { flex-shrink: 0; width: 350px; padding: 16px; background-color: #f5f7fa; overflow-y: auto; border-left: 1px solid #e4e7ed; display: flex; flex-direction: column; }
.analysis-buttons, .upload-section { margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }
.el-card { border: none; background-color: transparent; }
.el-card:deep(.el-card__header) { border-bottom: 1px solid #e4e7ed; padding: 16px 20px; }
.el-card:deep(.el-card__body) { padding: 20px; }
ul { padding-left: 20px; list-style-type: disc; }
.timelapse-control { display: flex; flex-direction: column; gap: 15px; }
.select-row, .slider-row { display: flex; align-items: center; gap: 10px; }
.label { width: 70px; flex-shrink: 0; font-size: 14px; }
</style>
