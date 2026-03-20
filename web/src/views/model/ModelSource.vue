<script setup lang="ts">
import { modelApi } from "@/api/model";
import type { ModelProvider, ModelSource } from "@/types/api";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref, watch } from "vue";

const loading = ref(false);
const sources = ref<ModelSource[]>([]);
const providers = ref<ModelProvider[]>([]);
const searchKeyword = ref("");
const providerFilter = ref<number | undefined>();
const enabledFilter = ref<boolean | "">("");
const healthyFilter = ref<boolean | "">("");
const pagination = reactive({ current: 1, pageSize: 10, total: 0 });

const drawerVisible = ref(false);
const drawerLoading = ref(false);
const isEdit = ref(false);
const editId = ref<string | null>(null);

const defaultForm = () => ({
  name: "",
  alias: "",
  providerId: undefined as number | undefined,
  enabled: true,
  priority: 0,
  generationKwargs: "",
});

const form = reactive(defaultForm());

const enabledOptions = [
  { label: "全部", value: "" },
  { label: "已启用", value: true },
  { label: "已禁用", value: false },
];

const healthyOptions = [
  { label: "全部", value: "" },
  { label: "健康", value: true },
  { label: "异常", value: false },
];

const providerOptions = computed(() => {
  return providers.value.map((p) => ({
    label: p.name,
    value: p.id,
  }));
});

async function loadProviders() {
  try {
    const res = await modelApi.getProviders({ current: 1, size: 100 });
    if (res.code === "0000" && res.data) {
      providers.value = res.data.items;
    }
  } catch (e) {
    console.error("Failed to load providers:", e);
  }
}

async function loadSources() {
  loading.value = true;
  try {
    const res = await modelApi.getSources({
      current: pagination.current,
      size: pagination.pageSize,
      nameOrAlias: searchKeyword.value || undefined,
      providerId: providerFilter.value,
      enabled: enabledFilter.value === "" ? undefined : enabledFilter.value,
      healthy: healthyFilter.value === "" ? undefined : healthyFilter.value,
    });
    if (res.code === "0000" && res.data) {
      sources.value = res.data.items;
      pagination.total = res.data.total;
    }
  } catch (e) {
    console.error("Failed to load sources:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadSources();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadSources();
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size;
  pagination.current = 1;
  loadSources();
}

function openCreateDrawer() {
  Object.assign(form, defaultForm());
  isEdit.value = false;
  editId.value = null;
  drawerVisible.value = true;
}

async function openEditDrawer(source: ModelSource) {
  isEdit.value = true;
  editId.value = source.id;
  form.name = source.name;
  form.alias = source.alias || "";
  form.providerId = source.providerId;
  form.enabled = source.enabled;
  form.priority = source.priority || 0;
  form.generationKwargs = source.generationKwargs
    ? JSON.stringify(source.generationKwargs, null, 2)
    : "";
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
  Object.assign(form, defaultForm());
}

function validateJson(str: string): boolean {
  if (!str.trim()) return true;
  try {
    JSON.parse(str);
    return true;
  } catch {
    return false;
  }
}

async function handleSubmit() {
  if (!form.name.trim()) {
    Message.warning("请输入模型名称");
    return;
  }
  if (!form.providerId) {
    Message.warning("请选择所属渠道商");
    return;
  }
  if (form.generationKwargs && !validateJson(form.generationKwargs)) {
    Message.warning("模型参数 JSON 格式不正确");
    return;
  }

  drawerLoading.value = true;
  try {
    const payload: Partial<ModelSource> = {
      name: form.name.trim(),
      alias: form.alias.trim() || undefined,
      providerId: form.providerId,
      enabled: form.enabled,
      priority: form.priority,
      generationKwargs: form.generationKwargs
        ? JSON.parse(form.generationKwargs)
        : undefined,
    };

    if (isEdit.value && editId.value) {
      await modelApi.updateSource(editId.value, payload);
      Message.success("更新成功");
    } else {
      await modelApi.createSource(payload);
      Message.success("创建成功");
    }

    closeDrawer();
    loadSources();
  } catch (e) {
    console.error("Failed to save source:", e);
  } finally {
    drawerLoading.value = false;
  }
}

async function deleteSource(id: string) {
  try {
    await modelApi.deleteSource(id);
    Message.success("删除成功");
    loadSources();
  } catch (e) {
    console.error("Failed to delete source:", e);
    Message.error("删除失败");
  }
}

async function toggleSourceStatus(source: ModelSource) {
  try {
    await modelApi.updateSource(source.id, { enabled: !source.enabled });
    Message.success(source.enabled ? "已禁用" : "已启用");
    loadSources();
  } catch (e) {
    console.error("Failed to toggle source status:", e);
  }
}

function getProviderName(providerId: number): string {
  const provider = providers.value.find((p) => String(p.id) === String(providerId));
  return provider?.name || "-";
}

watch([enabledFilter, healthyFilter, providerFilter], () => {
  pagination.current = 1;
  loadSources();
});

onMounted(() => {
  loadProviders();
  loadSources();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div
      class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
    >
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:cube-outline" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">模型源管理</h1>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索名称或别名..."
            style="width: 200px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-select
            v-model="providerFilter"
            placeholder="渠道商"
            style="width: 140px"
            allow-clear
          >
            <a-option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </a-option>
          </a-select>
          <a-select v-model="enabledFilter" placeholder="启用状态" style="width: 110px">
            <a-option
              v-for="opt in enabledOptions"
              :key="String(opt.value)"
              :value="opt.value"
            >
              {{ opt.label }}
            </a-option>
          </a-select>
          <a-select v-model="healthyFilter" placeholder="健康状态" style="width: 110px">
            <a-option
              v-for="opt in healthyOptions"
              :key="String(opt.value)"
              :value="opt.value"
            >
              {{ opt.label }}
            </a-option>
          </a-select>
          <a-button type="primary" @click="openCreateDrawer">
            <template #icon><Icon icon="mdi:plus" /></template>
            新增模型源
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-table
        :data="sources"
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
          <a-table-column title="模型名称" data-index="name" :width="180">
            <template #cell="{ record }">
              <span class="font-medium text-slate-700 dark:text-slate-200">{{
                record.name
              }}</span>
            </template>
          </a-table-column>
          <a-table-column title="别名" data-index="alias" :width="140">
            <template #cell="{ record }">
              <a-tag v-if="record.alias" color="arcoblue" size="small">{{
                record.alias
              }}</a-tag>
              <span v-else class="text-slate-300">-</span>
            </template>
          </a-table-column>
          <a-table-column title="渠道商" data-index="providerId" :width="120">
            <template #cell="{ record }">
              <span class="text-sm text-slate-600 dark:text-slate-300">
                {{ getProviderName(record.providerId) }}
              </span>
            </template>
          </a-table-column>
          <a-table-column title="优先级" data-index="priority" :width="80" align="center">
            <template #cell="{ record }">
              <span class="text-sm font-mono">{{ record.priority ?? 0 }}</span>
            </template>
          </a-table-column>
          <a-table-column
            title="健康状态"
            data-index="healthy"
            :width="100"
            align="center"
          >
            <template #cell="{ record }">
              <a-tag v-if="record.healthy" color="green" size="small">健康</a-tag>
              <a-tag v-else color="red" size="small">异常</a-tag>
            </template>
          </a-table-column>
          <a-table-column
            title="延迟"
            data-index="lastLatency"
            :width="100"
            align="center"
          >
            <template #cell="{ record }">
              <span
                v-if="record.lastLatency != null"
                class="text-sm text-slate-600 dark:text-slate-300"
              >
                {{ record.lastLatency.toFixed(2) }}ms
              </span>
              <span v-else class="text-slate-300">-</span>
            </template>
          </a-table-column>
          <a-table-column
            title="失败次数"
            data-index="failureCount"
            :width="90"
            align="center"
          >
            <template #cell="{ record }">
              <a-tag v-if="record.failureCount > 0" color="orange" size="small">
                {{ record.failureCount }}
              </a-tag>
              <span v-else class="text-slate-400">0</span>
            </template>
          </a-table-column>
          <a-table-column
            title="启用状态"
            data-index="enabled"
            :width="90"
            align="center"
          >
            <template #cell="{ record }">
              <a-tag v-if="record.enabled" color="green" size="small">启用</a-tag>
              <a-tag v-else color="gray" size="small">禁用</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="160" align="center">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="toggleSourceStatus(record)">
                  <template #icon>
                    <Icon
                      :icon="
                        record.enabled
                          ? 'mdi:toggle-switch'
                          : 'mdi:toggle-switch-off-outline'
                      "
                      class="text-lg"
                    />
                  </template>
                </a-button>
                <a-button type="text" size="small" @click="openEditDrawer(record)">
                  <template #icon><Icon icon="mdi:pencil" class="text-lg" /></template>
                </a-button>
                <a-popconfirm
                  content="确定删除此模型源吗？"
                  @ok="deleteSource(record.id)"
                >
                  <a-button type="text" size="small" status="danger">
                    <template #icon><Icon icon="mdi:delete" class="text-lg" /></template>
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>

      <div v-if="sources.length === 0 && !loading" class="text-center py-16">
        <div
          class="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center"
        >
          <Icon
            icon="mdi:cube-outline"
            class="text-4xl text-slate-300 dark:text-slate-500"
          />
        </div>
        <p class="text-slate-400 dark:text-slate-500 text-lg">暂无模型源</p>
        <p class="text-slate-300 dark:text-slate-600 text-sm mt-1">
          点击上方按钮添加第一个模型源
        </p>
      </div>
    </div>

    <a-drawer
      v-model:visible="drawerVisible"
      :title="isEdit ? '编辑模型源' : '新增模型源'"
      :width="500"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="模型名称" required>
          <a-input v-model="form.name" placeholder="如：gpt-4、qwen-turbo" />
        </a-form-item>
        <a-form-item label="模型别名">
          <a-input v-model="form.alias" placeholder="如：GPT-4、通义千问" />
        </a-form-item>
        <a-form-item label="所属渠道商" required>
          <a-select v-model="form.providerId" placeholder="请选择渠道商">
            <a-option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="优先级">
          <a-input-number
            v-model="form.priority"
            :min="0"
            :max="100"
            style="width: 100%"
          />
          <template #extra>
            <span class="text-xs text-slate-400">数值越大优先级越高</span>
          </template>
        </a-form-item>
        <a-form-item label="模型参数 (JSON)">
          <a-textarea
            v-model="form.generationKwargs"
            placeholder='如：{"temperature": 0.7, "max_tokens": 2048}'
            :auto-size="{ minRows: 3, maxRows: 8 }"
          />
          <template #extra>
            <span class="text-xs text-slate-400">可选，JSON 格式的模型调用参数</span>
          </template>
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
