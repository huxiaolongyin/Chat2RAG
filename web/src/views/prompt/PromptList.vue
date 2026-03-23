<script setup lang="ts">
import { promptApi } from "@/api/prompt";
import type { Prompt, PromptDetailData, PromptVersionData } from "@/types/api";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { diffLines } from "diff";
import { computed, onMounted, reactive, ref } from "vue";

const loading = ref(false);
const prompts = ref<Prompt[]>([]);
const searchName = ref("");
const searchDesc = ref("");
const pagination = reactive({ current: 1, pageSize: 12, total: 0 });

const editModalVisible = ref(false);
const editLoading = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);
const form = reactive({
  promptName: "",
  promptDesc: "",
  promptText: "",
});

const versionModalVisible = ref(false);
const versionLoading = ref(false);
const promptDetail = ref<PromptDetailData | null>(null);
const selectedVersion = ref<number | null>(null);
const compareModalVisible = ref(false);
const compareLoading = ref(false);
const targetVersion = ref<number | null>(null);

const filteredPrompts = computed(() => {
  if (!searchName.value.trim() && !searchDesc.value.trim()) return prompts.value;
  const nameKeyword = searchName.value.toLowerCase();
  const descKeyword = searchDesc.value.toLowerCase();
  return prompts.value.filter((p) => {
    const nameMatch = !nameKeyword || p.promptName.toLowerCase().includes(nameKeyword);
    const descMatch = !descKeyword || p.promptDesc.toLowerCase().includes(descKeyword);
    return nameMatch && descMatch;
  });
});

async function loadPrompts() {
  loading.value = true;
  try {
    const res = await promptApi.getPrompts(
      pagination.current,
      pagination.pageSize,
      searchName.value || undefined,
      searchDesc.value || undefined
    );
    if (res.code === "0000" && res.data) {
      prompts.value = res.data.promptList || [];
      pagination.total = res.data.total || 0;
    }
  } catch (e) {
    console.error("Failed to load prompts:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadPrompts();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadPrompts();
}

function openCreateModal() {
  form.promptName = "";
  form.promptDesc = "";
  form.promptText = "";
  isEdit.value = false;
  editId.value = null;
  editModalVisible.value = true;
}

function openEditModal(prompt: Prompt) {
  isEdit.value = true;
  editId.value = prompt.id;
  form.promptName = prompt.promptName;
  form.promptDesc = prompt.promptDesc;
  form.promptText = prompt.promptText;
  editModalVisible.value = true;
}

function closeEditModal() {
  editModalVisible.value = false;
}

async function handleSubmit() {
  if (!form.promptName.trim()) {
    Message.warning("请输入提示词名称");
    return;
  }
  if (!form.promptDesc.trim()) {
    Message.warning("请输入提示词描述");
    return;
  }
  if (!form.promptText.trim()) {
    Message.warning("请输入提示词内容");
    return;
  }

  editLoading.value = true;
  try {
    if (isEdit.value && editId.value) {
      await promptApi.updatePrompt(editId.value, {
        promptName: form.promptName.trim(),
        promptDesc: form.promptDesc.trim(),
        promptText: form.promptText.trim(),
      });
      Message.success("更新成功，已创建新版本");
    } else {
      await promptApi.createPrompt({
        promptName: form.promptName.trim(),
        promptDesc: form.promptDesc.trim(),
        promptText: form.promptText.trim(),
      });
      Message.success("创建成功");
    }
    closeEditModal();
    loadPrompts();
  } catch (e) {
    console.error("Failed to save prompt:", e);
  } finally {
    editLoading.value = false;
  }
}

async function deletePrompt(id: number) {
  try {
    await promptApi.deletePrompt(id);
    Message.success("删除成功");
    loadPrompts();
  } catch (e) {
    console.error("Failed to delete prompt:", e);
    Message.error("删除失败");
  }
}

async function openVersionModal(prompt: Prompt) {
  versionLoading.value = true;
  versionModalVisible.value = true;
  selectedVersion.value = prompt.currentVersion;
  promptDetail.value = null;
  try {
    const res = await promptApi.getPrompt(prompt.id);
    if (res.code === "0000" && res.data) {
      promptDetail.value = {
        ...res.data,
        versions: res.data.versions || [],
      };
    }
  } catch (e) {
    console.error("Failed to load prompt detail:", e);
    Message.error("加载版本信息失败");
    versionModalVisible.value = false;
  } finally {
    versionLoading.value = false;
  }
}

function closeVersionModal() {
  versionModalVisible.value = false;
  promptDetail.value = null;
  selectedVersion.value = null;
}

function openCompareModal(version: number) {
  if (version === selectedVersion.value) {
    Message.info("已是当前版本");
    return;
  }
  targetVersion.value = version;
  compareModalVisible.value = true;
}

async function confirmVersionChange() {
  if (!promptDetail.value || targetVersion.value === null) return;

  compareLoading.value = true;
  try {
    await promptApi.setVersion(promptDetail.value.id, targetVersion.value);
    Message.success("版本切换成功");
    compareModalVisible.value = false;
    const currentId = promptDetail.value.id;
    const currentVersion = targetVersion.value;
    promptDetail.value = null;
    const res = await promptApi.getPrompt(currentId);
    if (res.code === "0000" && res.data) {
      promptDetail.value = {
        ...res.data,
        versions: res.data.versions || [],
      };
      selectedVersion.value = currentVersion;
    }
    loadPrompts();
  } catch (e) {
    console.error("Failed to set version:", e);
    Message.error("版本切换失败");
  } finally {
    compareLoading.value = false;
  }
}

function getCurrentVersionData(): PromptVersionData | undefined {
  if (!promptDetail.value?.versions) return undefined;
  return promptDetail.value.versions.find((v) => v.version === selectedVersion.value);
}

function getTargetVersionData(): PromptVersionData | undefined {
  if (!promptDetail.value?.versions || targetVersion.value === null) return undefined;
  return promptDetail.value.versions.find((v) => v.version === targetVersion.value);
}

interface DiffLine {
  value: string;
  added?: boolean;
  removed?: boolean;
}

function computeDiff(): DiffLine[] {
  const currentText = getCurrentVersionData()?.promptText || "";
  const targetText = getTargetVersionData()?.promptText || "";
  return diffLines(currentText, targetText);
}

const diffResult = computed(() => {
  if (!compareModalVisible.value) return [];
  return computeDiff();
});

function splitDiffForSideBySide() {
  const diff = diffResult.value;
  const leftLines: { text: string; type: "normal" | "removed" }[] = [];
  const rightLines: { text: string; type: "normal" | "added" }[] = [];

  diff.forEach((part) => {
    const lines = part.value.split("\n");
    if (part.added) {
      lines.forEach((line) => {
        rightLines.push({ text: line, type: "added" });
      });
    } else if (part.removed) {
      lines.forEach((line) => {
        leftLines.push({ text: line, type: "removed" });
      });
    } else {
      lines.forEach((line) => {
        leftLines.push({ text: line, type: "normal" });
        rightLines.push({ text: line, type: "normal" });
      });
    }
  });

  const maxLen = Math.max(leftLines.length, rightLines.length);
  while (leftLines.length < maxLen) {
    leftLines.push({ text: "", type: "normal" });
  }
  while (rightLines.length < maxLen) {
    rightLines.push({ text: "", type: "normal" });
  }

  return { leftLines, rightLines };
}

const sideBySideDiff = computed(() => splitDiffForSideBySide());

onMounted(() => {
  loadPrompts();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div
      class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
    >
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:text-box-outline" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">提示词管理</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-input-search
            v-model="searchName"
            placeholder="搜索名称..."
            style="width: 180px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-input-search
            v-model="searchDesc"
            placeholder="搜索描述..."
            style="width: 180px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-button type="primary" @click="openCreateModal">
            <template #icon><Icon icon="mdi:plus" /></template>
            创建提示词
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-spin :loading="loading" class="w-full">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <div
            v-for="prompt in filteredPrompts"
            :key="prompt.id"
            class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700 hover:shadow-lg hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group overflow-hidden"
            @click="openEditModal(prompt)"
          >
            <div class="p-5">
              <div class="flex items-start justify-between mb-4">
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center"
                  >
                    <Icon icon="mdi:text-box-outline" class="text-xl text-primary" />
                  </div>
                  <div>
                    <h3
                      class="text-base font-bold text-slate-900 dark:text-white truncate max-w-[160px]"
                    >
                      {{ prompt.promptName }}
                    </h3>
                    <div class="flex items-center gap-2 mt-1">
                      <span
                        class="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                      >
                        v{{ prompt.currentVersion }}
                      </span>
                    </div>
                  </div>
                </div>
                <a-dropdown trigger="click" @click.stop>
                  <a-button
                    type="text"
                    size="small"
                    class="opacity-0 group-hover:opacity-100 !text-slate-400 hover:!text-slate-600"
                  >
                    <template #icon><Icon icon="mdi:dots-vertical" /></template>
                  </a-button>
                  <template #content>
                    <a-doption @click.stop="openVersionModal(prompt)">
                      <template #icon><Icon icon="mdi:history" /></template>
                      版本管理
                    </a-doption>
                    <a-doption @click.stop="openEditModal(prompt)">
                      <template #icon><Icon icon="mdi:pencil" /></template>
                      编辑
                    </a-doption>
                    <a-doption class="text-red-500" @click.stop>
                      <a-popconfirm
                        content="确定删除此提示词吗？"
                        @ok="deletePrompt(prompt.id)"
                        @click.stop
                      >
                        <div class="flex items-center gap-2">
                          <Icon icon="mdi:delete" />
                          删除
                        </div>
                      </a-popconfirm>
                    </a-doption>
                  </template>
                </a-dropdown>
              </div>

              <p
                class="text-sm text-slate-500 dark:text-slate-400 line-clamp-2 mb-4 min-h-[40px]"
              >
                {{ prompt.promptDesc }}
              </p>

              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                <div class="flex items-center gap-2 mb-1">
                  <Icon icon="mdi:text" class="text-sm text-slate-400" />
                  <span class="text-xs text-slate-400">内容预览</span>
                </div>
                <p class="text-sm text-slate-600 dark:text-slate-300 line-clamp-2">
                  {{ prompt.promptText }}
                </p>
              </div>
            </div>

            <div
              class="px-5 py-3 bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-700/50 dark:to-slate-700/70 border-t border-slate-200/60 dark:border-slate-600 text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity"
              @click.stop="openVersionModal(prompt)"
            >
              <span>查看版本历史</span>
              <Icon icon="mdi:arrow-right" class="text-primary" />
            </div>
          </div>
        </div>

        <div
          v-if="filteredPrompts.length === 0 && !loading"
          class="text-center py-16"
        >
          <div
            class="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center"
          >
            <Icon
              icon="mdi:text-box-remove-outline"
              class="text-4xl text-slate-300 dark:text-slate-500"
            />
          </div>
          <p class="text-slate-400 dark:text-slate-500 text-lg">暂无提示词</p>
          <p class="text-slate-300 dark:text-slate-600 text-sm mt-1">
            点击上方按钮创建第一个提示词
          </p>
        </div>
      </a-spin>
    </div>

    <div
      v-if="pagination.total > pagination.pageSize"
      class="px-6 py-4 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700"
    >
      <a-pagination
        :current="pagination.current"
        :page-size="pagination.pageSize"
        :total="pagination.total"
        show-total
        @change="handlePageChange"
      />
    </div>

    <a-modal
      v-model:visible="editModalVisible"
      :title="isEdit ? '编辑提示词' : '创建提示词'"
      :width="600"
      :ok-loading="editLoading"
      @ok="handleSubmit"
      @cancel="closeEditModal"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="提示词名称" required>
          <a-input
            v-model="form.promptName"
            placeholder="请输入提示词名称"
            :max-length="50"
          />
        </a-form-item>
        <a-form-item label="提示词描述" required>
          <a-textarea
            v-model="form.promptDesc"
            placeholder="请输入提示词描述"
            :max-length="200"
            :auto-size="{ minRows: 2, maxRows: 4 }"
          />
        </a-form-item>
        <a-form-item label="提示词内容" required>
          <a-textarea
            v-model="form.promptText"
            placeholder="请输入提示词内容"
            :auto-size="{ minRows: 6, maxRows: 12 }"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:visible="versionModalVisible"
      title="版本管理"
      :width="600"
      :footer="false"
      @cancel="closeVersionModal"
    >
      <a-spin :loading="versionLoading" class="w-full">
        <div v-if="promptDetail" class="space-y-4">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-lg font-semibold text-slate-900 dark:text-white">
                {{ promptDetail.promptName }}
              </h3>
              <p class="text-sm text-slate-500">当前版本: v{{ promptDetail.currentVersion }}</p>
            </div>
          </div>

          <a-divider class="!my-2" />

          <div class="space-y-3 max-h-96 overflow-auto">
            <div
              v-for="v in promptDetail.versions || []"
              :key="v.version"
              class="p-4 rounded-lg border transition-all cursor-pointer"
              :class="[
                v.version === promptDetail.currentVersion
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-600 hover:border-primary/50',
              ]"
              @click="openCompareModal(v.version)"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span class="font-semibold text-slate-700 dark:text-slate-200">
                    v{{ v.version }}
                  </span>
                  <a-tag
                    v-if="v.version === promptDetail.currentVersion"
                    color="blue"
                    size="small"
                  >
                    当前
                  </a-tag>
                </div>
                <span class="text-xs text-slate-400">
                  {{ v.updateTime || v.createTime }}
                </span>
              </div>
              <p class="text-sm text-slate-500 dark:text-slate-400 mb-2">
                {{ v.promptDesc }}
              </p>
              <div class="bg-slate-50 dark:bg-slate-700/50 rounded p-2">
                <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                  {{ v.promptText }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </a-spin>
    </a-modal>

    <a-modal
      v-model:visible="compareModalVisible"
      title="版本对比"
      :width="800"
      :ok-loading="compareLoading"
      ok-text="确认切换"
      @ok="confirmVersionChange"
      @cancel="compareModalVisible = false"
    >
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="flex items-center gap-2 mb-2">
            <span class="font-semibold text-slate-700 dark:text-slate-200">
              当前版本 v{{ selectedVersion }}
            </span>
            <a-tag color="blue" size="small">当前</a-tag>
          </div>
          <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg h-72 overflow-auto border border-slate-200 dark:border-slate-600">
            <div
              v-for="(line, idx) in sideBySideDiff.leftLines"
              :key="idx"
              class="px-3 py-0.5 font-mono text-sm whitespace-pre-wrap"
              :class="[
                line.type === 'removed'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                  : 'text-slate-600 dark:text-slate-300'
              ]"
            >
              <span v-if="line.type === 'removed'" class="inline-block w-4 text-red-500">-</span>
              <span v-else class="inline-block w-4 text-slate-400">&nbsp;</span>
              <span>{{ line.text || '&nbsp;' }}</span>
            </div>
          </div>
        </div>
        <div>
          <div class="flex items-center gap-2 mb-2">
            <span class="font-semibold text-slate-700 dark:text-slate-200">
              目标版本 v{{ targetVersion }}
            </span>
            <a-tag color="green" size="small">切换</a-tag>
          </div>
          <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg h-72 overflow-auto border border-slate-200 dark:border-slate-600">
            <div
              v-for="(line, idx) in sideBySideDiff.rightLines"
              :key="idx"
              class="px-3 py-0.5 font-mono text-sm whitespace-pre-wrap"
              :class="[
                line.type === 'added'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                  : 'text-slate-600 dark:text-slate-300'
              ]"
            >
              <span v-if="line.type === 'added'" class="inline-block w-4 text-green-500">+</span>
              <span v-else class="inline-block w-4 text-slate-400">&nbsp;</span>
              <span>{{ line.text || '&nbsp;' }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="mt-3 flex items-center gap-4 text-xs text-slate-500">
        <div class="flex items-center gap-1">
          <span class="w-3 h-3 bg-red-100 dark:bg-red-900/40 rounded"></span>
          <span>删除的内容</span>
        </div>
        <div class="flex items-center gap-1">
          <span class="w-3 h-3 bg-green-100 dark:bg-green-900/40 rounded"></span>
          <span>新增的内容</span>
        </div>
      </div>
      <div class="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <div class="flex items-center gap-2">
          <Icon icon="mdi:alert-circle-outline" class="text-amber-500" />
          <span class="text-sm text-amber-700 dark:text-amber-400">
            确认后将切换到版本 v{{ targetVersion }}
          </span>
        </div>
      </div>
    </a-modal>
  </div>
</template>