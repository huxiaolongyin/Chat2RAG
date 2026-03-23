import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CurrentUserResponse, LoginResponse } from '../api/auth'
import { authApi } from '../api/auth'
import router from '../router'

export const useUserStore = defineStore(
  'user',
  () => {
    const token = ref<string | null>(null)
    const userInfo = ref<CurrentUserResponse | null>(null)

    const isLoggedIn = computed(() => !!token.value)
    const permissions = computed(() => userInfo.value?.permissions || [])
    const roles = computed(() => userInfo.value?.roles || [])
    const isSuperuser = computed(() => userInfo.value?.isSuperuser || false)

    function setToken(newToken: string) {
      token.value = newToken
    }

    function setUserInfo(info: CurrentUserResponse) {
      userInfo.value = info
    }

    async function login(data: { username: string; password: string; tenantCode?: string }) {
      const res = await authApi.login(data)
      const loginData: LoginResponse = res.data.data
      setToken(loginData.token.accessToken)
      await fetchUserInfo()
      return loginData
    }

    async function smsLogin(data: { phone: string; code: string; tenantCode?: string }) {
      const res = await authApi.smsLogin(data)
      const loginData: LoginResponse = res.data.data
      setToken(loginData.token.accessToken)
      await fetchUserInfo()
      return loginData
    }

    async function fetchUserInfo() {
      const res = await authApi.getCurrentUser()
      const info: CurrentUserResponse = res.data.data
      setUserInfo(info)
      return info
    }

    async function logout() {
      try {
        await authApi.logout()
      } catch {
        // ignore
      }
      token.value = null
      userInfo.value = null
      router.push('/login')
    }

    function hasPermission(permission: string): boolean {
      if (isSuperuser.value) return true
      if (permissions.value.includes('*')) return true
      return permissions.value.includes(permission)
    }

    function hasAnyPermission(permissionList: string[]): boolean {
      if (isSuperuser.value) return true
      if (permissions.value.includes('*')) return true
      return permissionList.some(p => permissions.value.includes(p))
    }

    function hasAllPermissions(permissionList: string[]): boolean {
      if (isSuperuser.value) return true
      if (permissions.value.includes('*')) return true
      return permissionList.every(p => permissions.value.includes(p))
    }

    function hasRole(role: string): boolean {
      return roles.value.includes(role)
    }

    return {
      token,
      userInfo,
      isLoggedIn,
      permissions,
      roles,
      isSuperuser,
      setToken,
      setUserInfo,
      login,
      smsLogin,
      fetchUserInfo,
      logout,
      hasPermission,
      hasAnyPermission,
      hasAllPermissions,
      hasRole,
    }
  },
  {
    persist: {
      key: 'chat2rag-user',
      storage: localStorage,
      pick: ['token'],
    },
  }
)