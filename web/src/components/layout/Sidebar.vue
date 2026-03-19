<script setup lang="ts">
import { useAppStore, type ThemeMode } from '@/stores/app'
import { Icon } from '@iconify/vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const themeSliderOffset = computed(() => {
  const index = { light: 0, dark: 1, system: 2 }[appStore.themeMode] ?? 2
  return index * 40
})

const menuItems = [
  { key: '/', icon: 'mdi:home', label: '首页' },
  { key: '/debug', icon: 'mdi:chat', label: '交互调试' },
  { key: '/knowledge', icon: 'mdi:database', label: '知识库管理' },
  {
    key: '/rules',
    icon: 'mdi:cog',
    label: '规则配置',
    children: [
      { key: '/rules/commands', label: '命令词管理' },
      { key: '/rules/sensitive', label: '敏感词管理' },
      { key: '/rules/flows', label: '流程管理' },
    ],
  },
  { key: '/tools', icon: 'mdi:tools', label: '工具管理' },
  {
    key: '/models',
    icon: 'mdi:cube-outline',
    label: '模型管理',
    children: [
      { key: '/models/providers', label: '渠道商管理' },
      { key: '/models/sources', label: '模型源管理' },
    ],
  },
  { key: '/prompts', icon: 'mdi:text-box-edit', label: '提示词管理' },
  {
    key: '/robot',
    icon: 'mdi:robot',
    label: '机器人控制',
    children: [
      { key: '/robot/expressions', label: '表情管理' },
      { key: '/robot/actions', label: '动作管理' },
    ],
  },
  { key: '/analytics', icon: 'mdi:chart-line', label: '数据分析' },
  { key: '/settings', icon: 'mdi:cogs', label: '系统设置' },
]

const activeKey = computed(() => {
  const path = route.path
  for (const item of menuItems) {
    if (item.key === path) return path
    if (item.children) {
      const child = item.children.find((c) => c.key === path)
      if (child) return path
    }
  }
  return path
})

function handleMenuClick(key: string) {
  router.push(key)
}
</script>

<template>
  <aside
    class="flex flex-col h-full bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transition-all duration-300 shrink-0"
    :class="[appStore.sidebarCollapsed ? 'w-16' : 'w-56']"
  >
    <div
      class="flex items-center h-14 px-4 border-b border-slate-200 dark:border-slate-800 shrink-0"
    >
      <div class="bg-primary p-1.5 rounded-lg text-white">
        <Icon icon="mdi:chat" class="text-xl" />
      </div>
      <transition name="fade">
        <div v-if="!appStore.sidebarCollapsed" class="ml-3 overflow-hidden">
          <h1 class="text-base font-bold text-slate-900 dark:text-white truncate">
            Chat2RAG
          </h1>
          <p class="text-xs text-slate-500 dark:text-slate-400 truncate">
            人机交互管理平台
          </p>
        </div>
      </transition>
    </div>

    <div class="flex-1 overflow-y-auto py-4 custom-scrollbar">
      <a-menu
        :collapsed="appStore.sidebarCollapsed"
        :selected-keys="[activeKey]"
        :auto-open-selected="true"
        @menu-item-click="handleMenuClick"
        class="border-none bg-transparent"
      >
        <template v-for="item in menuItems" :key="item.key">
          <a-sub-menu v-if="item.children" :key="item.key">
            <template #icon>
              <Icon :icon="item.icon" />
            </template>
            <template #title>{{ item.label }}</template>
            <a-menu-item v-for="child in item.children" :key="child.key">
              {{ child.label }}
            </a-menu-item>
          </a-sub-menu>
          <a-menu-item v-else :key="item.key">
            <template #icon>
              <Icon :icon="item.icon" />
            </template>
            {{ item.label }}
          </a-menu-item>
        </template>
      </a-menu>
    </div>

    <div class="p-3 border-t border-slate-200 dark:border-slate-800 shrink-0">
      <a-dropdown trigger="click" position="top">
        <div
          class="flex items-center gap-3 p-2 bg-slate-50 dark:bg-slate-800 rounded-xl cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          <div
            class="size-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0"
          >
            <Icon icon="mdi:account" class="text-primary text-base" />
          </div>
          <transition name="fade">
            <div v-if="!appStore.sidebarCollapsed" class="flex-1 overflow-hidden">
              <p class="text-xs font-bold truncate text-slate-900 dark:text-white">
                Admin User
              </p>
              <p class="text-[10px] text-slate-500 truncate">admin@example.com</p>
            </div>
          </transition>
        </div>
        <template #content>
          <div class="p-2">
            <div
              class="flex items-center justify-around p-1 bg-slate-100 dark:bg-slate-700 rounded-lg relative"
            >
              <div
                class="absolute h-7 w-10 bg-white dark:bg-slate-600 rounded shadow-sm transition-transform duration-200"
                :style="{ transform: `translateX(${themeSliderOffset}px)` }"
              ></div>
              <button
                v-for="t in [
                  { key: 'light', icon: 'mdi:weather-sunny' },
                  { key: 'dark', icon: 'mdi:weather-night' },
                  { key: 'system', icon: 'mdi:theme-light-dark' },
                ]"
                :key="t.key"
                @click="appStore.setThemeMode(t.key as ThemeMode)"
                class="relative z-10 p-1.5 rounded transition-colors w-10 flex justify-center"
                :class="
                  appStore.themeMode === t.key
                    ? 'text-primary'
                    : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                "
              >
                <Icon :icon="t.icon" class="text-lg" />
              </button>
            </div>
          </div>
          <a-divider class="my-1" />
          <a-doption>
            <template #icon>
              <Icon icon="mdi:logout" />
            </template>
            退出登录
          </a-doption>
        </template>
      </a-dropdown>
      <transition name="fade">
        <a-button
          v-if="!appStore.sidebarCollapsed"
          size="small"
          class="w-full mt-2"
          @click="appStore.toggleSidebar"
        >
          <template #icon>
            <Icon icon="mdi:menu-open" />
          </template>
          折叠菜单
        </a-button>
      </transition>
      <a-tooltip v-if="appStore.sidebarCollapsed" content="展开菜单" position="right">
        <a-button size="small" class="w-full mt-2" @click="appStore.toggleSidebar">
          <template #icon>
            <Icon icon="mdi:menu" />
          </template>
        </a-button>
      </a-tooltip>
    </div>
  </aside>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: #334155;
}
</style>
