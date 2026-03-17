import { defineStore } from 'pinia'
import { ref, watch, computed } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

export const useAppStore = defineStore(
  'app',
  () => {
    const sidebarCollapsed = ref(false)
    const themeMode = ref<ThemeMode>('system')

    function toggleSidebar() {
      sidebarCollapsed.value = !sidebarCollapsed.value
    }

    function setThemeMode(mode: ThemeMode) {
      themeMode.value = mode
    }

    function applyTheme() {
      const isDark = themeMode.value === 'dark' ||
        (themeMode.value === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)

      if (isDark) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }

    watch(themeMode, applyTheme, { immediate: true })

    if (typeof window !== 'undefined') {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (themeMode.value === 'system') {
          applyTheme()
        }
      })
    }

    return {
      sidebarCollapsed,
      themeMode,
      toggleSidebar,
      setThemeMode,
    }
  },
  {
    persist: {
      key: 'chat2rag-app',
      storage: localStorage,
      pick: ['sidebarCollapsed', 'themeMode'],
    },
  }
)