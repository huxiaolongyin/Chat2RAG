import type { Router } from 'vue-router'
import { useUserStore } from '@/stores/user'

export function setupRouterGuard(router: Router) {
  router.beforeEach(async (to, _from, next) => {
    const title = to.meta.title as string
    if (title) {
      document.title = `${title} - Chat2RAG`
    }

    const userStore = useUserStore()
    const requiresAuth = to.meta.requiresAuth !== false

    if (to.path === '/login') {
      if (userStore.isLoggedIn) {
        next('/')
        return
      }
      next()
      return
    }

    if (requiresAuth && !userStore.isLoggedIn) {
      next('/login')
      return
    }

    if (userStore.isLoggedIn && !userStore.userInfo) {
      try {
        await userStore.fetchUserInfo()
      } catch {
        userStore.logout()
        next('/login')
        return
      }
    }

    next()
  })
}