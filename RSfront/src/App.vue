<template>
  <header class="navbar">
    <div class="logo-container">
      <img src="./assets/vue.svg" alt="Logo" class="logo" />
      <span class="logo-text">Your Brand</span>
    </div>

    <nav class="nav-center">
      <RouterLink to="/" class="nav-link" v-slot="{ isActive }">
        <span :class="{ 'active': isActive }">首页</span>
      </RouterLink>
      <RouterLink to="/changedetectHome" class="nav-link" v-slot="{ isActive }">
        <span :class="{ 'active': isActive }">变化检测</span>
      </RouterLink>
      <RouterLink to="/objectdetectHome" class="nav-link" v-slot="{ isActive }">
        <span :class="{ 'active': isActive }">目标检测</span>
      </RouterLink>
      <RouterLink to="/roadextractHome" class="nav-link" v-slot="{ isActive }">
        <span :class="{ 'active': isActive }">道路提取</span>
      </RouterLink>
      <RouterLink to="/landclassHome" class="nav-link" v-slot="{ isActive }">
        <span :class="{ 'active': isActive }">地物分类</span>
      </RouterLink>
      <RouterLink to="/map-view" class="nav-link" v-slot="{ isActive }">
        <span :class="{ 'active': isActive }">地图分析</span>
      </RouterLink>
    </nav>

    <div class="actions-container">
      </div>
  </header>

  <main class="main-content">
    <RouterView />
  </main>
</template>

<style scoped>
/* =========== 整体导航栏容器 =========== */
.navbar {
  display: flex;
  justify-content: space-between; /* 子元素两端对齐，中间元素自动居中 */
  align-items: center;
  padding: 0 2rem; /* 左右内边距 */
  height: 64px; /* 固定高度 */
  background-color: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); /* 更柔和的阴影 */
  font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
}

/* =========== Logo 区域 =========== */
.logo-container {
  display: flex;
  align-items: center;
  gap: 0.75rem; /* Logo 和文字的间距 */
}

.logo {
  height: 32px;
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: scale(1.1) rotate(-10deg); /* 悬停时稍微放大并旋转 */
}

.logo-text {
  font-size: 1.25rem;
  font-weight: bold;
  color: #2c3e50;
}

/* =========== 中间导航链接 =========== */
.nav-center {
  display: flex;
  gap: 2.5rem; /* 链接之间的间距 */
}

.nav-link span {
  position: relative; /* 为下划线伪元素定位 */
  text-decoration: none;
  color: #2c3e50;
  font-size: 1rem;
  font-weight: 500;
  padding: 0.5rem 0;
  transition: color 0.3s ease;
}

/* 下划线动效的基础样式 */
.nav-link span::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background-color: #42b883; /* Vue 标志性的绿色 */
  transform: scaleX(0); /* 初始状态下划线宽度为0 */
  transform-origin: center;
  transition: transform 0.3s ease-in-out;
}

/* 鼠标悬停或路由激活时，触发下划线动画 */
.nav-link span:hover::after,
.nav-link span.active::after {
  transform: scaleX(1); /* 展开下划线 */
}

/* 激活状态的文字颜色 */
.nav-link span.active {
  color: #42b883;
}

/* =========== 右侧预留区域 =========== */
.actions-container {
  /* 确保这个容器和logo容器宽度差不多，可以更好地让中间导航居中 */
  /* 如果不需要严格居中，可以移除这个容器 */
  min-width: 150px; /* 示例宽度，与 logo-container 大致相等 */
  display: flex;
  justify-content: flex-end;
}

/* =========== 主内容区域 =========== */
.main-content {
  padding: 1.5rem;
}
</style>