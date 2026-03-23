<script setup lang="ts">
import { expressionApi } from "@/api/expression";
import type { RobotExpression, RobotExpressionCreate } from "@/types/api";
import { formatDateTime } from "@/utils/format";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { onMounted, reactive, ref, watch } from "vue";

const loading = ref(false);
const expressions = ref<RobotExpression[]>([]);
const searchKeyword = ref("");
const isActiveFilter = ref<boolean | "">("");
const pagination = reactive({ current: 1, pageSize: 10, total: 0 });
const selectedRowKeys = ref<number[]>([]);

const drawerVisible = ref(false);
const drawerLoading = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);

const exportLoading = ref(false);
const importLoading = ref(false);
const importDrawerVisible = ref(false);

const defaultForm = () => ({
  name: "",
  code: "",
  description: "",
  isActive: true,
});

const form = reactive(defaultForm());

const isActiveOptions = [
  { label: "全部", value: "" },
  { label: "已启用", value: true },
  { label: "已禁用", value: false },
];

async function loadExpressions() {
  loading.value = true;
  try {
    const res = await expressionApi.getExpressions({
      current: pagination.current,
      size: pagination.pageSize,
      nameOrCode: searchKeyword.value || undefined,
      isActive: isActiveFilter.value === "" ? undefined : isActiveFilter.value,
    });
    if (res.code === "0000" && res.data) {
      expressions.value = res.data.items;
      pagination.total = res.data.total;
    }
  } catch (e) {
    console.error("Failed to load expressions:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadExpressions();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadExpressions();
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size;
  pagination.current = 1;
  loadExpressions();
}

function openCreateDrawer() {
  Object.assign(form, defaultForm());
  isEdit.value = false;
  editId.value = null;
  drawerVisible.value = true;
}

function openEditDrawer(expression: RobotExpression) {
  isEdit.value = true;
  editId.value = expression.id;
  form.name = expression.name;
  form.code = expression.code;
  form.description = expression.description || "";
  form.isActive = expression.isActive;
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
  Object.assign(form, defaultForm());
}

async function handleSubmit() {
  if (!form.name.trim()) {
    Message.warning("请输入表情名称");
    return;
  }
  if (!form.code.trim()) {
    Message.warning("请输入表情代码");
    return;
  }

  drawerLoading.value = true;
  try {
    const payload: RobotExpressionCreate = {
      name: form.name.trim(),
      code: form.code.trim(),
      description: form.description || undefined,
      isActive: form.isActive,
    };

    if (isEdit.value && editId.value) {
      await expressionApi.updateExpression(editId.value, payload);
      Message.success("更新成功");
    } else {
      await expressionApi.createExpression(payload);
      Message.success("创建成功");
    }

    closeDrawer();
    loadExpressions();
  } catch (e) {
    console.error("Failed to save expression:", e);
  } finally {
    drawerLoading.value = false;
  }
}

async function deleteExpression(id: number) {
  try {
    await expressionApi.deleteExpression(id);
    Message.success("删除成功");
    loadExpressions();
  } catch (e) {
    console.error("Failed to delete expression:", e);
    Message.error("删除失败");
  }
}

async function toggleExpressionStatus(expression: RobotExpression) {
  try {
    await expressionApi.updateExpression(expression.id, { isActive: !expression.isActive });
    Message.success(expression.isActive ? "已禁用" : "已启用");
    loadExpressions();
  } catch (e) {
    console.error("Failed to toggle expression status:", e);
  }
}

function handleSelectionChange(keys: (string | number)[]) {
  selectedRowKeys.value = keys as number[];
}

async function handleExport(format: "xlsx" | "csv") {
  exportLoading.value = true;
  try {
    const response = await expressionApi.exportExpressions({
      format,
      expressionIds: selectedRowKeys.value.length > 0 ? selectedRowKeys.value : undefined,
      isActive:
        selectedRowKeys.value.length > 0
          ? undefined
          : isActiveFilter.value === ""
          ? undefined
          : isActiveFilter.value,
    });
    const blob = new Blob([response.data], {
      type:
        format === "csv"
          ? "text/csv"
          : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = format === "csv" ? "expressions.csv" : "expressions.xlsx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    Message.success("导出成功");
  } catch (e) {
    console.error("Failed to export expressions:", e);
    Message.error("导出失败");
  } finally {
    exportLoading.value = false;
  }
}

async function handleDownloadTemplate() {
  try {
    const response = await expressionApi.downloadTemplate();
    const blob = new Blob([response.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "expression_template.xlsx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (e) {
    console.error("Failed to download template:", e);
    Message.error("下载模板失败");
  }
}

function openImportDrawer() {
  importDrawerVisible.value = true;
}

function closeImportDrawer() {
  importDrawerVisible.value = false;
}

async function handleImport(file: File) {
  importLoading.value = true;
  try {
    const result = await expressionApi.importExpressions(file);
    if (result.code === "0000") {
      Message.success(result.msg);
      closeImportDrawer();
      loadExpressions();
    } else {
      Message.error(result.msg);
    }
  } catch (e) {
    console.error("Failed to import expressions:", e);
    Message.error("导入失败");
  } finally {
    importLoading.value = false;
  }
  return false;
}

function handleUploadRequest(option: { fileItem: { file: File } }) {
  handleImport(option.fileItem.file);
}

watch(isActiveFilter, () => {
  pagination.current = 1;
  loadExpressions();
});

onMounted(() => {
  loadExpressions();
});
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="border-b border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
      <div class="flex items-center justify-between gap-4">
        <div class="flex flex-1 items-center gap-3">
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索表情名称或代码..."
            style="width: 280px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-select v-model="isActiveFilter" placeholder="启用状态" style="width: 120px">
            <a-option
              v-for="opt in isActiveOptions"
              :key="String(opt.value)"
              :value="opt.value"
            >
              {{ opt.label }}
            </a-option>
          </a-select>
          <a-dropdown>
            <a-button type="outline" :loading="exportLoading">
              <template #icon><Icon icon="mdi:download" /></template>
              导出
            </a-button>
            <template #content>
              <a-doption @click="handleExport('xlsx')">
                <template #icon><Icon icon="mdi:file-excel" /></template>
                导出为 Excel
              </a-doption>
              <a-doption @click="handleExport('csv')">
                <template #icon><Icon icon="mdi:file-export" /></template>
                导出为 CSV
              </a-doption>
            </template>
          </a-dropdown>
          <a-button type="outline" @click="openImportDrawer">
            <template #icon><Icon icon="mdi:upload" /></template>
            导入
          </a-button>
        </div>
        <a-button type="primary" @click="openCreateDrawer">
          <template #icon><Icon icon="mdi:plus" /></template>
          新增表情
        </a-button>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-4">
      <a-table
        :data="expressions"
        :loading="loading"
        :pagination="{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showTotal: true,
          showPageSize: true,
        }"
        :row-selection="{
          type: 'checkbox',
          selectedRowKeys: selectedRowKeys,
          showCheckedAll: true,
        }"
        row-key="id"
        @selection-change="handleSelectionChange"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
      >
        <template #columns>
          <a-table-column title="名称" data-index="name" :width="140">
            <template #cell="{ record }">
              <span class="font-medium text-slate-700 dark:text-slate-200">{{
                record.name
              }}</span>
            </template>
          </a-table-column>
          <a-table-column title="代码" data-index="code" :width="140">
            <template #cell="{ record }">
              <a-tag size="small" color="arcoblue">{{ record.code }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="描述" data-index="description" :width="240">
            <template #cell="{ record }">
              <span
                v-if="record.description"
                class="text-sm text-slate-600 dark:text-slate-300"
              >
                {{
                  record.description.length > 30
                    ? record.description.slice(0, 30) + "..."
                    : record.description
                }}
              </span>
              <span v-else class="text-slate-300">-</span>
            </template>
          </a-table-column>
          <a-table-column title="状态" data-index="isActive" :width="100" align="center">
            <template #cell="{ record }">
              <a-tag v-if="record.isActive" color="green" size="small">启用</a-tag>
              <a-tag v-else color="red" size="small">禁用</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="创建时间" data-index="createTime" :width="180">
            <template #cell="{ record }">
              <span class="text-sm text-slate-500">{{ formatDateTime(record.createTime) }}</span>
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="160" align="center">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="toggleExpressionStatus(record)">
                  <template #icon>
                    <Icon
                      :icon="
                        record.isActive
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
                  content="确定删除此表情吗？"
                  popup-container="body"
                  @ok="deleteExpression(record.id)"
                >
                  <a-button type="text" size="small" status="danger">
                    <template #icon><Icon icon="mdi:delete" class="text-lg"/></template>
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
      :title="isEdit ? '编辑表情' : '新增表情'"
      :width="420"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="表情名称" required>
          <a-input v-model="form.name" placeholder="请输入表情名称" />
        </a-form-item>
        <a-form-item label="表情代码" required>
          <a-input v-model="form.code" placeholder="请输入表情代码，如 Happy" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea
            v-model="form.description"
            placeholder="表情描述信息"
            :auto-size="{ minRows: 2, maxRows: 4 }"
          />
        </a-form-item>
        <a-form-item label="启用状态">
          <a-switch v-model="form.isActive" />
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

    <a-drawer
      v-model:visible="importDrawerVisible"
      title="导入表情"
      :width="400"
      :footer="false"
      @cancel="closeImportDrawer"
    >
      <div class="space-y-4">
        <a-alert type="info">
          <template #title>导入说明</template>
          <ul class="list-disc pl-4 text-sm">
            <li>支持 Excel (.xlsx, .xls) 和 CSV 文件</li>
            <li>根据「代码」字段判断，存在则更新，不存在则新增</li>
          </ul>
        </a-alert>

        <a-upload
          :auto-upload="true"
          :show-file-list="false"
          accept=".xlsx,.xls,.csv"
          :custom-request="handleUploadRequest"
        >
          <template #upload-button>
            <a-button type="primary" :loading="importLoading">
              <template #icon><Icon icon="mdi:upload" /></template>
              选择文件导入
            </a-button>
          </template>
        </a-upload>

        <a-divider />

        <div class="text-center">
          <a-button type="text" @click="handleDownloadTemplate">
            <template #icon><Icon icon="mdi:download" /></template>
            下载导入模板
          </a-button>
        </div>
      </div>
    </a-drawer>
  </div>
</template>