<script setup lang="ts">
import { flowApi } from "@/api/flow";
import type { Flow } from "@/types/api";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const loading = ref(false);
const flows = ref<Flow[]>([]);
const searchName = ref("");
const pagination = reactive({ current: 1, pageSize: 12, total: 0 });

const editModalVisible = ref(false);
const editLoading = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);
const form = reactive({
  name: "",
  desc: "",
});

async function loadFlows() {
  loading.value = true;
  try {
    const res = await flowApi.getFlows(
      pagination.current,
      pagination.pageSize,
      searchName.value || undefined
    );
    if (res.code === "0000" && res.data) {
      flows.value = res.data.items || [];
      pagination.total = res.data.total || 0;
    }
  } catch (e) {
    console.error("Failed to load flows:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadFlows();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadFlows();
}

function openCreateModal() {
  form.name = "";
  form.desc = "";
  isEdit.value = false;
  editId.value = null;
  editModalVisible.value = true;
}

function openEditModal(flow: Flow) {
  isEdit.value = true;
  editId.value = flow.id;
  form.name = flow.name;
  form.desc = flow.desc || "";
  editModalVisible.value = true;
}

function closeEditModal() {
  editModalVisible.value = false;
}

async function handleSubmit() {
  if (!form.name.trim()) {
    Message.warning("请输入流程名称");
    return;
  }

  editLoading.value = true;
  try {
    if (isEdit.value && editId.value) {
      await flowApi.updateFlow(editId.value, {
        name: form.name.trim(),
        desc: form.desc.trim() || undefined,
      });
      Message.success("更新成功");
    } else {
      await flowApi.createFlow({
        name: form.name.trim(),
        desc: form.desc.trim() || undefined,
      });
      Message.success("创建成功");
    }
    closeEditModal();
    loadFlows();
  } catch (e) {
    console.error("Failed to save flow:", e);
  } finally {
    editLoading.value = false;
  }
}

async function deleteFlow(id: number) {
  try {
    await flowApi.deleteFlow(id);
    Message.success("删除成功");
    loadFlows();
  } catch (e) {
    console.error("Failed to delete flow:", e);
    Message.error("删除失败");
  }
}

function goToEditor(flow: Flow) {
  router.push(`/rules/flows/editor/${flow.id}`);
}

onMounted(() => {
  loadFlows();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div
      class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
    >
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:source-branch" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">流程管理</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-input-search
            v-model="searchName"
            placeholder="搜索流程名称..."
            style="width: 220px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-button type="primary" @click="openCreateModal">
            <template #icon><Icon icon="mdi:plus" /></template>
            创建流程
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-spin :loading="loading" class="w-full">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <div
            v-for="flow in flows"
            :key="flow.id"
            class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700 hover:shadow-lg hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group overflow-hidden"
            @click="goToEditor(flow)"
          >
            <div class="p-5">
              <div class="flex items-start justify-between mb-4">
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center"
                  >
                    <Icon icon="mdi:account-tree" class="text-xl text-primary" />
                  </div>
                  <div>
                    <h3
                      class="text-base font-bold text-slate-900 dark:text-white truncate max-w-[160px]"
                    >
                      {{ flow.name }}
                    </h3>
                    <div class="flex items-center gap-2 mt-1">
                      <span
                        v-if="flow.currentVersion"
                        class="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                      >
                        v{{ flow.currentVersion }}
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
                    <a-doption @click.stop="goToEditor(flow)">
                      <template #icon><Icon icon="mdi:pencil-ruler" /></template>
                      编辑器
                    </a-doption>
                    <a-doption @click.stop="openEditModal(flow)">
                      <template #icon><Icon icon="mdi:pencil" /></template>
                      编辑信息
                    </a-doption>
                    <a-doption class="text-red-500" @click.stop>
                      <a-popconfirm
                        content="确定删除此流程吗？"
                        @ok="deleteFlow(flow.id)"
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
                {{ flow.desc || "暂无描述" }}
              </p>

              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                <div class="flex items-center gap-2 mb-1">
                  <Icon icon="mdi:clock-outline" class="text-sm text-slate-400" />
                  <span class="text-xs text-slate-400">创建时间</span>
                </div>
                <p class="text-sm text-slate-600 dark:text-slate-300">
                  {{ flow.createTime || "-" }}
                </p>
              </div>
            </div>

            <div
              class="px-5 py-3 bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-700/50 dark:to-slate-700/70 border-t border-slate-200/60 dark:border-slate-600 text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity"
              @click.stop="goToEditor(flow)"
            >
              <span>打开编辑器</span>
              <Icon icon="mdi:arrow-right" class="text-primary" />
            </div>
          </div>
        </div>

        <div v-if="flows.length === 0 && !loading" class="text-center py-16">
          <div
            class="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center"
          >
            <Icon
              icon="mdi:account-tree-outline"
              class="text-4xl text-slate-300 dark:text-slate-500"
            />
          </div>
          <p class="text-slate-400 dark:text-slate-500 text-lg">暂无流程</p>
          <p class="text-slate-300 dark:text-slate-600 text-sm mt-1">
            点击上方按钮创建第一个流程
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
      :title="isEdit ? '编辑流程' : '创建流程'"
      :width="500"
      :ok-loading="editLoading"
      @ok="handleSubmit"
      @cancel="closeEditModal"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="流程名称" required>
          <a-input v-model="form.name" placeholder="请输入流程名称" :max-length="50" />
        </a-form-item>
        <a-form-item label="流程描述">
          <a-textarea
            v-model="form.desc"
            placeholder="请输入流程描述"
            :max-length="200"
            :auto-size="{ minRows: 2, maxRows: 4 }"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>
