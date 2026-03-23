<script setup lang="ts">
import { sensitiveApi } from "@/api/sensitive";
import type {
  SensitiveWord,
  SensitiveWordCategory,
  SensitiveWordCreate,
} from "@/types/api";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref, watch } from "vue";

const loading = ref(false);
const categories = ref<SensitiveWordCategory[]>([]);
const words = ref<SensitiveWord[]>([]);
const selectedCategoryId = ref<number | null>(null);
const searchKeyword = ref("");
const categorySearchKeyword = ref("");
const levelFilter = ref<number | undefined>(undefined);
const isActiveFilter = ref<boolean | "">("");
const pagination = reactive({ current: 1, pageSize: 10, total: 0 });

const drawerVisible = ref(false);
const drawerLoading = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);

const categoryDrawerVisible = ref(false);
const categoryDrawerLoading = ref(false);
const isEditCategory = ref(false);
const editCategoryId = ref<number | null>(null);

const defaultForm = () => ({
  word: "",
  categoryId: undefined as number | undefined,
  level: 1 as number,
  description: "",
  isActive: true,
});

const form = reactive(defaultForm());

const categoryForm = reactive({
  name: "",
  description: "",
});

const levelOptions = [
  { label: "全部", value: undefined },
  { label: "低", value: 1 },
  { label: "中", value: 2 },
  { label: "高", value: 3 },
];

const isActiveOptions = [
  { label: "全部", value: "" },
  { label: "已启用", value: true },
  { label: "已禁用", value: false },
];

const filteredCategories = computed(() => {
  let result = [
    { id: 0, name: "全部分类" },
    { id: -1, name: "未分类" },
    ...categories.value,
  ];
  if (categorySearchKeyword.value.trim()) {
    const keyword = categorySearchKeyword.value.toLowerCase();
    result = result.filter(
      (c) =>
        c.name.toLowerCase().includes(keyword) ||
        ((c as SensitiveWordCategory).description &&
          (c as SensitiveWordCategory).description!.toLowerCase().includes(keyword))
    );
  }
  return result;
});

async function loadCategories() {
  try {
    const res = await sensitiveApi.getCategories();
    if (res.code === "0000" && res.data) {
      categories.value = res.data.items;
    }
  } catch (e) {
    console.error("Failed to load categories:", e);
  }
}

async function loadWords() {
  loading.value = true;
  try {
    const res = await sensitiveApi.getWords({
      current: pagination.current,
      size: pagination.pageSize,
      word: searchKeyword.value || undefined,
      categoryId: selectedCategoryId.value || undefined,
      level: levelFilter.value,
    });
    if (res.code === "0000" && res.data) {
      words.value = res.data.items;
      pagination.total = res.data.total;
    }
  } catch (e) {
    console.error("Failed to load words:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadWords();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadWords();
}

function handlePageSizeChange(size: number) {
  pagination.pageSize = size;
  pagination.current = 1;
  loadWords();
}

function selectCategory(id: number | null) {
  selectedCategoryId.value = id === 0 ? null : id;
  pagination.current = 1;
  loadWords();
}

function openCreateDrawer() {
  Object.assign(form, defaultForm());
  form.categoryId = selectedCategoryId.value || undefined;
  isEdit.value = false;
  editId.value = null;
  drawerVisible.value = true;
}

function openEditDrawer(word: SensitiveWord) {
  isEdit.value = true;
  editId.value = word.id;
  form.word = word.word;
  form.categoryId = word.categoryId || undefined;
  form.level = word.level || 1;
  form.description = word.description || "";
  form.isActive = word.isActive;
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
  Object.assign(form, defaultForm());
}

async function handleSubmit() {
  if (!form.word.trim()) {
    Message.warning("请输入敏感词");
    return;
  }

  drawerLoading.value = true;
  try {
    const payload: SensitiveWordCreate = {
      word: form.word.trim(),
      categoryId: form.categoryId,
      level: form.level,
      description: form.description || undefined,
      isActive: form.isActive,
    };

    if (isEdit.value && editId.value) {
      await sensitiveApi.updateWord(editId.value, payload);
      Message.success("更新成功");
    } else {
      await sensitiveApi.createWord(payload);
      Message.success("创建成功");
    }

    closeDrawer();
    loadWords();
  } catch (e) {
    console.error("Failed to save word:", e);
  } finally {
    drawerLoading.value = false;
  }
}

async function deleteWord(id: number) {
  try {
    await sensitiveApi.deleteWord(id);
    Message.success("删除成功");
    loadWords();
  } catch (e) {
    console.error("Failed to delete word:", e);
    Message.error("删除失败");
  }
}

async function toggleWordStatus(word: SensitiveWord) {
  try {
    await sensitiveApi.updateWord(word.id, { isActive: !word.isActive });
    Message.success(word.isActive ? "已禁用" : "已启用");
    loadWords();
  } catch (e) {
    console.error("Failed to toggle word status:", e);
  }
}

function openCreateCategoryDrawer() {
  categoryForm.name = "";
  categoryForm.description = "";
  isEditCategory.value = false;
  editCategoryId.value = null;
  categoryDrawerVisible.value = true;
}

function openEditCategoryDrawer(category: SensitiveWordCategory) {
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
      await sensitiveApi.updateCategory(editCategoryId.value, {
        name: categoryForm.name.trim(),
        description: categoryForm.description || undefined,
      });
      Message.success("更新成功");
    } else {
      await sensitiveApi.createCategory({
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
    await sensitiveApi.deleteCategory(id);
    Message.success("删除成功");
    if (selectedCategoryId.value === id) {
      selectedCategoryId.value = null;
    }
    loadCategories();
    loadWords();
  } catch (e) {
    console.error("Failed to delete category:", e);
    Message.error("删除失败");
  }
}

watch([levelFilter, isActiveFilter], () => {
  pagination.current = 1;
  loadWords();
});

onMounted(() => {
  loadCategories();
  loadWords();
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
            敏感词分类
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
            <div class="flex items-center gap-1">
              <a-button
                v-if="category.id !== 0 && category.id !== -1"
                type="text"
                size="mini"
                class="opacity-0 group-hover:opacity-100"
                @click.stop="openEditCategoryDrawer(category as SensitiveWordCategory)"
              >
                <template #icon><Icon icon="mdi:pencil" class="text-sm" /></template>
              </a-button>
              <a-popconfirm
                v-if="category.id !== 0 && category.id !== -1"
                content="确定删除此分类吗？"
                @ok="deleteCategory(category.id)"
              >
                <a-button
                  type="text"
                  size="mini"
                  status="danger"
                  class="opacity-0 group-hover:opacity-100"
                  @click.stop
                >
                  <template #icon><Icon icon="mdi:delete" class="text-sm" /></template>
                </a-button>
              </a-popconfirm>
            </div>
          </div>
          <p
            v-if="(category as SensitiveWordCategory).description"
            class="text-xs text-slate-400 mt-1 truncate"
          >
            {{ (category as SensitiveWordCategory).description }}
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
              placeholder="搜索敏感词..."
              style="width: 240px"
              @search="handleSearch"
              @press-enter="handleSearch"
            />
            <a-select
              v-model="levelFilter"
              placeholder="级别"
              style="width: 100px"
              allow-clear
            >
              <a-option
                v-for="opt in levelOptions"
                :key="opt.value ?? 'all'"
                :value="opt.value"
              >
                {{ opt.label }}
              </a-option>
            </a-select>
            <a-select
              v-model="isActiveFilter"
              placeholder="状态"
              style="width: 100px"
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
            新增敏感词
          </a-button>
        </div>
      </div>

      <div class="flex-1 overflow-auto p-4">
        <a-table
          :data="words"
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
            <a-table-column title="敏感词" data-index="word" :width="180">
              <template #cell="{ record }">
                <span class="font-medium text-slate-700 dark:text-slate-200">{{
                  record.word
                }}</span>
              </template>
            </a-table-column>
            <a-table-column title="分类" data-index="categoryId" :width="140">
              <template #cell="{ record }">
                <span v-if="record.category" class="text-sm text-slate-600 dark:text-slate-300">
                  {{ record.category.name }}
                </span>
                <span v-else class="text-slate-300">未分类</span>
              </template>
            </a-table-column>
            <a-table-column title="级别" data-index="level" :width="100" align="center">
              <template #cell="{ record }">
                <a-tag v-if="record.level === 1" color="green" size="small">低</a-tag>
                <a-tag v-else-if="record.level === 2" color="orange" size="small">中</a-tag>
                <a-tag v-else-if="record.level === 3" color="red" size="small">高</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="描述" data-index="description" :width="200">
              <template #cell="{ record }">
                <span
                  v-if="record.description"
                  class="text-sm text-slate-500 dark:text-slate-400"
                >
                  {{
                    record.description.length > 20
                      ? record.description.slice(0, 20) + "..."
                      : record.description
                  }}
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
            <a-table-column title="操作" :width="140" align="center">
              <template #cell="{ record }">
                <a-space>
                  <a-button type="text" size="small" @click="toggleWordStatus(record)">
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
                    content="确定删除此敏感词吗？"
                    popup-container="body"
                    @ok="deleteWord(record.id)"
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
      :title="isEdit ? '编辑敏感词' : '新增敏感词'"
      :width="420"
      :footer="true"
      @cancel="closeDrawer"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="敏感词" required>
          <a-input v-model="form.word" placeholder="请输入敏感词" />
        </a-form-item>
        <a-form-item label="所属分类">
          <a-select v-model="form.categoryId" placeholder="请选择分类" allow-clear>
            <a-option v-for="cat in categories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="级别">
          <a-radio-group v-model="form.level">
            <a-radio :value="1">低</a-radio>
            <a-radio :value="2">中</a-radio>
            <a-radio :value="3">高</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea
            v-model="form.description"
            placeholder="请输入描述信息"
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
  </div>
</template>