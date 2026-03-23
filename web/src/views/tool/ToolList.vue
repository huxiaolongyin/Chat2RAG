<script setup lang="ts">
import { toolApi } from "@/api/tool";
import type {
  ApiToolCreate,
  ApiToolUpdate,
  McpServerCreate,
  McpServerUpdate,
  McpType,
  Tool,
  ToolMethod,
  ToolType,
} from "@/types/api";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref, watch } from "vue";

const loading = ref(false);
const tools = ref<Tool[]>([]);
const selectedType = ref<ToolType>("all");
const searchKeyword = ref("");
const isActiveFilter = ref<boolean | "">("");
const pagination = reactive({ current: 1, pageSize: 10, total: 0 });

const drawerVisible = ref(false);
const drawerLoading = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);
const formTab = ref<"api" | "mcp">("api");

const jsonEditorVisible = ref(false);
const jsonEditorValue = ref("");
const jsonEditorField = ref<"parameters" | "env">("parameters");

const methodOptions: { label: string; value: ToolMethod }[] = [
  { label: "GET", value: "GET" },
  { label: "POST", value: "POST" },
  { label: "PUT", value: "PUT" },
  { label: "DELETE", value: "DELETE" },
];

const mcpTypeOptions: { label: string; value: McpType }[] = [
  { label: "stdio", value: "stdio" },
  { label: "sse", value: "sse" },
];

const isActiveOptions = [
  { label: "全部", value: "" },
  { label: "已启用", value: true },
  { label: "已禁用", value: false },
];

const defaultApiForm = (): {
  name: string;
  description: string;
  url: string;
  method: ToolMethod;
  parameters: Record<string, unknown>;
} => ({
  name: "",
  description: "",
  url: "",
  method: "GET",
  parameters: {},
});

const defaultMcpForm = (): {
  name: string;
  mcpType: McpType;
  url: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  isActive: boolean;
} => ({
  name: "",
  mcpType: "stdio",
  url: "",
  command: "",
  args: [],
  env: {},
  isActive: true,
});

const apiForm = reactive(defaultApiForm());
const mcpForm = reactive(defaultMcpForm());

const sidebarItems = computed(() => [
  { value: "all", label: "全部工具", icon: "mdi:tools" },
  { value: "api", label: "API 工具", icon: "mdi:api" },
  { value: "mcp", label: "MCP 服务", icon: "mdi:server" },
]);

async function loadTools() {
  loading.value = true;
  try {
    const res = await toolApi.getTools({
      current: pagination.current,
      size: pagination.pageSize,
      toolType: selectedType.value,
      toolName: searchKeyword.value || undefined,
      isActive: isActiveFilter.value === "" ? undefined : isActiveFilter.value,
    });
    if (res.code === "0000" && res.data) {
      tools.value = res.data.items;
      pagination.total = res.data.total;
    }
  } catch (e) {
    console.error("Failed to load tools:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadTools();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadTools();
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size;
  pagination.current = 1;
  loadTools();
}

function selectType(type: ToolType) {
  selectedType.value = type;
  pagination.current = 1;
  loadTools();
}

function openCreateDrawer() {
  isEdit.value = false;
  editId.value = null;
  formTab.value = "api";
  Object.assign(apiForm, defaultApiForm());
  Object.assign(mcpForm, defaultMcpForm());
  drawerVisible.value = true;
}

async function openEditDrawer(tool: Tool) {
  isEdit.value = true;
  editId.value = tool.id;
  formTab.value = tool.toolType;

  if (tool.toolType === "api") {
    Object.assign(apiForm, {
      name: tool.name,
      description: tool.description || "",
      url: tool.url || "",
      method: tool.method || "GET",
      parameters: tool.parameters || {},
    });
  } else {
    Object.assign(mcpForm, {
      name: tool.name,
      mcpType: (tool as Tool & { mcpType?: McpType }).mcpType || "stdio",
      url: tool.url || "",
      command: tool.command || "",
      args: tool.args || [],
      env: {},
      isActive: tool.isActive,
    });
  }
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
  Object.assign(apiForm, defaultApiForm());
  Object.assign(mcpForm, defaultMcpForm());
}

async function handleSubmit() {
  if (formTab.value === "api") {
    if (!apiForm.name.trim()) {
      Message.warning("请输入工具名称");
      return;
    }
  } else {
    if (!mcpForm.name.trim()) {
      Message.warning("请输入服务名称");
      return;
    }
  }

  drawerLoading.value = true;
  try {
    if (formTab.value === "api") {
      const payload: ApiToolCreate | ApiToolUpdate = {
        name: apiForm.name.trim(),
        description: apiForm.description || undefined,
        url: apiForm.url || undefined,
        method: apiForm.method,
        parameters:
          Object.keys(apiForm.parameters).length > 0 ? apiForm.parameters : undefined,
      };

      if (isEdit.value && editId.value) {
        await toolApi.updateApiTool(editId.value, payload);
        Message.success("更新成功");
      } else {
        await toolApi.createApiTool(payload as ApiToolCreate);
        Message.success("创建成功");
      }
    } else {
      const payload: McpServerCreate | McpServerUpdate = {
        name: mcpForm.name.trim(),
        mcpType: mcpForm.mcpType,
        url: mcpForm.url || undefined,
        command: mcpForm.command || undefined,
        args: mcpForm.args.length > 0 ? mcpForm.args : undefined,
        env: Object.keys(mcpForm.env).length > 0 ? mcpForm.env : undefined,
        isActive: mcpForm.isActive,
      };

      if (isEdit.value && editId.value) {
        await toolApi.updateMcpServer(editId.value, payload);
        Message.success("更新成功");
      } else {
        await toolApi.createMcpServer(payload as McpServerCreate);
        Message.success("创建成功");
      }
    }

    closeDrawer();
    loadTools();
  } catch (e) {
    console.error("Failed to save tool:", e);
  } finally {
    drawerLoading.value = false;
  }
}

async function deleteTool(tool: Tool) {
  try {
    await toolApi.deleteTool(tool.id, tool.toolType);
    Message.success("删除成功");
    loadTools();
  } catch (e) {
    console.error("Failed to delete tool:", e);
    Message.error("删除失败");
  }
}

async function toggleToolStatus(tool: Tool) {
  try {
    if (tool.toolType === "api") {
      await toolApi.updateApiTool(tool.id, { isActive: !tool.isActive });
    } else {
      await toolApi.updateMcpServer(tool.id, { isActive: !tool.isActive });
    }
    Message.success(tool.isActive ? "已禁用" : "已启用");
    loadTools();
  } catch (e) {
    console.error("Failed to toggle tool status:", e);
  }
}

async function syncMcpTools(serverId: number) {
  try {
    const res = await toolApi.syncMcpTools(serverId);
    if (res.code === "0000" && res.data) {
      Message.success(`成功同步 ${res.data.toolCount} 个工具`);
      loadTools();
    }
  } catch (e) {
    console.error("Failed to sync MCP tools:", e);
    Message.error("同步失败");
  }
}

function openJsonEditor(field: "parameters" | "env") {
  jsonEditorField.value = field;
  if (field === "parameters") {
    jsonEditorValue.value = JSON.stringify(apiForm.parameters, null, 2);
  } else {
    jsonEditorValue.value = JSON.stringify(mcpForm.env, null, 2);
  }
  jsonEditorVisible.value = true;
}

function saveJsonEditor() {
  try {
    const parsed = JSON.parse(jsonEditorValue.value || "{}");
    if (jsonEditorField.value === "parameters") {
      apiForm.parameters = parsed;
    } else {
      mcpForm.env = parsed;
    }
    jsonEditorVisible.value = false;
  } catch {
    Message.error("JSON 格式错误");
  }
}

function addArg() {
  mcpForm.args.push("");
}

function removeArg(index: number) {
  mcpForm.args.splice(index, 1);
}

watch(isActiveFilter, () => {
  pagination.current = 1;
  loadTools();
});

onMounted(() => {
  loadTools();
});
</script>

<template>
  <div class="flex h-full">
    <aside
      class="w-56 flex-shrink-0 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col"
    >
      <div class="p-4 border-b border-slate-200 dark:border-slate-700">
        <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-200">工具类型</h2>
      </div>
      <div class="flex-1 overflow-y-auto">
        <div
          v-for="item in sidebarItems"
          :key="item.value"
          class="px-4 py-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
          :class="{
            'bg-primary/5 border-r-2 border-primary': selectedType === item.value,
          }"
          @click="selectType(item.value as ToolType)"
        >
          <div class="flex items-center gap-2">
            <Icon :icon="item.icon" class="text-lg text-slate-500 dark:text-slate-400" />
            <span class="text-sm text-slate-700 dark:text-slate-200">{{
              item.label
            }}</span>
          </div>
        </div>
      </div>
    </aside>

    <main class="flex-1 flex flex-col overflow-hidden">
      <div
        class="p-4 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
      >
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3 flex-1">
            <a-input-search
              v-model="searchKeyword"
              placeholder="搜索工具名称或描述..."
              style="width: 280px"
              @search="handleSearch"
              @press-enter="handleSearch"
            />
            <a-select
              v-model="isActiveFilter"
              placeholder="启用状态"
              style="width: 120px"
            >
              <a-option
                v-for="opt in isActiveOptions"
                :key="String(opt.value)"
                :value="opt.value"
              >
                {{ opt.label }}
              </a-option>
            </a-select>
          </div>
          <a-button type="primary" @click="openCreateDrawer">
            <template #icon><Icon icon="mdi:plus" /></template>
            新增工具
          </a-button>
        </div>
      </div>

      <div class="flex-1 overflow-auto p-4">
        <a-table
          :data="tools"
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
            <a-table-column title="名称" data-index="name" :width="240">
              <template #cell="{ record }">
                <div class="flex items-center gap-2">
                  <Icon
                    :icon="record.toolType === 'api' ? 'mdi:api' : 'mdi:server'"
                    class="text-lg"
                    :class="
                      record.toolType === 'api' ? 'text-blue-500' : 'text-green-500'
                    "
                  />
                  <span class="font-medium text-slate-700 dark:text-slate-200">{{
                    record.name
                  }}</span>
                </div>
              </template>
            </a-table-column>
            <a-table-column title="描述" data-index="description" :width="480">
              <template #cell="{ record }">
                <a-tooltip
                  v-if="record.description && record.description.length > 30"
                  :content="record.description"
                >
                  <span class="text-sm text-slate-600 dark:text-slate-300 cursor-help">
                    {{ record.description.slice(0, 30) + "..." }}
                  </span>
                </a-tooltip>
                <span
                  v-else-if="record.description"
                  class="text-sm text-slate-600 dark:text-slate-300"
                >
                  {{ record.description }}
                </span>
                <span v-else class="text-slate-300">-</span>
              </template>
            </a-table-column>
            <a-table-column
              title="类型"
              data-index="toolType"
              :width="100"
              align="center"
            >
              <template #cell="{ record }">
                <a-tag
                  :color="record.toolType === 'api' ? 'arcoblue' : 'green'"
                  size="small"
                >
                  {{ record.toolType === "api" ? "API" : "MCP" }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="地址" data-index="url" :width="200">
              <template #cell="{ record }">
                <span
                  v-if="record.url"
                  class="text-xs text-slate-500 dark:text-slate-400 truncate"
                >
                  {{
                    record.url.length > 25 ? record.url.slice(0, 25) + "..." : record.url
                  }}
                </span>
                <span
                  v-else-if="record.command"
                  class="text-xs text-slate-500 dark:text-slate-400"
                >
                  {{ record.command }}
                </span>
                <span v-else class="text-slate-300">-</span>
              </template>
            </a-table-column>
            <a-table-column title="状态" data-index="isActive" :width="80" align="center">
              <template #cell="{ record }">
                <a-tag v-if="record.isActive" color="green" size="small">启用</a-tag>
                <a-tag v-else color="red" size="small">禁用</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" :width="180" align="center">
              <template #cell="{ record }">
                <a-space>
                  <a-button type="text" size="small" @click="toggleToolStatus(record)">
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
                  <a-button
                    v-if="record.toolType === 'mcp'"
                    type="text"
                    size="small"
                    @click="syncMcpTools(record.id)"
                  >
                    <template #icon><Icon icon="mdi:sync" class="text-lg" /></template>
                  </a-button>
                  <a-button type="text" size="small" @click="openEditDrawer(record)">
                    <template #icon><Icon icon="mdi:pencil" class="text-lg" /></template>
                  </a-button>
                  <a-popconfirm
                    content="确定删除此工具吗？"
                    popup-container="body"
                    @ok="deleteTool(record)"
                  >
                    <a-button type="text" size="small" status="danger">
                      <template #icon
                        ><Icon icon="mdi:delete" class="text-lg"
                      /></template>
                    </a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>
    </main>

    <a-drawer
      v-model:visible="drawerVisible"
      :title="isEdit ? '编辑工具' : '新增工具'"
      :width="500"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-tabs v-model:active-key="formTab" :disabled="isEdit">
        <a-tab-pane key="api" title="API 工具">
          <a-form :model="apiForm" layout="vertical" class="mt-4">
            <a-form-item label="工具名称" required>
              <a-input v-model="apiForm.name" placeholder="请输入工具名称" />
            </a-form-item>
            <a-form-item label="描述">
              <a-textarea
                v-model="apiForm.description"
                placeholder="请输入工具描述"
                :auto-size="{ minRows: 2, maxRows: 4 }"
              />
            </a-form-item>
            <a-form-item label="URL">
              <a-input v-model="apiForm.url" placeholder="请输入 API URL" />
            </a-form-item>
            <a-form-item label="HTTP 方法">
              <a-select v-model="apiForm.method">
                <a-option
                  v-for="opt in methodOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </a-option>
              </a-select>
            </a-form-item>
            <a-form-item label="请求参数">
              <a-button type="dashed" long @click="openJsonEditor('parameters')">
                <template #icon><Icon icon="mdi:code-json" /></template>
                编辑参数 (JSON)
              </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="mcp" title="MCP 服务">
          <a-form :model="mcpForm" layout="vertical" class="mt-4">
            <a-form-item label="服务名称" required>
              <a-input v-model="mcpForm.name" placeholder="请输入服务名称" />
            </a-form-item>
            <a-form-item label="MCP 类型">
              <a-select v-model="mcpForm.mcpType">
                <a-option
                  v-for="opt in mcpTypeOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </a-option>
              </a-select>
            </a-form-item>
            <a-form-item v-if="mcpForm.mcpType === 'sse'" label="URL">
              <a-input v-model="mcpForm.url" placeholder="请输入 SSE URL" />
            </a-form-item>
            <a-form-item v-if="mcpForm.mcpType === 'stdio'" label="启动命令">
              <a-input v-model="mcpForm.command" placeholder="请输入启动命令" />
            </a-form-item>
            <a-form-item v-if="mcpForm.mcpType === 'stdio'" label="命令参数">
              <div class="space-y-2">
                <div v-for="(_, index) in mcpForm.args" :key="index" class="flex gap-2">
                  <a-input
                    v-model="mcpForm.args[index]"
                    placeholder="输入参数"
                    class="flex-1"
                  />
                  <a-button type="text" status="danger" @click="removeArg(index)">
                    <template #icon><Icon icon="mdi:close" /></template>
                  </a-button>
                </div>
                <a-button type="dashed" long @click="addArg">
                  <template #icon><Icon icon="mdi:plus" /></template>
                  添加参数
                </a-button>
              </div>
            </a-form-item>
            <a-form-item label="环境变量">
              <a-button type="dashed" long @click="openJsonEditor('env')">
                <template #icon><Icon icon="mdi:code-json" /></template>
                编辑环境变量 (JSON)
              </a-button>
            </a-form-item>
            <a-form-item label="启用状态">
              <a-switch v-model="mcpForm.isActive" />
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
      <template #footer>
        <a-space>
          <a-button @click="closeDrawer">取消</a-button>
          <a-button type="primary" :loading="drawerLoading" @click="handleSubmit">
            {{ isEdit ? "更新" : "创建" }}
          </a-button>
        </a-space>
      </template>
    </a-drawer>

    <a-modal
      v-model:visible="jsonEditorVisible"
      title="JSON 编辑器"
      :width="600"
      :footer="true"
      @cancel="jsonEditorVisible = false"
    >
      <a-textarea
        v-model="jsonEditorValue"
        :auto-size="{ minRows: 10, maxRows: 20 }"
        placeholder="请输入 JSON 格式数据"
      />
      <template #footer>
        <a-space>
          <a-button @click="jsonEditorVisible = false">取消</a-button>
          <a-button type="primary" @click="saveJsonEditor">保存</a-button>
        </a-space>
      </template>
    </a-modal>
  </div>
</template>
