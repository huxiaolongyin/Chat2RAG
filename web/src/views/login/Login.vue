<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h1>Chat2RAG</h1>
        <p>智能问答系统</p>
      </div>

      <a-tabs v-model:active-key="loginType" class="login-tabs">
        <a-tab-pane key="password" title="账号密码">
          <a-form :model="passwordForm" @submit-success="handlePasswordLogin" layout="vertical">
            <a-form-item field="username" label="用户名" :rules="[{ required: true, message: '请输入用户名' }]">
              <a-input v-model="passwordForm.username" placeholder="请输入用户名" allow-clear />
            </a-form-item>
            <a-form-item field="password" label="密码" :rules="[{ required: true, message: '请输入密码' }]">
              <a-input-password v-model="passwordForm.password" placeholder="请输入密码" allow-clear />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" html-type="submit" long :loading="loading">登录</a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="sms" title="手机验证码">
          <a-form :model="smsForm" @submit-success="handleSmsLogin" layout="vertical">
            <a-form-item field="phone" label="手机号" :rules="[{ required: true, message: '请输入手机号' }]">
              <a-input v-model="smsForm.phone" placeholder="请输入手机号" allow-clear />
            </a-form-item>
            <a-form-item field="code" label="验证码" :rules="[{ required: true, message: '请输入验证码' }]">
              <a-input v-model="smsForm.code" placeholder="请输入验证码" allow-clear>
                <template #append>
                  <a-button :disabled="countdown > 0" @click="sendCode" :loading="sendingCode">
                    {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
                  </a-button>
                </template>
              </a-input>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" html-type="submit" long :loading="loading">登录</a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api/auth'

const router = useRouter()
const userStore = useUserStore()

const loginType = ref('password')
const loading = ref(false)
const sendingCode = ref(false)
const countdown = ref(0)

const passwordForm = reactive({
  username: '',
  password: '',
  tenantCode: '',
})

const smsForm = reactive({
  phone: '',
  code: '',
  tenantCode: '',
})

async function handlePasswordLogin() {
  loading.value = true
  try {
    await userStore.login({
      username: passwordForm.username,
      password: passwordForm.password,
      tenantCode: passwordForm.tenantCode || undefined,
    })
    Message.success('登录成功')
    router.push('/')
  } catch (error: any) {
    Message.error(error.response?.data?.msg || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleSmsLogin() {
  loading.value = true
  try {
    await userStore.smsLogin({
      phone: smsForm.phone,
      code: smsForm.code,
      tenantCode: smsForm.tenantCode || undefined,
    })
    Message.success('登录成功')
    router.push('/')
  } catch (error: any) {
    Message.error(error.response?.data?.msg || '登录失败')
  } finally {
    loading.value = false
  }
}

async function sendCode() {
  if (!smsForm.phone) {
    Message.warning('请输入手机号')
    return
  }
  sendingCode.value = true
  try {
    await authApi.sendSmsCode({ phone: smsForm.phone })
    Message.success('验证码已发送')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  } catch (error: any) {
    Message.error(error.response?.data?.msg || '发送失败')
  } finally {
    sendingCode.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 8px;
}

.login-header p {
  color: #666;
  font-size: 14px;
}

.login-tabs {
  margin-top: 20px;
}
</style>