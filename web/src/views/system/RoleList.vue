<script setup lang="ts">
import { roleApi, type Role, type RoleDetail, type RoleCreate, type RoleUpdate } from '@/api/role'
import { permissionApi, type PermissionTree } from '@/api/permission'
import { Message } from '@arco-design/web-vue'
import { Icon } from '@iconify/vue'
import { onMounted, reactive, ref } from 'vue'

const loading = ref(false)
const roles = ref<Role[]>([])
const permissionTree = ref<PermissionTree[]>([])
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
  description: '',
  status: 1,
  sort: 0,
  permissionIds: [] as number[],
})

const form = reactive(defaultForm())

const statusOptions = [
  { label: '全部', value: '' },
  { label: '启用', value: 1 },
  { label: '禁用', value: 0 },
]

async function loadPermissionTree() {
  try {
    const res = await permissionApi.getTree()
    permissionTree.value = res.data.data
  } catch {
    console.error('Failed to load permission tree')
  }
}

async function fetchRoles() {
  loading.value = true
  try {
    const res = await roleApi.getList({
      current: pagination.current,
      size: pagination.pageSize,
    })
    roles.value = res.data.data.items
    pagination.total = res.data.data.total
  } catch {
    Message.error('获取角色列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.current = 1
  fetchRoles()
}

function handlePageChange(page: number) {
  pagination.current = page
  fetchRoles()
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size
  pagination.current = 1
  fetchRoles()
}

function openCreateDrawer() {
  Object.assign(form, defaultForm())
  isEdit.value = false
  editId.value = null
  drawerVisible.value = true
}

async function openEditDrawer(role: Role) {
  isEdit.value = true
  editId.value = role.id
  try {
    const res = await roleApi.getDetail(role.id)
    const detail: RoleDetail = res.data.data
    form.name = detail.name
    form.code = detail.code
    form.description = detail.description || ''
    form.status = detail.status
    form.sort = detail.sort
    form.permissionIds = detail.permissions ? detail.permissions.map(Number) : []
    drawerVisible.value = true
  } catch {
    Message.error('获取角色详情失败')
  }
}

function closeDrawer() {
  drawerVisible.value = false
  Object.assign(form, defaultForm())
}

async function handleSubmit() {
  if (!form.name.trim()) {
    Message.warning('请输入角色名称')
    return
  }
  if (!form.code.trim()) {
    Message.warning('请输入角色编码')
    return
  }

  drawerLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      const payload: RoleUpdate = {
        name: form.name.trim(),
        description: form.description || undefined,
        status: form.status,
        sort: form.sort,
        permissionIds: form.permissionIds.length > 0 ? form.permissionIds : undefined,
      }
      await roleApi.update(editId.value, payload)
      Message.success('更新成功')
    } else {
      const payload: RoleCreate = {
        name: form.name.trim(),
        code: form.code.trim(),
        description: form.description || undefined,
        status: form.status,
        sort: form.sort,
        permissionIds: form.permissionIds.length > 0 ? form.permissionIds : undefined,
      }
      await roleApi.create(payload)
      Message.success('创建成功')
    }
    closeDrawer()
    fetchRoles()
  } catch {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    drawerLoading.value = false
  }
}

async function toggleRoleStatus(role: Role) {
  try {
    await roleApi.update(role.id, { status: role.status === 1 ? 0 : 1 })
    Message.success(role.status === 1 ? '已禁用' : '已启用')
    fetchRoles()
  } catch {
    Message.error('操作失败')
  }
}

async function deleteRole(role: Role) {
  if (role.isSystem) {
    Message.warning('系统内置角色不能删除')
    return
  }
  try {
    await roleApi.delete(role.id)
    Message.success('删除成功')
    fetchRoles()
  } catch {
    Message.error('删除失败')
  }
}

function flattenPermissions(tree: PermissionTree[], result: { key: string; title: string }[] = []) {
  for (const node of tree) {
    result.push({ key: String(node.id), title: node.name })
    if (node.children && node.children.length > 0) {
      flattenPermissions(node.children, result)
    }
  }
  return result
}

onMounted(() => {
  loadPermissionTree()
  fetchRoles()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:account-cog" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">角色管理</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索角色名称或编码..."
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
            新增角色
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-table
        :data="roles"
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
          <a-table-column title="角色名称" data-index="name" :width="140">
            <template #cell="{ record }">
              <span class="font-medium text-slate-700 dark:text-slate-200">{{ record.name }}</span>
            </template>
          </a-table-column>
          <a-table-column title="角色编码" data-index="code" :width="140">
            <template #cell="{ record }">
              <a-tag size="small" color="arcoblue">{{ record.code }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="描述" data-index="description" :width="200">
            <template #cell="{ record }">
              <span class="text-slate-500 text-sm">{{ record.description || '-' }}</span>
            </template>
          </a-table-column>
          <a-table-column title="排序" data-index="sort" :width="80" align="center">
            <template #cell="{ record }">
              <span class="font-mono text-sm">{{ record.sort }}</span>
            </template>
          </a-table-column>
          <a-table-column title="系统内置" :width="90" align="center">
            <template #cell="{ record }">
              <a-tag v-if="record.isSystem" color="purple" size="small">是</a-tag>
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
          <a-table-column title="操作" :width="140" align="center">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="toggleRoleStatus(record)">
                  <template #icon>
                    <Icon :icon="record.status === 1 ? 'mdi:toggle-switch' : 'mdi:toggle-switch-off-outline'" class="text-lg" />
                  </template>
                </a-button>
                <a-button type="text" size="small" @click="openEditDrawer(record)">
                  <template #icon><Icon icon="mdi:pencil" class="text-lg" /></template>
                </a-button>
                <a-popconfirm content="确定删除该角色吗？" @ok="deleteRole(record)">
                  <a-button type="text" size="small" status="danger" :disabled="record.isSystem">
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
      :title="isEdit ? '编辑角色' : '新增角色'"
      :width="480"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="角色名称" required>
          <a-input v-model="form.name" placeholder="请输入角色名称" />
        </a-form-item>
        <a-form-item label="角色编码" required>
          <a-input v-model="form.code" placeholder="请输入角色编码，如 admin" :disabled="isEdit" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model="form.description" placeholder="请输入角色描述" :auto-size="{ minRows: 2, maxRows: 4 }" />
        </a-form-item>
        <a-form-item label="排序">
          <a-input-number v-model="form.sort" :min="0" :max="999" style="width: 100%" />
        </a-form-item>
        <a-form-item label="权限分配">
          <a-tree
            v-model:checked-keys="form.permissionIds"
            :data="permissionTree"
            :field-names="{ key: 'id', title: 'name', children: 'children' }"
            checkable
            :default-expand-all="true"
            style="max-height: 300px; overflow: auto"
          />
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