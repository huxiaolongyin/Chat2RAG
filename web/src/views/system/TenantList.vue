<script setup lang="ts">
import { tenantApi, type Tenant, type TenantCreate, type TenantUpdate } from '@/api/tenant'
import { Message } from '@arco-design/web-vue'
import { Icon } from '@iconify/vue'
import { onMounted, reactive, ref } from 'vue'

const loading = ref(false)
const tenants = ref<Tenant[]>([])
const pagination = reactive({ current: 1, pageSize: 10, total: 0 })
const searchKeyword = ref('')
const statusFilter = ref<number | ''>('')

const drawerVisible = ref(false)
const drawerLoading = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)

const defaultForm = () => ({
  name: '',
  code: '',
  logo: '',
  contactName: '',
  contactPhone: '',
  status: 1,
  expireTime: '',
  remark: '',
})

const form = reactive(defaultForm())

const statusOptions = [
  { label: '全部', value: '' },
  { label: '启用', value: 1 },
  { label: '禁用', value: 0 },
]

async function fetchTenants() {
  loading.value = true
  try {
    const res = await tenantApi.getList({
      current: pagination.current,
      size: pagination.pageSize,
    })
    tenants.value = res.data.data.items
    pagination.total = res.data.data.total
  } catch {
    Message.error('获取租户列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.current = 1
  fetchTenants()
}

function handlePageChange(page: number) {
  pagination.current = page
  fetchTenants()
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size
  pagination.current = 1
  fetchTenants()
}

function openCreateDrawer() {
  Object.assign(form, defaultForm())
  isEdit.value = false
  editId.value = null
  drawerVisible.value = true
}

async function openEditDrawer(tenant: Tenant) {
  isEdit.value = true
  editId.value = tenant.id
  try {
    const res = await tenantApi.getDetail(tenant.id)
    const detail: Tenant = res.data.data
    form.name = detail.name
    form.code = detail.code
    form.logo = detail.logo || ''
    form.contactName = detail.contactName || ''
    form.contactPhone = detail.contactPhone || ''
    form.status = detail.status
    form.expireTime = detail.expireTime || ''
    form.remark = detail.remark || ''
    drawerVisible.value = true
  } catch {
    Message.error('获取租户详情失败')
  }
}

function closeDrawer() {
  drawerVisible.value = false
  Object.assign(form, defaultForm())
}

async function handleSubmit() {
  if (!form.name.trim()) {
    Message.warning('请输入租户名称')
    return
  }
  if (!form.code.trim()) {
    Message.warning('请输入租户编码')
    return
  }

  drawerLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      const payload: TenantUpdate = {
        name: form.name.trim(),
        logo: form.logo || undefined,
        contactName: form.contactName || undefined,
        contactPhone: form.contactPhone || undefined,
        status: form.status,
        expireTime: form.expireTime || undefined,
        remark: form.remark || undefined,
      }
      await tenantApi.update(editId.value, payload)
      Message.success('更新成功')
    } else {
      const payload: TenantCreate = {
        name: form.name.trim(),
        code: form.code.trim(),
        logo: form.logo || undefined,
        contactName: form.contactName || undefined,
        contactPhone: form.contactPhone || undefined,
        status: form.status,
        expireTime: form.expireTime || undefined,
        remark: form.remark || undefined,
      }
      await tenantApi.create(payload)
      Message.success('创建成功')
    }
    closeDrawer()
    fetchTenants()
  } catch {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    drawerLoading.value = false
  }
}

async function toggleTenantStatus(tenant: Tenant) {
  try {
    await tenantApi.update(tenant.id, { status: tenant.status === 1 ? 0 : 1 })
    Message.success(tenant.status === 1 ? '已禁用' : '已启用')
    fetchTenants()
  } catch {
    Message.error('操作失败')
  }
}

async function deleteTenant(tenant: Tenant) {
  try {
    await tenantApi.delete(tenant.id)
    Message.success('删除成功')
    fetchTenants()
  } catch {
    Message.error('删除失败')
  }
}

onMounted(() => {
  fetchTenants()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:office-building" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">租户管理</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索租户名称或编码..."
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
            新增租户
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-table
        :data="tenants"
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
          <a-table-column title="租户名称" data-index="name" :width="160">
            <template #cell="{ record }">
              <div class="flex items-center gap-2">
                <div
                  v-if="record.logo"
                  class="w-6 h-6 rounded bg-slate-100 dark:bg-slate-700 flex items-center justify-center overflow-hidden"
                >
                  <img :src="record.logo" :alt="record.name" class="w-full h-full object-cover" />
                </div>
                <span class="font-medium text-slate-700 dark:text-slate-200">{{ record.name }}</span>
              </div>
            </template>
          </a-table-column>
          <a-table-column title="租户编码" data-index="code" :width="140">
            <template #cell="{ record }">
              <a-tag size="small" color="arcoblue">{{ record.code }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="联系人" data-index="contactName" :width="120">
            <template #cell="{ record }">
              <span class="text-slate-600 dark:text-slate-300">{{ record.contactName || '-' }}</span>
            </template>
          </a-table-column>
          <a-table-column title="联系电话" data-index="contactPhone" :width="140">
            <template #cell="{ record }">
              <span class="text-slate-500">{{ record.contactPhone || '-' }}</span>
            </template>
          </a-table-column>
          <a-table-column title="到期时间" data-index="expireTime" :width="170">
            <template #cell="{ record }">
              <span v-if="record.expireTime" class="text-sm text-slate-500">{{ record.expireTime }}</span>
              <span v-else class="text-slate-400">永久有效</span>
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
          <a-table-column title="操作" :width="140" align="center">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="toggleTenantStatus(record)">
                  <template #icon>
                    <Icon :icon="record.status === 1 ? 'mdi:toggle-switch' : 'mdi:toggle-switch-off-outline'" class="text-lg" />
                  </template>
                </a-button>
                <a-button type="text" size="small" @click="openEditDrawer(record)">
                  <template #icon><Icon icon="mdi:pencil" class="text-lg" /></template>
                </a-button>
                <a-popconfirm content="确定删除该租户吗？" @ok="deleteTenant(record)">
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
      :title="isEdit ? '编辑租户' : '新增租户'"
      :width="420"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="租户名称" required>
          <a-input v-model="form.name" placeholder="请输入租户名称" />
        </a-form-item>
        <a-form-item label="租户编码" required>
          <a-input v-model="form.code" placeholder="请输入租户编码，如 company_a" :disabled="isEdit" />
        </a-form-item>
        <a-form-item label="Logo URL">
          <a-input v-model="form.logo" placeholder="请输入Logo图片URL" />
        </a-form-item>
        <a-form-item label="联系人">
          <a-input v-model="form.contactName" placeholder="请输入联系人姓名" />
        </a-form-item>
        <a-form-item label="联系电话">
          <a-input v-model="form.contactPhone" placeholder="请输入联系电话" />
        </a-form-item>
        <a-form-item label="到期时间">
          <a-date-picker
            v-model="form.expireTime"
            style="width: 100%"
            placeholder="选择到期时间，留空表示永久有效"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
          />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model="form.remark" placeholder="请输入备注信息" :auto-size="{ minRows: 2, maxRows: 4 }" />
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
  </div>
</template>