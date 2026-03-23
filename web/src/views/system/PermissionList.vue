<script setup lang="ts">
import { permissionApi, type Permission, type PermissionTree, type PermissionCreate, type PermissionUpdate } from '@/api/permission'
import { Message } from '@arco-design/web-vue'
import { Icon } from '@iconify/vue'
import { onMounted, reactive, ref } from 'vue'

const loading = ref(false)
const permissions = ref<PermissionTree[]>([])
const permissionList = ref<Permission[]>([])
const searchKeyword = ref('')

const drawerVisible = ref(false)
const drawerLoading = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)

const defaultForm = () => ({
  parentId: undefined as number | undefined,
  name: '',
  code: '',
  type: 'menu' as 'menu' | 'api' | 'button',
  path: '',
  component: '',
  icon: '',
  sort: 0,
  status: 1,
  visible: true,
  cache: false,
  remark: '',
})

const form = reactive(defaultForm())

const typeOptions = [
  { label: '菜单', value: 'menu' },
  { label: 'API', value: 'api' },
  { label: '按钮', value: 'button' },
]

const typeColorMap: Record<string, string> = {
  menu: 'blue',
  api: 'green',
  button: 'orange',
}

async function fetchPermissions() {
  loading.value = true
  try {
    const [treeRes, listRes] = await Promise.all([
      permissionApi.getTree(),
      permissionApi.getList({ current: 1, size: 1000 }),
    ])
    permissions.value = treeRes.data.data
    permissionList.value = listRes.data.data.items
  } catch {
    Message.error('获取权限列表失败')
  } finally {
    loading.value = false
  }
}

function flattenPermissions(tree: PermissionTree[], result: Permission[] = []): Permission[] {
  for (const node of tree) {
    result.push(node)
    if (node.children && node.children.length > 0) {
      flattenPermissions(node.children, result)
    }
  }
  return result
}

function handleSearch() {
  // 搜索功能在树形表格中通过前端过滤实现
}

function openCreateDrawer(parentId?: number) {
  Object.assign(form, defaultForm())
  form.parentId = parentId
  isEdit.value = false
  editId.value = null
  drawerVisible.value = true
}

async function openEditDrawer(permission: Permission) {
  isEdit.value = true
  editId.value = permission.id
  form.parentId = permission.parentId
  form.name = permission.name
  form.code = permission.code
  form.type = permission.type
  form.path = permission.path || ''
  form.component = permission.component || ''
  form.icon = permission.icon || ''
  form.sort = permission.sort
  form.status = permission.status
  form.visible = permission.visible
  form.cache = permission.cache
  form.remark = permission.remark || ''
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
  Object.assign(form, defaultForm())
}

async function handleSubmit() {
  if (!form.name.trim()) {
    Message.warning('请输入权限名称')
    return
  }
  if (!form.code.trim()) {
    Message.warning('请输入权限编码')
    return
  }

  drawerLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      const payload: PermissionUpdate = {
        name: form.name.trim(),
        path: form.path || undefined,
        component: form.component || undefined,
        icon: form.icon || undefined,
        sort: form.sort,
        status: form.status,
        visible: form.visible,
        cache: form.cache,
        remark: form.remark || undefined,
      }
      await permissionApi.update(editId.value, payload)
      Message.success('更新成功')
    } else {
      const payload: PermissionCreate = {
        parentId: form.parentId,
        name: form.name.trim(),
        code: form.code.trim(),
        type: form.type,
        path: form.path || undefined,
        component: form.component || undefined,
        icon: form.icon || undefined,
        sort: form.sort,
        status: form.status,
        visible: form.visible,
        cache: form.cache,
        remark: form.remark || undefined,
      }
      await permissionApi.create(payload)
      Message.success('创建成功')
    }
    closeDrawer()
    fetchPermissions()
  } catch {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    drawerLoading.value = false
  }
}

async function togglePermissionStatus(permission: Permission) {
  try {
    await permissionApi.update(permission.id, { status: permission.status === 1 ? 0 : 1 })
    Message.success(permission.status === 1 ? '已禁用' : '已启用')
    fetchPermissions()
  } catch {
    Message.error('操作失败')
  }
}

async function deletePermission(permission: Permission) {
  try {
    await permissionApi.delete(permission.id)
    Message.success('删除成功')
    fetchPermissions()
  } catch {
    Message.error('删除失败')
  }
}

onMounted(() => {
  fetchPermissions()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:lock" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">权限管理</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索权限名称或编码..."
            style="width: 240px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-button type="primary" @click="openCreateDrawer()">
            <template #icon><Icon icon="mdi:plus" /></template>
            新增权限
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-table
        :data="permissions"
        :loading="loading"
        :pagination="false"
        row-key="id"
        :default-expand-all-rows="true"
      >
        <template #columns>
          <a-table-column title="权限名称" data-index="name" :width="200">
            <template #cell="{ record }">
              <span class="font-medium text-slate-700 dark:text-slate-200">{{ record.name }}</span>
            </template>
          </a-table-column>
          <a-table-column title="权限编码" data-index="code" :width="180">
            <template #cell="{ record }">
              <a-tag size="small" color="arcoblue">{{ record.code }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="类型" :width="80" align="center">
            <template #cell="{ record }">
              <a-tag :color="typeColorMap[record.type]" size="small">
                {{ record.type === 'menu' ? '菜单' : record.type === 'api' ? 'API' : '按钮' }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="路径" data-index="path" :width="180">
            <template #cell="{ record }">
              <span v-if="record.path" class="text-slate-500 text-sm font-mono">{{ record.path }}</span>
              <span v-else class="text-slate-300">-</span>
            </template>
          </a-table-column>
          <a-table-column title="图标" data-index="icon" :width="80" align="center">
            <template #cell="{ record }">
              <Icon v-if="record.icon" :icon="record.icon" class="text-lg text-slate-500" />
              <span v-else class="text-slate-300">-</span>
            </template>
          </a-table-column>
          <a-table-column title="排序" data-index="sort" :width="70" align="center">
            <template #cell="{ record }">
              <span class="font-mono text-sm">{{ record.sort }}</span>
            </template>
          </a-table-column>
          <a-table-column title="可见" :width="70" align="center">
            <template #cell="{ record }">
              <a-tag v-if="record.visible" color="green" size="small">是</a-tag>
              <a-tag v-else color="gray" size="small">否</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="状态" :width="70" align="center">
            <template #cell="{ record }">
              <a-tag :color="record.status === 1 ? 'green' : 'red'" size="small">
                {{ record.status === 1 ? '启用' : '禁用' }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="180" align="center">
            <template #cell="{ record }">
              <a-space>
                <a-button v-if="record.type === 'menu'" type="text" size="small" @click="openCreateDrawer(record.id)">
                  <template #icon><Icon icon="mdi:plus" class="text-base" /></template>
                </a-button>
                <a-button type="text" size="small" @click="togglePermissionStatus(record)">
                  <template #icon>
                    <Icon :icon="record.status === 1 ? 'mdi:toggle-switch' : 'mdi:toggle-switch-off-outline'" class="text-lg" />
                  </template>
                </a-button>
                <a-button type="text" size="small" @click="openEditDrawer(record)">
                  <template #icon><Icon icon="mdi:pencil" class="text-lg" /></template>
                </a-button>
                <a-popconfirm content="确定删除该权限吗？删除后不可恢复" @ok="deletePermission(record)">
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
      :title="isEdit ? '编辑权限' : '新增权限'"
      :width="480"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="上级权限">
          <a-tree-select
            v-model="form.parentId"
            :data="permissions"
            :field-names="{ key: 'id', title: 'name', children: 'children' }"
            placeholder="请选择上级权限（留空为顶级）"
            allow-clear
          />
        </a-form-item>
        <a-form-item label="权限名称" required>
          <a-input v-model="form.name" placeholder="请输入权限名称" />
        </a-form-item>
        <a-form-item label="权限编码" required>
          <a-input v-model="form.code" placeholder="请输入权限编码，如 system:user:list" :disabled="isEdit" />
        </a-form-item>
        <a-form-item label="权限类型">
          <a-radio-group v-model="form.type" :disabled="isEdit">
            <a-radio v-for="opt in typeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item v-if="form.type === 'menu'" label="路由路径">
          <a-input v-model="form.path" placeholder="请输入路由路径，如 /system/users" />
        </a-form-item>
        <a-form-item v-if="form.type === 'menu'" label="组件路径">
          <a-input v-model="form.component" placeholder="请输入组件路径，如 system/UserList" />
        </a-form-item>
        <a-form-item v-if="form.type === 'menu'" label="图标">
          <a-input v-model="form.icon" placeholder="请输入图标名称，如 mdi:user" />
        </a-form-item>
        <a-form-item label="排序">
          <a-input-number v-model="form.sort" :min="0" :max="999" style="width: 100%" />
        </a-form-item>
        <a-form-item v-if="form.type === 'menu'" label="是否可见">
          <a-switch v-model="form.visible" />
        </a-form-item>
        <a-form-item v-if="form.type === 'menu'" label="是否缓存">
          <a-switch v-model="form.cache" />
        </a-form-item>
        <a-form-item label="状态">
          <a-radio-group v-model="form.status">
            <a-radio :value="1">启用</a-radio>
            <a-radio :value="0">禁用</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model="form.remark" placeholder="请输入备注信息" :auto-size="{ minRows: 2, maxRows: 4 }" />
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