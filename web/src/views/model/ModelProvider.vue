<script setup lang="ts">
import { modelApi } from "@/api/model";
import type { ModelProvider } from "@/types/api";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { onMounted, reactive, ref } from "vue";

const loading = ref(false);
const providers = ref<ModelProvider[]>([]);
const searchKeyword = ref("");
const enabledFilter = ref<boolean | "">("");
const pagination = reactive({ current: 1, pageSize: 10, total: 0 });

const drawerVisible = ref(false);
const drawerLoading = ref(false);
const isEdit = ref(false);
const editId = ref<string | null>(null);

const defaultForm = () => ({
  name: "",
  baseUrl: "",
  apiKey: "",
  description: "",
  enabled: true,
});

const form = reactive(defaultForm());

const enabledOptions = [
  { label: "全部", value: "" },
  { label: "已启用", value: true },
  { label: "已禁用", value: false },
];

async function loadProviders() {
  loading.value = true;
  try {
    const res = await modelApi.getProviders({
      current: pagination.current,
      size: pagination.pageSize,
      nameOrDesc: searchKeyword.value || undefined,
      enabled: enabledFilter.value === "" ? undefined : enabledFilter.value,
    });
    if (res.code === "0000" && res.data) {
      providers.value = res.data.items;
      pagination.total = res.data.total;
    }
  } catch (e) {
    console.error("Failed to load providers:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadProviders();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadProviders();
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size;
  pagination.current = 1;
  loadProviders();
}

function openCreateDrawer() {
  Object.assign(form, defaultForm());
  isEdit.value = false;
  editId.value = null;
  drawerVisible.value = true;
}

async function openEditDrawer(provider: ModelProvider) {
  isEdit.value = true;
  editId.value = provider.id;
  form.name = provider.name;
  form.baseUrl = provider.baseUrl || "";
  form.apiKey = provider.apiKey ? "****" : "";
  form.description = provider.description || "";
  form.enabled = provider.enabled;
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
  Object.assign(form, defaultForm());
}

async function handleSubmit() {
  if (!form.name.trim()) {
    Message.warning("请输入渠道商名称");
    return;
  }
  if (!form.baseUrl.trim()) {
    Message.warning("请输入 API 基础地址");
    return;
  }

  drawerLoading.value = true;
  try {
    const payload: Partial<ModelProvider> = {
      name: form.name.trim(),
      baseUrl: form.baseUrl.trim(),
      description: form.description || undefined,
      enabled: form.enabled,
    };
    if (form.apiKey && form.apiKey !== "****") {
      payload.apiKey = form.apiKey;
    }

    if (isEdit.value && editId.value) {
      await modelApi.updateProvider(editId.value, payload);
      Message.success("更新成功");
    } else {
      if (!form.apiKey.trim()) {
        Message.warning("请输入 API Key");
        drawerLoading.value = false;
        return;
      }
      payload.apiKey = form.apiKey;
      await modelApi.createProvider(payload);
      Message.success("创建成功");
    }

    closeDrawer();
    loadProviders();
  } catch (e) {
    console.error("Failed to save provider:", e);
  } finally {
    drawerLoading.value = false;
  }
}

async function deleteProvider(id: string) {
  try {
    await modelApi.deleteProvider(id);
    Message.success("删除成功");
    loadProviders();
  } catch (e) {
    console.error("Failed to delete provider:", e);
    Message.error("删除失败");
  }
}

async function toggleProviderStatus(provider: ModelProvider) {
  try {
    await modelApi.updateProvider(provider.id, { enabled: !provider.enabled });
    Message.success(provider.enabled ? "已禁用" : "已启用");
    loadProviders();
  } catch (e) {
    console.error("Failed to toggle provider status:", e);
  }
}

onMounted(() => {
  loadProviders();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:cloud-outline" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">模型渠道商管理</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索名称或描述..."
            style="width: 240px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-select v-model="enabledFilter" placeholder="启用状态" style="width: 120px" @change="handleSearch">
            <a-option v-for="opt in enabledOptions" :key="String(opt.value)" :value="opt.value">
              {{ opt.label }}
            </a-option>
          </a-select>
          <a-button type="primary" @click="openCreateDrawer">
            <template #icon><Icon icon="mdi:plus" /></template>
            新增渠道商
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-table
        :data="providers"
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
          <a-table-column title="名称" data-index="name" :width="150">
            <template #cell="{ record }">
              <span class="font-medium text-slate-700 dark:text-slate-200">{{ record.name }}</span>
            </template>
          </a-table-column>
          <a-table-column title="API 地址" data-index="baseUrl" :width="280">
            <template #cell="{ record }">
              <span class="text-sm text-slate-500 dark:text-slate-400 font-mono truncate block max-w-[260px]">
                {{ record.baseUrl }}
              </span>
            </template>
          </a-table-column>
          <a-table-column title="描述" data-index="description" :width="200">
            <template #cell="{ record }">
              <span v-if="record.description" class="text-sm text-slate-600 dark:text-slate-300">
                {{ record.description.length > 30 ? record.description.slice(0, 30) + "..." : record.description }}
              </span>
              <span v-else class="text-slate-300">-</span>
            </template>
          </a-table-column>
          <a-table-column title="状态" data-index="enabled" :width="100" align="center">
            <template #cell="{ record }">
              <a-tag v-if="record.enabled" color="green" size="small">启用</a-tag>
              <a-tag v-else color="red" size="small">禁用</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="创建时间" data-index="createTime" :width="180">
            <template #cell="{ record }">
              <span class="text-sm text-slate-500">{{ record.createTime || "-" }}</span>
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="160" align="center">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="toggleProviderStatus(record)">
                  <template #icon>
                    <Icon
                      :icon="record.enabled ? 'mdi:toggle-switch' : 'mdi:toggle-switch-off-outline'"
                      class="text-lg"
                    />
                  </template>
                </a-button>
                <a-button type="text" size="small" @click="openEditDrawer(record)">
                  <template #icon><Icon icon="mdi:pencil" class="text-lg" /></template>
                </a-button>
                <a-popconfirm content="确定删除此渠道商吗？关联的模型源也将被删除！" @ok="deleteProvider(record.id)">
                  <a-button type="text" size="small" status="danger">
                    <template #icon><Icon icon="mdi:delete" class="text-lg" /></template>
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>

      <div v-if="providers.length === 0 && !loading" class="text-center py-16">
        <div class="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
          <Icon icon="mdi:cloud-off-outline" class="text-4xl text-slate-300 dark:text-slate-500" />
        </div>
        <p class="text-slate-400 dark:text-slate-500 text-lg">暂无渠道商</p>
        <p class="text-slate-300 dark:text-slate-600 text-sm mt-1">点击上方按钮添加第一个渠道商</p>
      </div>
    </div>

    <a-drawer
      v-model:visible="drawerVisible"
      :title="isEdit ? '编辑渠道商' : '新增渠道商'"
      :width="480"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="渠道商名称" required>
          <a-input v-model="form.name" placeholder="如：OpenAI、阿里云、Azure" />
        </a-form-item>
        <a-form-item label="API 基础地址" required>
          <a-input v-model="form.baseUrl" placeholder="如：https://api.openai.com/v1" />
        </a-form-item>
        <a-form-item :label="isEdit ? 'API Key（留空保持不变）' : 'API Key'" :required="!isEdit">
          <a-input-password
            v-model="form.apiKey"
            :placeholder="isEdit ? '留空保持原有密钥不变' : '请输入 API Key'"
            allow-clear
          />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea
            v-model="form.description"
            placeholder="渠道商描述信息"
            :auto-size="{ minRows: 2, maxRows: 4 }"
          />
        </a-form-item>
        <a-form-item label="启用状态">
          <a-switch v-model="form.enabled" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="closeDrawer">取消</a-button>
          <a-button type="primary" :loading="drawerLoading" @click="handleSubmit">
            {{ isEdit ? "更新" : "创建" }}
          </a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>