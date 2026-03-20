<script setup lang="ts">
import { knowledgeApi } from "@/api/knowledge";
import type { KnowledgeCollection } from "@/types/api";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const loading = ref(false);
const collections = ref<KnowledgeCollection[]>([]);
const searchKeyword = ref("");
const pagination = reactive({ current: 1, pageSize: 12, total: 0 });

const createDrawerVisible = ref(false);
const createLoading = ref(false);
const createForm = reactive({ name: "" });

const reindexLoading = ref<string | null>(null);
const reindexModalVisible = ref(false);

const filteredCollections = computed(() => {
  if (!searchKeyword.value.trim()) return collections.value;
  const keyword = searchKeyword.value.toLowerCase();
  return collections.value.filter((c) =>
    c.collectionName.toLowerCase().includes(keyword)
  );
});

async function loadCollections() {
  loading.value = true;
  try {
    const res = await knowledgeApi.getCollections(
      pagination.current,
      pagination.pageSize,
      searchKeyword.value || undefined
    );
    if (res.data.code === "0000" && res.data.data) {
      const data = res.data.data as {
        items: KnowledgeCollection[];
        total: number;
      };
      collections.value = data.items || [];
      pagination.total = data.total || 0;
    }
  } catch (e) {
    console.error("Failed to load collections:", e);
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.current = 1;
  loadCollections();
}

function handlePageChange(page: number) {
  pagination.current = page;
  loadCollections();
}

function openCreateDrawer() {
  createForm.name = "";
  createDrawerVisible.value = true;
}

function closeCreateDrawer() {
  createDrawerVisible.value = false;
}

async function handleCreate() {
  if (!createForm.name.trim()) {
    Message.warning("请输入知识库名称");
    return;
  }

  createLoading.value = true;
  try {
    const res = await knowledgeApi.createCollection(createForm.name.trim());
    if (res.data.code === "0000") {
      Message.success("创建成功");
      closeCreateDrawer();
      loadCollections();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to create collection:", e);
  } finally {
    createLoading.value = false;
  }
}

async function deleteCollection(name: string) {
  try {
    const res = await knowledgeApi.deleteCollection(name);
    if (res.data.code === "0000") {
      Message.success("删除成功");
      loadCollections();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to delete collection:", e);
  }
}

async function reindexCollection(name: string) {
  reindexLoading.value = name;
  reindexModalVisible.value = true;
  try {
    const res = await knowledgeApi.reindexCollection(name);
    if (res.data.code === "0000") {
      Message.success("重新索引成功");
      loadCollections();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to reindex collection:", e);
  } finally {
    reindexLoading.value = null;
    reindexModalVisible.value = false;
  }
}

function enterCollection(name: string) {
  router.push(`/knowledge/${encodeURIComponent(name)}`);
}

onMounted(() => {
  loadCollections();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div
      class="px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
    >
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <Icon icon="mdi:database" class="text-2xl text-primary" />
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">知识库管理</h1>
        </div>
        <div class="flex items-center gap-3">
          <a-input-search
            v-model="searchKeyword"
            placeholder="搜索知识库..."
            style="width: 280px"
            @search="handleSearch"
            @press-enter="handleSearch"
          />
          <a-button type="primary" @click="openCreateDrawer">
            <template #icon><Icon icon="mdi:plus" /></template>
            创建知识库
          </a-button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <a-spin :loading="loading" class="w-full">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <div
            v-for="collection in filteredCollections"
            :key="collection.collectionName"
            class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200/60 dark:border-slate-700 hover:shadow-lg hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group overflow-hidden"
            @click="enterCollection(collection.collectionName)"
          >
            <div class="p-5">
              <div class="flex items-start justify-between mb-4">
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center"
                  >
                    <Icon icon="mdi:database" class="text-xl text-primary" />
                  </div>
                  <div>
                    <h3
                      class="text-base font-bold text-slate-900 dark:text-white truncate max-w-[160px]"
                    >
                      {{ collection.collectionName }}
                    </h3>
                    <div class="flex items-center gap-2 mt-1">
                      <span
                        v-if="collection.vectorMode"
                        :class="[
                          'text-xs px-1.5 py-0.5 rounded',
                          collection.vectorMode === 'legacy'
                            ? 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400'
                            : collection.vectorMode === 'hybrid'
                            ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
                        ]"
                      >
                        {{
                          collection.vectorMode === "legacy"
                            ? "旧版"
                            : collection.vectorMode === "hybrid"
                            ? "混合"
                            : "密集"
                        }}
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
                    <a-doption @click.stop="reindexCollection(collection.collectionName)">
                      <template #icon><Icon icon="mdi:refresh" /></template>
                      重建索引
                    </a-doption>
                    <a-doption class="text-red-500" @click.stop>
                      <a-popconfirm
                        content="确定删除此知识库吗？所有数据将被删除！"
                        @ok="deleteCollection(collection.collectionName)"
                        @click.stop
                      >
                        <div class="flex items-center gap-2">
                          <Icon icon="mdi:delete" />
                          删除知识库
                        </div>
                      </a-popconfirm>
                    </a-doption>
                  </template>
                </a-dropdown>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                  <div class="flex items-center gap-2 mb-1">
                    <Icon
                      icon="mdi:file-document-outline"
                      class="text-sm text-slate-400"
                    />
                    <span class="text-xs text-slate-400">知识点</span>
                  </div>
                  <p class="text-lg font-bold text-slate-700 dark:text-slate-200">
                    {{ collection.documentsCount ?? 0 }}
                  </p>
                </div>
                <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                  <div class="flex items-center gap-2 mb-1">
                    <Icon icon="mdi:file-outline" class="text-sm text-slate-400" />
                    <span class="text-xs text-slate-400">文件数</span>
                  </div>
                  <p class="text-lg font-bold text-slate-700 dark:text-slate-200">
                    {{ collection.filesCount ?? 0 }}
                  </p>
                </div>
              </div>
            </div>

            <div
              class="px-5 py-3 bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-700/50 dark:to-slate-700/70 border-t border-slate-200/60 dark:border-slate-600 text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <span>点击进入管理</span>
              <Icon icon="mdi:arrow-right" class="text-primary" />
            </div>
          </div>
        </div>

        <div
          v-if="filteredCollections.length === 0 && !loading"
          class="text-center py-16"
        >
          <div
            class="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center"
          >
            <Icon
              icon="mdi:database-off-outline"
              class="text-4xl text-slate-300 dark:text-slate-500"
            />
          </div>
          <p class="text-slate-400 dark:text-slate-500 text-lg">暂无知识库</p>
          <p class="text-slate-300 dark:text-slate-600 text-sm mt-1">
            点击上方按钮创建第一个知识库
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

    <a-drawer
      v-model:visible="createDrawerVisible"
      title="创建知识库"
      :width="400"
      :footer="true"
      @cancel="closeCreateDrawer"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="知识库名称" required>
          <a-input
            v-model="createForm.name"
            placeholder="请输入知识库名称"
            :max-length="100"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="closeCreateDrawer">取消</a-button>
          <a-button type="primary" :loading="createLoading" @click="handleCreate">
            创建
          </a-button>
        </a-space>
      </template>
    </a-drawer>

    <a-modal
      v-model:visible="reindexModalVisible"
      :closable="false"
      :mask-closable="false"
      :footer="false"
      simple
    >
      <div class="text-center py-4">
        <a-spin :size="32" />
        <p class="mt-4 text-slate-600">正在重建索引，请稍候...</p>
      </div>
    </a-modal>
  </div>
</template>
