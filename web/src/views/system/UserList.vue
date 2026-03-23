<script setup lang="ts">
import { userApi, type User, type UserDetail, type UserCreate, type UserUpdate } from '@/api/user'
import { roleApi, type Role } from '@/api/role'
import { Message } from '@arco-design/web-vue'
import { Icon } from '@iconify/vue'
import { onMounted, reactive, ref } from 'vue'

const loading = ref(false)
const users = ref<User[]>([])
const roles = ref<Role[]>([])
const pagination = reactive({ current: 1, pageSize: 10, total: 0 })
const searchKeyword = ref('')
const statusFilter = ref<number | ''>('')

const drawerVisible = ref(false)
const drawerLoading = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)

const resetPasswordVisible = ref(false)
const resetPasswordLoading = ref(false)
const resetPasswordUserId = ref<number | null>(null)
const newPassword = ref('')

const defaultForm = () => ({
  username: '',
  password: '',
  nickname: '',
  phone: '',
  email: '',
  status: 1,
  roleIds: [] as number[],
})

const form = reactive(defaultForm())

const statusOptions = [
  { label: '全部', value: '' },
  { label: '启用', value: 1 },
  { label: '禁用', value: 0 },
]

async function loadRoles() {
  try {
    const res = await roleApi.getList({ current: 1, size: 100 })
    roles.value = res.data.data.items
  } catch {
    console.error('Failed to load roles')
  }
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await userApi.getList({
      current: pagination.current,
      size: pagination.pageSize,
    })
    users.value = res.data.data.items
    pagination.total = res.data.data.total
  } catch {
    Message.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.current = 1
  fetchUsers()
}

function handlePageChange(page: number) {
  pagination.current = page
  fetchUsers()
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size
  pagination.current = 1
  fetchUsers()
}

function openCreateDrawer() {
  Object.assign(form, defaultForm())
  isEdit.value = false
  editId.value = null
  drawerVisible.value = true
}

async function openEditDrawer(user: User) {
  isEdit.value = true
  editId.value = user.id
  try {
    const res = await userApi.getDetail(user.id)
    const detail: UserDetail = res.data.data
    form.username = detail.username
    form.password = ''
    form.nickname = detail.nickname || ''
    form.phone = detail.phone || ''
    form.email = detail.email || ''
    form.status = detail.status
    form.roleIds = detail.roles ? detail.roles.map(Number) : []
    drawerVisible.value = true
  } catch {
    Message.error('获取用户详情失败')
  }
}

function closeDrawer() {
  drawerVisible.value = false
  Object.assign(form, defaultForm())
}

async function handleSubmit() {
  if (!form.username.trim()) {
    Message.warning('请输入用户名')
    return
  }
  if (!isEdit.value && !form.password.trim()) {
    Message.warning('请输入密码')
    return
  }

  drawerLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      const payload: UserUpdate = {
        nickname: form.nickname || undefined,
        phone: form.phone || undefined,
        email: form.email || undefined,
        status: form.status,
        roleIds: form.roleIds.length > 0 ? form.roleIds : undefined,
      }
      await userApi.update(editId.value, payload)
      Message.success('更新成功')
    } else {
      const payload: UserCreate = {
        username: form.username.trim(),
        password: form.password,
        nickname: form.nickname || undefined,
        phone: form.phone || undefined,
        email: form.email || undefined,
        status: form.status,
        roleIds: form.roleIds.length > 0 ? form.roleIds : undefined,
      }
      await userApi.create(payload)
      Message.success('创建成功')
    }
    closeDrawer()
    fetchUsers()
  } catch {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    drawerLoading.value = false
  }
}

async function toggleUserStatus(user: User) {
  try {
    await userApi.update(user.id, { status: user.status === 1 ? 0 : 1 })
    Message.success(user.status === 1 ? '已禁用' : '已启用')
    fetchUsers()
  } catch {
    Message.error('操作失败')
  }
}

function openResetPassword(user: User) {
  resetPasswordUserId.value = user.id
  newPassword.value = ''
  resetPasswordVisible.value = true
}

async function handleResetPassword() {
  if (!newPassword.value.trim()) {
    Message.warning('请输入新密码')
    return
  }
  if (newPassword.value.length < 6) {
    Message.warning('密码长度不能少于6位')
    return
  }

  resetPasswordLoading.value = true
  try {
    await userApi.update(resetPasswordUserId.value!, { password: newPassword.value } as any)
    Message.success('密码重置成功')
    resetPasswordVisible.value = false
  } catch {
    Message.error('密码重置失败')
  } finally {
    resetPasswordLoading.value = false
  }
}

async function deleteUser(user: User) {
  try {
    await userApi.delete(user.id)
    Message.success('删除成功')
    fetchUsers()
  } catch {
    Message.error('删除失败')
  }
}

onMounted(() => {
  loadRoles()
  fetchUsers()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:account-group" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">用户管理</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索用户名或手机号..."
            style="width: 240px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-select v-model="statusFilter" placeholder="状态" style="width: 100px">
            <a-option v-for="opt in statusOptions" :key="String(opt.value)" :value="opt.value">
              {{ opt.label }}
            </a-option>
          </a-select>
          <a-button type="primary" @click="openCreateDrawer">
            <template #icon><Icon icon="mdi:plus" /></template>
            新增用户
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-table
        :data="users"
        :loading="loading"
        :pagination="{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showTotal: true,
          showPageSize: true,
        }"
        row-key="id"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
      >
        <template #columns>
          <a-table-column title="ID" data-index="id" :width="80" />
          <a-table-column title="用户名" data-index="username" :width="120">
            <template #cell="{ record }">
              <span class="font-medium text-slate-700 dark:text-slate-200">{{ record.username }}</span>
            </template>
          </a-table-column>
          <a-table-column title="昵称" data-index="nickname" :width="120">
            <template #cell="{ record }">
              <span class="text-slate-600 dark:text-slate-300">{{ record.nickname || '-' }}</span>
            </template>
          </a-table-column>
          <a-table-column title="手机号" data-index="phone" :width="130">
            <template #cell="{ record }">
              <span class="text-slate-500">{{ record.phone || '-' }}</span>
            </template>
          </a-table-column>
          <a-table-column title="邮箱" data-index="email" :width="180">
            <template #cell="{ record }">
              <span class="text-slate-500 text-sm">{{ record.email || '-' }}</span>
            </template>
          </a-table-column>
          <a-table-column title="超级管理员" :width="100" align="center">
            <template #cell="{ record }">
              <a-tag v-if="record.isSuperuser" color="purple" size="small">是</a-tag>
              <span v-else class="text-slate-400">-</span>
            </template>
          </a-table-column>
          <a-table-column title="状态" :width="80" align="center">
            <template #cell="{ record }">
              <a-tag :color="record.status === 1 ? 'green' : 'red'" size="small">
                {{ record.status === 1 ? '启用' : '禁用' }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="创建时间" data-index="createTime" :width="170" />
          <a-table-column title="操作" :width="200" align="center">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="toggleUserStatus(record)">
                  <template #icon>
                    <Icon :icon="record.status === 1 ? 'mdi:toggle-switch' : 'mdi:toggle-switch-off-outline'" class="text-lg" />
                  </template>
                </a-button>
                <a-button type="text" size="small" @click="openEditDrawer(record)">
                  <template #icon><Icon icon="mdi:pencil" class="text-lg" /></template>
                </a-button>
                <a-button type="text" size="small" @click="openResetPassword(record)">
                  <template #icon><Icon icon="mdi:key" class="text-lg" /></template>
                </a-button>
                <a-popconfirm content="确定删除该用户吗？" @ok="deleteUser(record)">
                  <a-button type="text" size="small" status="danger">
                    <template #icon><Icon icon="mdi:delete" class="text-lg" /></template>
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </div>

    <a-drawer
      v-model:visible="drawerVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      :width="420"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="用户名" required>
          <a-input v-model="form.username" placeholder="请输入用户名" :disabled="isEdit" />
        </a-form-item>
        <a-form-item v-if="!isEdit" label="密码" required>
          <a-input-password v-model="form.password" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item label="昵称">
          <a-input v-model="form.nickname" placeholder="请输入昵称" />
        </a-form-item>
        <a-form-item label="手机号">
          <a-input v-model="form.phone" placeholder="请输入手机号" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model="form.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item label="角色">
          <a-select v-model="form.roleIds" multiple placeholder="请选择角色" allow-clear>
            <a-option v-for="role in roles" :key="role.id" :value="role.id">
              {{ role.name }}
            </a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="状态">
          <a-radio-group v-model="form.status">
            <a-radio :value="1">启用</a-radio>
            <a-radio :value="0">禁用</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="closeDrawer">取消</a-button>
          <a-button type="primary" :loading="drawerLoading" @click="handleSubmit">
            {{ isEdit ? '更新' : '创建' }}
          </a-button>
        </a-space>
      </template>
    </a-drawer>

    <a-modal
      v-model:visible="resetPasswordVisible"
      title="重置密码"
      :model="{ newPassword }"
      :ok-loading="resetPasswordLoading"
      @ok="handleResetPassword"
      @cancel="resetPasswordVisible = false"
    >
      <a-form :model="{ newPassword }" layout="vertical">
        <a-form-item label="新密码" required>
          <a-input-password v-model="newPassword" placeholder="请输入新密码" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>