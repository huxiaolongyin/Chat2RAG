<script setup lang="ts">
import { commandApi } from "@/api/command";
import type { Command, CommandCategory, CommandCreate, ParamType } from "@/types/api";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref, watch } from "vue";

const loading = ref(false);
const categories = ref<CommandCategory[]>([]);
const commands = ref<Command[]>([]);
const selectedCategoryId = ref<number | null>(null);
const searchKeyword = ref("");
const categorySearchKeyword = ref("");
const isActiveFilter = ref<boolean | "">("");
const pagination = reactive({ current: 1, pageSize: 10, total: 0 });
const selectedRowKeys = ref<number[]>([]);

const drawerVisible = ref(false);
const drawerLoading = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);

const categoryDrawerVisible = ref(false);
const categoryDrawerLoading = ref(false);
const isEditCategory = ref(false);
const editCategoryId = ref<number | null>(null);

const moveDrawerVisible = ref(false);
const moveDrawerLoading = ref(false);
const targetCategoryId = ref<number | null>(null);

const defaultForm = () => ({
  name: "",
  code: "",
  reply: "",
  categoryId: undefined as number | undefined,
  priority: 0,
  description: "",
  isActive: true,
  commands: "",
  commandList: [] as string[],
  paramType: "none" as ParamType,
  examples: [] as string[],
});

const form = reactive(defaultForm());

const categoryForm = reactive({
  name: "",
  description: "",
});

const paramTypeOptions = [
  { label: "无参数", value: "none" },
  { label: "数字", value: "number" },
  { label: "文本", value: "text" },
];

const isActiveOptions = [
  { label: "全部", value: "" },
  { label: "已启用", value: true },
  { label: "已禁用", value: false },
];

const filteredCategories = computed(() => {
  let result = [
    { id: 0, name: "全部分类" },
    ...categories.value,
    { id: -1, name: "未分类" },
  ];
  if (categorySearchKeyword.value.trim()) {
    const keyword = categorySearchKeyword.value.toLowerCase();
    result = result.filter(
      (c) =>
        c.name.toLowerCase().includes(keyword) ||
        (c.description && c.description.toLowerCase().includes(keyword))
    );
  }
  return result;
});

async function loadCategories() {
  try {
    const res = await commandApi.getCategories();
    if (res.code === "0000" && res.data) {
      categories.value = res.data.items;
    }
  } catch (e) {
    console.error("Failed to load categories:", e);
  }
}

async function loadCommands() {
  loading.value = true;
  try {
    const res = await commandApi.getCommands({
      current: pagination.current,
      size: pagination.pageSize,
      keyword: searchKeyword.value || undefined,
      categoryId: selectedCategoryId.value || undefined,
      isActive: isActiveFilter.value === "" ? undefined : isActiveFilter.value,
    });
    if (res.code === "0000" && res.data) {
      commands.value = res.data.items;
      pagination.total = res.data.total;
    }
  } catch (e) {
    console.error("Failed to load commands:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadCommands();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadCommands();
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size;
  pagination.current = 1;
  loadCommands();
}

function selectCategory(id: number | null) {
  selectedCategoryId.value = id === 0 ? null : id;
  pagination.current = 1;
  loadCommands();
}

function openCreateDrawer() {
  Object.assign(form, defaultForm());
  form.categoryId = selectedCategoryId.value || undefined;
  isEdit.value = false;
  editId.value = null;
  drawerVisible.value = true;
}

function openEditDrawer(command: Command) {
  isEdit.value = true;
  editId.value = command.id;
  form.name = command.name;
  form.code = command.code;
  form.reply = command.reply || "";
  form.categoryId = command.categoryId || undefined;
  form.priority = command.priority;
  form.description = command.description || "";
  form.isActive = command.isActive;
  form.commands = command.commands || "";
  form.commandList = command.commands
    ? command.commands.split("|").filter((c) => c.trim())
    : [];
  form.paramType = command.paramType;
  form.examples = command.examples || [];
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
  Object.assign(form, defaultForm());
}

async function handleSubmit() {
  if (!form.name.trim()) {
    Message.warning("请输入命令名称");
    return;
  }
  if (!form.code.trim()) {
    Message.warning("请输入命令代码");
    return;
  }

  drawerLoading.value = true;
  try {
    const payload: CommandCreate = {
      name: form.name.trim(),
      code: form.code.trim(),
      reply: form.reply || undefined,
      categoryId: form.categoryId,
      priority: form.priority,
      description: form.description || undefined,
      isActive: form.isActive,
      commands: form.commandList.filter((c) => c.trim()).join("|") || undefined,
      paramType: form.paramType,
      examples: form.examples.length > 0 ? form.examples : undefined,
    };

    if (isEdit.value && editId.value) {
      await commandApi.updateCommand(editId.value, payload);
      Message.success("更新成功");
    } else {
      await commandApi.createCommand(payload);
      Message.success("创建成功");
    }

    closeDrawer();
    loadCommands();
  } catch (e) {
    console.error("Failed to save command:", e);
  } finally {
    drawerLoading.value = false;
  }
}

async function deleteCommand(id: number) {
  try {
    await commandApi.deleteCommand(id);
    Message.success("删除成功");
    loadCommands();
  } catch (e) {
    console.error("Failed to delete command:", e);
    Message.error("删除失败");
  }
}

async function toggleCommandStatus(command: Command) {
  try {
    await commandApi.updateCommand(command.id, { isActive: !command.isActive });
    Message.success(command.isActive ? "已禁用" : "已启用");
    loadCommands();
  } catch (e) {
    console.error("Failed to toggle command status:", e);
  }
}

function addExample() {
  form.examples.push("");
}

function removeExample(index: number) {
  form.examples.splice(index, 1);
}

function addCommandWord() {
  form.commandList.push("");
}

function removeCommandWord(index: number) {
  form.commandList.splice(index, 1);
}

function openCreateCategoryDrawer() {
  categoryForm.name = "";
  categoryForm.description = "";
  isEditCategory.value = false;
  editCategoryId.value = null;
  categoryDrawerVisible.value = true;
}

function openEditCategoryDrawer(category: CommandCategory) {
  isEditCategory.value = true;
  editCategoryId.value = category.id;
  categoryForm.name = category.name;
  categoryForm.description = category.description || "";
  categoryDrawerVisible.value = true;
}

function closeCategoryDrawer() {
  categoryDrawerVisible.value = false;
}

async function handleCategorySubmit() {
  if (!categoryForm.name.trim()) {
    Message.warning("请输入分类名称");
    return;
  }

  categoryDrawerLoading.value = true;
  try {
    if (isEditCategory.value && editCategoryId.value) {
      await commandApi.updateCategory(editCategoryId.value, {
        name: categoryForm.name.trim(),
        description: categoryForm.description || undefined,
      });
      Message.success("更新成功");
    } else {
      await commandApi.createCategory({
        name: categoryForm.name.trim(),
        description: categoryForm.description || undefined,
      });
      Message.success("创建成功");
    }

    closeCategoryDrawer();
    loadCategories();
  } catch (e) {
    console.error("Failed to save category:", e);
  } finally {
    categoryDrawerLoading.value = false;
  }
}

async function deleteCategory(id: number) {
  try {
    await commandApi.deleteCategory(id);
    Message.success("删除成功");
    if (selectedCategoryId.value === id) {
      selectedCategoryId.value = null;
    }
    loadCategories();
    loadCommands();
  } catch (e) {
    console.error("Failed to delete category:", e);
    Message.error("删除失败");
  }
}

function handleSelectionChange(keys: (string | number)[]) {
  selectedRowKeys.value = keys as number[];
}

function openMoveDrawer() {
  if (selectedRowKeys.value.length === 0) {
    Message.warning("请先选择要移动的命令");
    return;
  }
  targetCategoryId.value = null;
  moveDrawerVisible.value = true;
}

function closeMoveDrawer() {
  moveDrawerVisible.value = false;
  targetCategoryId.value = null;
}

async function handleMove() {
  if (selectedRowKeys.value.length === 0) {
    Message.warning("请选择要移动的命令");
    return;
  }

  moveDrawerLoading.value = true;
  try {
    await commandApi.batchMoveCommands(selectedRowKeys.value, targetCategoryId.value);
    Message.success(`成功移动 ${selectedRowKeys.value.length} 个命令`);
    closeMoveDrawer();
    selectedRowKeys.value = [];
    loadCommands();
  } catch (e) {
    console.error("Failed to move commands:", e);
    Message.error("移动失败");
  } finally {
    moveDrawerLoading.value = false;
  }
}

watch(isActiveFilter, () => {
  pagination.current = 1;
  loadCommands();
});

onMounted(() => {
  loadCategories();
  loadCommands();
});
</script>

<template>
  <div class="flex h-full">
    <aside
      class="w-64 flex-shrink-0 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col"
    >
      <div class="p-4 border-b border-slate-200 dark:border-slate-700">
        <div class="flex items-center justify-between mb-2">
          <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-200">
            命令分类
          </h2>
          <a-button size="small" type="text" @click="openCreateCategoryDrawer">
            <template #icon><Icon icon="mdi:plus" /></template>
          </a-button>
        </div>
        <a-input
          v-model="categorySearchKeyword"
          placeholder="搜索分类..."
          size="small"
          allow-clear
        >
          <template #prefix><Icon icon="mdi:magnify" /></template>
        </a-input>
      </div>
      <div class="flex-1 overflow-y-auto">
        <div
          v-for="category in filteredCategories"
          :key="category.id"
          class="group px-4 py-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
          :class="{
            'bg-primary/5 border-r-2 border-primary':
              (selectedCategoryId === null && category.id === 0) ||
              selectedCategoryId === category.id,
          }"
          @click="selectCategory(category.id)"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-700 dark:text-slate-200">{{
              category.name
            }}</span>
            <div
              v-if="category.id !== 0"
              class="hidden group-hover:flex items-center gap-1"
            >
              <a-button
                type="text"
                size="mini"
                @click.stop="openEditCategoryDrawer(category)"
              >
                <template #icon><Icon icon="mdi:pencil" class="text-sm" /></template>
              </a-button>
              <a-popconfirm
                content="确定删除此分类吗？"
                @ok="deleteCategory(category.id)"
              >
                <a-button type="text" size="mini" status="danger" @click.stop>
                  <template #icon><Icon icon="mdi:delete" class="text-sm" /></template>
                </a-button>
              </a-popconfirm>
            </div>
          </div>
          <p v-if="category.description" class="text-xs text-slate-400 mt-1 truncate">
            {{ category.description }}
          </p>
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
              placeholder="搜索命令名称或代码..."
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
            <a-button
              v-if="selectedRowKeys.length > 0"
              type="outline"
              @click="openMoveDrawer"
            >
              <template #icon><Icon icon="mdi:folder-move" /></template>
              移动 ({{ selectedRowKeys.length }})
            </a-button>
          </div>
          <a-button type="primary" @click="openCreateDrawer">
            <template #icon><Icon icon="mdi:plus" /></template>
            新增命令
          </a-button>
        </div>
      </div>

      <div class="flex-1 overflow-auto p-4">
        <a-table
          :data="commands"
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
            <a-table-column title="名称" data-index="name" :width="120">
              <template #cell="{ record }">
                <span class="font-medium text-slate-700 dark:text-slate-200">{{
                  record.name
                }}</span>
              </template>
            </a-table-column>
            <a-table-column title="代码" data-index="code" :width="120">
              <template #cell="{ record }">
                <a-tag size="small" color="arcoblue">{{ record.code }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="回复内容" data-index="reply" :width="180">
              <template #cell="{ record }">
                <span
                  v-if="record.reply"
                  class="text-sm text-slate-600 dark:text-slate-300"
                >
                  {{
                    record.reply.length > 18
                      ? record.reply.slice(0, 18) + "..."
                      : record.reply
                  }}
                </span>
                <span v-else class="text-slate-300">-</span>
              </template>
            </a-table-column>
            <a-table-column title="命令词" data-index="commands" :width="240">
              <template #cell="{ record }">
                <span
                  v-if="record.commands"
                  class="text-xs text-slate-500 dark:text-slate-400"
                >
                  {{
                    record.commands.length > 18
                      ? record.commands.slice(0, 18) + "..."
                      : record.commands
                  }}
                </span>
                <span v-else class="text-slate-300">-</span>
              </template>
            </a-table-column>
            <a-table-column
              title="参数类型"
              data-index="paramType"
              :width="90"
              align="center"
            >
              <template #cell="{ record }">
                <a-tag v-if="record.paramType === 'none'" color="gray" size="small"
                  >无</a-tag
                >
                <a-tag
                  v-else-if="record.paramType === 'number'"
                  color="green"
                  size="small"
                  >数字</a-tag
                >
                <a-tag v-else-if="record.paramType === 'text'" color="purple" size="small"
                  >文本</a-tag
                >
              </template>
            </a-table-column>
            <a-table-column
              title="优先级"
              data-index="priority"
              :width="80"
              align="center"
            >
              <template #cell="{ record }">
                <span class="text-sm font-mono">{{ record.priority }}</span>
              </template>
            </a-table-column>
            <a-table-column title="状态" data-index="isActive" :width="80" align="center">
              <template #cell="{ record }">
                <a-tag v-if="record.isActive" color="green" size="small">启用</a-tag>
                <a-tag v-else color="red" size="small">禁用</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" :width="160" align="center">
              <template #cell="{ record }">
                <a-space>
                  <a-button type="text" size="small" @click="toggleCommandStatus(record)">
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
                    content="确定删除此命令吗？"
                    @ok="deleteCommand(record.id)"
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
      :title="isEdit ? '编辑命令' : '新增命令'"
      :width="480"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="命令名称" required>
          <a-input v-model="form.name" placeholder="请输入命令名称" />
        </a-form-item>
        <a-form-item label="命令代码" required>
          <a-input v-model="form.code" placeholder="请输入命令代码，如 TurnLeft" />
        </a-form-item>
        <a-form-item label="所属分类">
          <a-select v-model="form.categoryId" placeholder="请选择分类" allow-clear>
            <a-option v-for="cat in categories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="命令词">
          <div class="space-y-2">
            <div v-for="(_, index) in form.commandList" :key="index" class="flex gap-2">
              <a-input
                v-model="form.commandList[index]"
                placeholder="输入命令词"
                class="flex-1"
              />
              <a-button type="text" status="danger" @click="removeCommandWord(index)">
                <template #icon><Icon icon="mdi:close" /></template>
              </a-button>
            </div>
            <a-button type="dashed" long @click="addCommandWord">
              <template #icon><Icon icon="mdi:plus" /></template>
              添加命令词
            </a-button>
          </div>
        </a-form-item>
        <a-form-item label="参数类型">
          <a-select v-model="form.paramType">
            <a-option v-for="opt in paramTypeOptions" :key="opt.value" :value="opt.value">
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
        </a-form-item>
        <a-form-item label="回复内容">
          <a-textarea
            v-model="form.reply"
            placeholder="命令触发后的回复内容"
            :auto-size="{ minRows: 2, maxRows: 4 }"
          />
        </a-form-item>
        <a-form-item label="示例说法">
          <div class="space-y-2">
            <div v-for="(_, index) in form.examples" :key="index" class="flex gap-2">
              <a-input
                v-model="form.examples[index]"
                placeholder="输入示例说法"
                class="flex-1"
              />
              <a-button type="text" status="danger" @click="removeExample(index)">
                <template #icon><Icon icon="mdi:close" /></template>
              </a-button>
            </div>
            <a-button type="dashed" long @click="addExample">
              <template #icon><Icon icon="mdi:plus" /></template>
              添加示例
            </a-button>
          </div>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea
            v-model="form.description"
            placeholder="命令描述信息"
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
      v-model:visible="categoryDrawerVisible"
      :title="isEditCategory ? '编辑分类' : '新增分类'"
      :width="360"
      :footer="true"
      @cancel="closeCategoryDrawer"
    >
      <a-form :model="categoryForm" layout="vertical">
        <a-form-item label="分类名称" required>
          <a-input v-model="categoryForm.name" placeholder="请输入分类名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea
            v-model="categoryForm.description"
            placeholder="请输入分类描述"
            :auto-size="{ minRows: 2, maxRows: 4 }"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="closeCategoryDrawer">取消</a-button>
          <a-button
            type="primary"
            :loading="categoryDrawerLoading"
            @click="handleCategorySubmit"
          >
            {{ isEditCategory ? "更新" : "创建" }}
          </a-button>
        </a-space>
      </template>
    </a-drawer>

    <a-drawer
      v-model:visible="moveDrawerVisible"
      title="批量移动命令"
      :width="400"
      :footer="true"
      @cancel="closeMoveDrawer"
    >
      <div class="mb-4">
        <p class="text-sm text-slate-500">
          已选择
          <span class="font-semibold text-primary">{{ selectedRowKeys.length }}</span>
          个命令
        </p>
      </div>
      <a-form :model="{ targetCategoryId }" layout="vertical">
        <a-form-item label="目标分类">
          <a-select v-model="targetCategoryId" placeholder="请选择目标分类" allow-clear>
            <a-option :value="null">未分类</a-option>
            <a-option v-for="cat in categories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </a-option>
          </a-select>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="closeMoveDrawer">取消</a-button>
          <a-button type="primary" :loading="moveDrawerLoading" @click="handleMove">
            确认移动
          </a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>
