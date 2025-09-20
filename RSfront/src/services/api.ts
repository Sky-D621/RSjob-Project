import axios from 'axios';
import { ElMessage } from 'element-plus';

// 创建一个 Axios 实例，并进行基础配置
const apiClient = axios.create({
  // 使用相对路径 '/api'，Vite 代理会自动匹配并转发
  // 在生产环境中，Nginx 等反向代理服务器也会配置相应的规则来处理 '/api'
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 请求超时时间 60 秒
});

// --- 添加响应拦截器，用于统一的错误处理 ---
apiClient.interceptors.response.use(
  // 请求成功，直接返回响应体中的 `data`
  (response) => {
    return response.data;
  },
  // 请求失败，进行统一的错误提示
  (error) => {
    console.error('API Error:', error.response || error.message);

    // 优先使用后端返回的错误信息，否则显示通用错误
    const errorMessage = error.response?.data?.error || '网络请求异常，请稍后重试';
    ElMessage.error(errorMessage);
    
    // 将错误继续抛出，以便组件中的 .catch() 逻辑可以执行
    return Promise.reject(error);
  }
);


// --- 定义并导出具体的 API 请求函数 ---
export const MapAnalysisAPI = {
  predictFromCoords(payload: {
    southWest: L.LatLng;
    northEast: L.LatLng;
    zoom: number;
    task_type: string;
    tileUrlTemplate: string;
  }) {
    return apiClient.post('/map_analysis/predict_from_coords', payload);
  }
};

export const ChangeDetectionAPI = {
  predict(payload: { path_a: string; path_b: string; }) {
    return apiClient.post('/change_detection/predict', payload);
  }
};
