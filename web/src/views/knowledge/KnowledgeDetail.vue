<script setup lang="ts">
import { knowledgeApi } from "@/api/knowledge";
import type {
  ChunkPreview,
  FileData,
  FileVersionData,
  KnowledgeDocument,
  QueryResult,
} from "@/types/api";
import type { FileItem } from "@arco-design/web-vue";
import { Message } from "@arco-design/web-vue";
import { Icon } from "@iconify/vue";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const collectionName = computed(() => decodeURIComponent(route.params.name as string));

const loading = ref(false);

const files = ref<FileData[]>([]);
const filePagination = reactive({ current: 1, pageSize: 10, total: 0 });

const documents = ref<KnowledgeDocument[]>([]);
const docPagination = reactive({ current: 1, pageSize: 20, total: 0 });
const docSearchKeyword = ref("");

const queryText = ref("");
const topK = ref(5);
const scoreThreshold = ref(0.6);
const searchResults = ref<QueryResult[]>([]);
const searchLoading = ref(false);

const uploadDrawerVisible = ref(false);
const uploadLoading = ref(false);
const uploadForm = reactive({ maxChars: 600, overlap: 100 });
const uploadFile = ref<File | null>(null);
const uploadPreviewChunks = ref<ChunkPreview[]>([]);
const uploadPreviewLoading = ref(false);
const uploadPreviewId = ref<string | null>(null);

const versionDrawerVisible = ref(false);
const versionLoading = ref(false);
const versions = ref<FileVersionData[]>([]);
const selectedFileId = ref<number | null>(null);
const currentFileVersion = ref<number | null>(null);

const versionUploadDrawerVisible = ref(false);
const versionUploadLoading = ref(false);
const versionUploadFileId = ref<number | null>(null);
const versionUploadFileName = ref("");
const versionUploadFile = ref<File | null>(null);
const versionUploadForm = reactive({ maxChars: 600, overlap: 100, changeNote: "" });
const versionUploadPreviewChunks = ref<ChunkPreview[]>([]);
const versionUploadPreviewLoading = ref(false);
const versionUploadPreviewId = ref<string | null>(null);

const selectedDocIds = ref<string[]>([]);

const addDocDrawerVisible = ref(false);
const addDocLoading = ref(false);
const addDocList = reactive<{ question: string; answer: string }[]>([]);

const deleteFileId = ref<number | null>(null);
const deleteFileVisible = ref(false);

const filteredFileId = ref<number | null>(null);
const filteredFileName = ref<string>("");

const docDetailDrawerVisible = ref(false);
const selectedDoc = ref<KnowledgeDocument | null>(null);

watch(
  () => [uploadForm.maxChars, uploadForm.overlap],
  () => {
    uploadPreviewChunks.value = [];
    uploadPreviewId.value = null;
  }
);

watch(
  () => [versionUploadForm.maxChars, versionUploadForm.overlap],
  () => {
    versionUploadPreviewChunks.value = [];
    versionUploadPreviewId.value = null;
  }
);

async function loadFiles() {
  loading.value = true;
  try {
    const res = await knowledgeApi.getFiles(
      collectionName.value,
      filePagination.current,
      filePagination.pageSize
    );
    if (res.data.code === "0000" && res.data.data) {
      files.value = res.data.data.fileList || [];
      filePagination.total = res.data.data.total || 0;
    }
  } catch (e) {
    console.error("Failed to load files:", e);
  } finally {
    loading.value = false;
  }
}

async function loadDocuments() {
  try {
    const res = await knowledgeApi.getDocuments(
      collectionName.value,
      docPagination.current,
      docPagination.pageSize,
      docSearchKeyword.value || undefined,
      filteredFileId.value ?? undefined
    );
    if (res.data.code === "0000" && res.data.data) {
      documents.value = res.data.data.docList || [];
      docPagination.total = res.data.data.total || 0;
    }
  } catch (e) {
    console.error("Failed to load documents:", e);
  }
}

function selectFile(file: FileData | null) {
  if (file) {
    filteredFileId.value = file.id;
    filteredFileName.value = file.filename;
  } else {
    filteredFileId.value = null;
    filteredFileName.value = "";
  }
  docPagination.current = 1;
  loadDocuments();
}

function handleFilePageChange(page: number) {
  filePagination.current = page;
  loadFiles();
}

function handleDocPageChange(page: number) {
  docPagination.current = page;
  loadDocuments();
}

function handleDocSearch() {
  docPagination.current = 1;
  loadDocuments();
}

function goBack() {
  router.push("/knowledge");
}

function openUploadDrawer() {
  uploadForm.maxChars = 600;
  uploadForm.overlap = 100;
  uploadFile.value = null;
  uploadPreviewChunks.value = [];
  uploadPreviewId.value = null;
  uploadDrawerVisible.value = true;
}

function handleUploadChange(fileList: FileItem[]) {
  const fileItem = fileList[0];
  uploadFile.value = fileItem?.file || null;
  uploadPreviewChunks.value = [];
  uploadPreviewId.value = null;
}

async function handlePreviewChunks() {
  if (!uploadFile.value) {
    Message.warning("请选择文件");
    return;
  }

  uploadPreviewLoading.value = true;
  try {
    const res = await knowledgeApi.previewFileChunks(
      uploadFile.value,
      uploadForm.maxChars,
      uploadForm.overlap
    );
    if (res.data.code === "0000" && res.data.data) {
      uploadPreviewChunks.value = res.data.data.chunks;
      uploadPreviewId.value = res.data.data.previewId;
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to preview chunks:", e);
  } finally {
    uploadPreviewLoading.value = false;
  }
}

async function handleUpload() {
  if (!uploadFile.value) {
    Message.warning("请选择文件");
    return;
  }

  uploadLoading.value = true;
  try {
    const res = await knowledgeApi.uploadFile(
      collectionName.value,
      uploadFile.value,
      uploadForm.maxChars,
      uploadForm.overlap,
      uploadPreviewId.value || undefined
    );
    if (res.data.code === "0000") {
      Message.success("上传成功");
      uploadDrawerVisible.value = false;
      loadFiles();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to upload file:", e);
  } finally {
    uploadLoading.value = false;
  }
}

function confirmDeleteFile(fileId: number) {
  deleteFileId.value = fileId;
  deleteFileVisible.value = true;
}

async function handleDeleteFile() {
  if (!deleteFileId.value) return;
  try {
    const res = await knowledgeApi.deleteFile(deleteFileId.value, collectionName.value);
    if (res.data.code === "0000") {
      Message.success("删除成功");
      deleteFileVisible.value = false;
      loadFiles();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to delete file:", e);
  }
}

async function reparseFile(fileId: number) {
  try {
    const res = await knowledgeApi.reparseFile(fileId);
    if (res.data.code === "0000") {
      Message.success("重新解析已触发");
      loadFiles();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to reparse file:", e);
  }
}

function downloadFile(file: FileData) {
  if (file.filePath) {
    window.open("/" + file.filePath, "_blank");
  }
}

function downloadVersionFile(filePath: string) {
  window.open("/" + filePath, "_blank");
}

async function openVersionDrawer(fileId: number, currentVersion: number) {
  selectedFileId.value = fileId;
  currentFileVersion.value = currentVersion;
  versionDrawerVisible.value = true;
  versionLoading.value = true;
  try {
    const res = await knowledgeApi.getFileVersions(fileId);
    if (res.data.code === "0000" && res.data.data) {
      versions.value = res.data.data.versions || [];
    }
  } catch (e) {
    console.error("Failed to load versions:", e);
  } finally {
    versionLoading.value = false;
  }
}

function openDocDetail(doc: KnowledgeDocument) {
  selectedDoc.value = doc;
  docDetailDrawerVisible.value = true;
}

async function rollbackVersion(fileId: number, version: number) {
  try {
    const res = await knowledgeApi.rollbackVersion(fileId, version);
    if (res.data.code === "0000") {
      Message.success("回滚成功");
      currentFileVersion.value = version;
      await openVersionDrawer(fileId, version);
      loadFiles();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to rollback:", e);
  }
}

function openVersionUploadDrawer(fileId: number, filename: string) {
  versionUploadFileId.value = fileId;
  versionUploadFileName.value = filename;
  versionUploadForm.maxChars = 600;
  versionUploadForm.overlap = 100;
  versionUploadForm.changeNote = "";
  versionUploadFile.value = null;
  versionUploadPreviewChunks.value = [];
  versionUploadPreviewId.value = null;
  versionUploadDrawerVisible.value = true;
}

function handleVersionUploadChange(fileList: FileItem[]) {
  const fileItem = fileList[0];
  versionUploadFile.value = fileItem?.file || null;
  versionUploadPreviewChunks.value = [];
  versionUploadPreviewId.value = null;
}

async function handleVersionUploadPreview() {
  if (!versionUploadFile.value) {
    Message.warning("请选择文件");
    return;
  }

  versionUploadPreviewLoading.value = true;
  try {
    const res = await knowledgeApi.previewFileChunks(
      versionUploadFile.value,
      versionUploadForm.maxChars,
      versionUploadForm.overlap
    );
    if (res.data.code === "0000" && res.data.data) {
      versionUploadPreviewChunks.value = res.data.data.chunks;
      versionUploadPreviewId.value = res.data.data.previewId;
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to preview chunks:", e);
  } finally {
    versionUploadPreviewLoading.value = false;
  }
}

async function handleVersionUpload() {
  if (!versionUploadFile.value) {
    Message.warning("请选择文件");
    return;
  }

  versionUploadLoading.value = true;
  try {
    const res = await knowledgeApi.uploadFileVersion(
      versionUploadFileId.value!,
      versionUploadFile.value,
      versionUploadForm.changeNote || undefined,
      versionUploadForm.maxChars,
      versionUploadForm.overlap
    );
    if (res.data.code === "0000") {
      Message.success("版本上传成功");
      versionUploadDrawerVisible.value = false;
      loadFiles();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to upload version:", e);
  } finally {
    versionUploadLoading.value = false;
  }
}

function handleDocSelectionChange(keys: (string | number)[]) {
  selectedDocIds.value = keys as string[];
}

async function deleteDocuments() {
  if (selectedDocIds.value.length === 0) {
    Message.warning("请选择要删除的知识点");
    return;
  }

  try {
    const res = await knowledgeApi.deleteDocuments(
      collectionName.value,
      selectedDocIds.value
    );
    if (res.data.code === "0000") {
      Message.success("删除成功");
      selectedDocIds.value = [];
      loadFiles();
      loadDocuments();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to delete documents:", e);
  }
}

function openAddDocDrawer() {
  addDocList.splice(0);
  addDocList.push({ question: "", answer: "" });
  addDocDrawerVisible.value = true;
}

function addDocItem() {
  addDocList.push({ question: "", answer: "" });
}

function removeDocItem(index: number) {
  if (addDocList.length > 1) {
    addDocList.splice(index, 1);
  }
}

async function handleAddDocuments() {
  const validDocs = addDocList.filter((doc) => doc.question.trim() && doc.answer.trim());
  if (validDocs.length === 0) {
    Message.warning("请至少填写一条有效的问答");
    return;
  }

  addDocLoading.value = true;
  try {
    const res = await knowledgeApi.createDocumentsByJson(collectionName.value, validDocs);
    if (res.data.code === "0000") {
      Message.success(`成功创建 ${validDocs.length} 条知识点`);
      addDocDrawerVisible.value = false;
      loadFiles();
      loadDocuments();
    } else {
      Message.error(res.data.msg);
    }
  } catch (e) {
    console.error("Failed to add documents:", e);
  } finally {
    addDocLoading.value = false;
  }
}

async function handleSearch() {
  if (!queryText.value.trim()) {
    Message.warning("请输入查询内容");
    return;
  }

  searchLoading.value = true;
  try {
    const res = await knowledgeApi.queryDocuments(
      collectionName.value,
      queryText.value.trim(),
      topK.value,
      scoreThreshold.value
    );
    if (res.data.code === "0000" && res.data.data) {
      searchResults.value = res.data.data.docList || [];
    }
  } catch (e) {
    console.error("Failed to search:", e);
  } finally {
    searchLoading.value = false;
  }
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function formatDate(dateStr?: string) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    Message.success("已复制到剪贴板");
  });
}

function getFileIcon(fileType: string) {
  const icons: Record<string, string> = {
    pdf: "mdi:file-pdf-box",
    docx: "mdi:file-word-box",
    xlsx: "mdi:file-excel-box",
    xls: "mdi:file-excel-box",
    csv: "mdi:file-delimiter",
    json: "mdi:code-json",
  };
  return icons[fileType] || "mdi:file-document-outline";
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    pending: "gray",
    parsing: "orange",
    parsed: "green",
    failed: "red",
  };
  return colors[status] || "gray";
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    pending: "待解析",
    parsing: "解析中",
    parsed: "已完成",
    failed: "失败",
  };
  return texts[status] || status;
}

onMounted(() => {
  loadFiles();
  loadDocuments();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div
      class="px-6 py-4 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <a-button type="text" @click="goBack">
            <template #icon><Icon icon="mdi:arrow-left" class="text-lg" /></template>
          </a-button>
          <h1 class="text-lg font-bold text-slate-900 dark:text-white">
            {{ collectionName }}
          </h1>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-hidden flex gap-4 p-4">
      <section class="w-1/4 flex flex-col gap-4 min-w-[280px]">
        <div
          class="flex-1 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden"
        >
          <div
            class="flex justify-between items-center px-4 py-3 border-b border-slate-200 dark:border-slate-700"
          >
            <h2 class="text-sm font-bold text-slate-900 dark:text-white">文件管理</h2>
            <span
              class="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded-full font-medium"
            >
              {{ filePagination.total }} 个文件
            </span>
          </div>

          <div class="p-3 border-b border-slate-100 dark:border-slate-700">
            <a-button type="primary" long size="small" @click="openUploadDrawer">
              <template #icon><Icon icon="mdi:cloud-upload" /></template>
              上传文件
            </a-button>
          </div>

          <div class="flex-1 overflow-y-auto">
            <a-spin :loading="loading" class="w-full">
              <div
                v-if="files.length === 0"
                class="text-center py-8 text-slate-400 text-sm"
              >
                暂无文件
              </div>
              <div v-else class="divide-y divide-slate-100 dark:divide-slate-700">
                <div
                  v-for="file in files"
                  :key="file.id"
                  class="p-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer group"
                  :class="{
                    'bg-primary/5 border-l-2 border-l-primary':
                      filteredFileId === file.id,
                  }"
                  @click="selectFile(file)"
                >
                  <div class="flex items-start gap-2">
                    <Icon
                      :icon="getFileIcon(file.fileType)"
                      class="text-xl text-slate-400 mt-0.5"
                    />
                    <div class="flex-1 min-w-0">
                      <h3
                        class="text-sm font-medium text-slate-700 dark:text-slate-200 truncate"
                      >
                        {{ file.filename }}
                      </h3>
                      <div class="flex items-center gap-2 mt-1">
                        <span class="text-xs text-slate-400">{{
                          formatFileSize(file.fileSize)
                        }}</span>
                        <a-tag :color="getStatusColor(file.status)" size="small">
                          {{ getStatusText(file.status) }}
                        </a-tag>
                      </div>
                      <div class="flex items-center justify-between mt-2">
                        <span class="text-xs text-slate-400">
                          v{{ file.version }} · {{ file.chunkCount }} chunks
                        </span>
                        <a-dropdown
                          trigger="click"
                          @click.stop
                          v-if="file.filePath != 'json'"
                        >
                          <a-button
                            type="text"
                            size="mini"
                            class="opacity-0 group-hover:opacity-100"
                          >
                            <template #icon><Icon icon="mdi:dots-horizontal" /></template>
                          </a-button>
                          <template #content>
                            <a-doption
                              v-if="file.filePath"
                              @click.stop="downloadFile(file)"
                            >
                              <template #icon><Icon icon="mdi:download" /></template>
                              下载文件
                            </a-doption>
                            <a-doption
                              @click.stop="
                                openVersionUploadDrawer(file.id, file.filename)
                              "
                            >
                              <template #icon><Icon icon="mdi:upload" /></template>
                              上传新版本
                            </a-doption>
                            <a-doption
                              @click.stop="openVersionDrawer(file.id, file.version)"
                            >
                              <template #icon><Icon icon="mdi:history" /></template>
                              版本历史
                            </a-doption>
                            <a-doption @click.stop="reparseFile(file.id)">
                              <template #icon><Icon icon="mdi:refresh" /></template>
                              重新解析
                            </a-doption>
                            <a-doption
                              class="text-red-500"
                              @click="confirmDeleteFile(file.id)"
                            >
                              <template #icon><Icon icon="mdi:delete" /></template>
                              删除文件
                            </a-doption>
                          </template>
                        </a-dropdown>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </a-spin>
          </div>

          <div
            v-if="filePagination.total > filePagination.pageSize"
            class="p-3 border-t border-slate-200 dark:border-slate-700"
          >
            <a-pagination
              :current="filePagination.current"
              :page-size="filePagination.pageSize"
              :total="filePagination.total"
              size="small"
              simple
              @change="handleFilePageChange"
            />
          </div>
        </div>
      </section>

      <section class="flex-1 flex flex-col gap-4 min-w-0">
        <div
          class="flex-1 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden"
        >
          <div
            class="flex justify-between items-center px-4 py-3 border-b border-slate-200 dark:border-slate-700"
          >
            <div class="flex items-center gap-2">
              <h2 class="text-sm font-bold text-slate-900 dark:text-white">
                {{ filteredFileName || "知识点列表" }}
              </h2>
              <a-button
                v-if="filteredFileId"
                type="text"
                size="mini"
                @click="selectFile(null)"
              >
                <template #icon><Icon icon="mdi:close" /></template>
                显示全部
              </a-button>
            </div>
            <div class="flex items-center gap-2">
              <a-button
                v-if="selectedDocIds.length > 0"
                size="small"
                status="danger"
                @click="deleteDocuments"
              >
                <template #icon><Icon icon="mdi:delete" /></template>
                删除 ({{ selectedDocIds.length }})
              </a-button>
              <a-button size="small" type="primary" @click="openAddDocDrawer">
                <template #icon><Icon icon="mdi:plus" /></template>
                新增知识点
              </a-button>

              <a-input
                v-model="docSearchKeyword"
                placeholder="搜索知识点..."
                size="small"
                style="width: 180px"
                allow-clear
                @press-enter="handleDocSearch"
              >
                <template #prefix><Icon icon="mdi:magnify" /></template>
              </a-input>
              <a-button size="small" type="text" @click="handleDocSearch">
                <template #icon><Icon icon="mdi:filter-variant" /></template>
              </a-button>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto">
            <a-table
              :data="documents"
              :loading="loading"
              :pagination="false"
              :row-selection="{
                type: 'checkbox',
                selectedRowKeys: selectedDocIds,
                showCheckedAll: true,
              }"
              row-key="id"
              @selection-change="handleDocSelectionChange"
            >
              <template #columns>
                <a-table-column title="内容" data-index="content">
                  <template #cell="{ record }">
                    <p
                      class="text-sm text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed cursor-pointer hover:text-primary transition-colors"
                      @click="openDocDetail(record)"
                    >
                      {{ record.content }}
                    </p>
                  </template>
                </a-table-column>
                <a-table-column title="字符数" :width="80" align="center">
                  <template #cell="{ record }">
                    <span class="text-xs text-slate-400">{{
                      record.content.length
                    }}</span>
                  </template>
                </a-table-column>
                <a-table-column title="文档类型" :width="140">
                  <template #cell="{ record }">
                    <span class="text-xs text-slate-400">
                      {{ record.docType || "-" }}
                    </span>
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </div>

          <div
            class="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between"
          >
            <span class="text-xs text-slate-400">共 {{ docPagination.total }} 条</span>
            <a-pagination
              v-if="docPagination.total > docPagination.pageSize"
              :current="docPagination.current"
              :page-size="docPagination.pageSize"
              :total="docPagination.total"
              size="small"
              simple
              @change="handleDocPageChange"
            />
          </div>
        </div>
      </section>

      <section class="w-1/4 flex flex-col gap-4 min-w-[300px]">
        <div
          class="flex-1 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden"
        >
          <div
            class="flex items-center gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-700"
          >
            <Icon icon="mdi:vector-search" class="text-primary text-lg" />
            <h2 class="text-sm font-bold text-slate-900 dark:text-white">向量搜索</h2>
          </div>

          <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <div class="space-y-2">
              <label class="text-xs font-bold text-slate-400 uppercase tracking-wider"
                >查询内容</label
              >
              <a-textarea
                v-model="queryText"
                placeholder="输入查询内容..."
                :auto-size="{ minRows: 3, maxRows: 6 }"
              />
            </div>

            <div class="space-y-3">
              <div class="space-y-2">
                <div class="flex justify-between items-center">
                  <label class="text-xs font-bold text-slate-400 uppercase tracking-wider"
                    >Top K</label
                  >
                  <span class="text-xs font-bold text-primary">{{ topK }}</span>
                </div>
                <a-slider v-model="topK" :min="1" :max="20" />
              </div>

              <div class="space-y-2">
                <div class="flex justify-between items-center">
                  <label class="text-xs font-bold text-slate-400 uppercase tracking-wider"
                    >相似度阈值</label
                  >
                  <span class="text-xs font-bold text-primary">{{
                    scoreThreshold.toFixed(2)
                  }}</span>
                </div>
                <a-slider v-model="scoreThreshold" :min="0.5" :max="1" :step="0.05" />
              </div>
            </div>

            <a-button type="primary" long :loading="searchLoading" @click="handleSearch">
              <template #icon><Icon icon="mdi:play" /></template>
              执行搜索
            </a-button>

            <div v-if="searchResults.length > 0" class="space-y-3 pt-2">
              <h3
                class="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 pb-2"
              >
                搜索结果
              </h3>
              <div
                v-for="(result, index) in searchResults"
                :key="result.id"
                class="p-3 rounded-lg border transition-colors"
                :class="
                  index === 0
                    ? 'bg-primary/5 border-primary/20'
                    : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600'
                "
              >
                <div class="flex justify-between items-center mb-1">
                  <span
                    class="text-xs font-bold"
                    :class="index === 0 ? 'text-primary' : 'text-slate-500'"
                  >
                    SCORE: {{ result.score.toFixed(3) }}
                  </span>
                </div>
                <p
                  class="text-xs text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed"
                >
                  {{ result.content }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div
          class="bg-gradient-to-br from-primary to-blue-700 p-4 rounded-xl shadow-lg text-white"
        >
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-xs font-bold uppercase tracking-wider opacity-80">
              索引状态
            </h3>
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-1.5 rounded-full bg-green-400"></div>
              <span class="text-xs font-bold uppercase tracking-wider">Active</span>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <p class="text-xs opacity-80">知识库</p>
              <p class="text-base font-bold truncate">{{ collectionName }}</p>
            </div>
            <div>
              <p class="text-xs opacity-80">知识点数</p>
              <p class="text-base font-bold">{{ docPagination.total }}</p>
            </div>
          </div>
        </div>
      </section>
    </div>

    <a-drawer
      v-model:visible="uploadDrawerVisible"
      title="上传文件"
      :width="550"
      :footer="true"
    >
      <div class="flex flex-col h-full overflow-x-hidden">
        <a-form :model="uploadForm" layout="vertical" class="flex-shrink-0">
          <a-form-item label="选择文件" required>
            <a-upload
              :auto-upload="false"
              :file-list="uploadFile ? [{ uid: '1', name: uploadFile.name }] : []"
              :show-file-list="false"
              accept=".pdf,.docx,.xlsx,.xls,.csv,.tsv,.json,.txt,.md"
              @change="handleUploadChange"
            >
              <template #upload-button>
                <a-button type="primary">
                  <template #icon><Icon icon="mdi:file-plus" /></template>
                  选择文件
                </a-button>
              </template>
            </a-upload>
            <p v-if="uploadFile" class="mt-2 text-sm text-slate-600 dark:text-slate-300">
              已选择: {{ uploadFile.name }}
            </p>
          </a-form-item>
          <div class="flex gap-4">
            <a-form-item label="最大字符数" class="flex-1">
              <a-input-number
                v-model="uploadForm.maxChars"
                :min="100"
                :max="2000"
                :step="100"
                style="width: 100%"
              />
            </a-form-item>
            <a-form-item label="重叠字符数" class="flex-1">
              <a-input-number
                v-model="uploadForm.overlap"
                :min="0"
                :max="500"
                :step="50"
                style="width: 100%"
              />
            </a-form-item>
          </div>
          <a-form-item>
            <a-button
              type="outline"
              long
              :loading="uploadPreviewLoading"
              :disabled="!uploadFile"
              @click="handlePreviewChunks"
            >
              <template #icon><Icon icon="mdi:text-box-search" /></template>
              预览分块
            </a-button>
          </a-form-item>
        </a-form>

        <div
          v-if="uploadPreviewChunks.length > 0"
          class="flex-1 flex flex-col min-h-0 border-t border-slate-200 dark:border-slate-700 -mx-6 px-6 pt-4"
        >
          <div class="flex items-center justify-between flex-shrink-0 mb-3">
            <span class="text-sm font-medium text-slate-700 dark:text-slate-300">
              分块预览 ({{ uploadPreviewChunks.length }} 个)
            </span>
            <a-button type="text" size="mini" @click="uploadPreviewChunks = []">
              清空
            </a-button>
          </div>
          <div class="flex-1 overflow-y-auto space-y-2 -mx-2 px-2">
            <div
              v-for="(chunk, index) in uploadPreviewChunks"
              :key="index"
              class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-bold text-slate-400"
                  >#{{ chunk.chunkIndex ?? index + 1 }}</span
                >
                <span class="text-xs text-slate-400"
                  >{{ chunk.content.length }} 字符</span
                >
              </div>
              <p
                class="text-xs text-slate-600 dark:text-slate-300 whitespace-pre-wrap break-words"
              >
                {{ chunk.content }}
              </p>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <a-space>
          <a-button @click="uploadDrawerVisible = false">取消</a-button>
          <a-button type="primary" :loading="uploadLoading" @click="handleUpload">
            确认上传
          </a-button>
        </a-space>
      </template>
    </a-drawer>

    <a-drawer
      v-model:visible="versionDrawerVisible"
      title="版本历史"
      :width="400"
      :footer="false"
    >
      <a-spin :loading="versionLoading" class="w-full">
        <div v-if="versions.length === 0" class="text-center py-8 text-slate-400">
          暂无版本记录
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="ver in versions"
            :key="ver.id"
            class="p-3 rounded-lg"
            :class="
              ver.version === currentFileVersion
                ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                : 'bg-slate-50 dark:bg-slate-700/50'
            "
          >
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="text-sm font-bold text-slate-700 dark:text-slate-200">
                  v{{ ver.version }}
                </span>
                <a-tag
                  v-if="ver.version === currentFileVersion"
                  color="green"
                  size="small"
                  >当前</a-tag
                >
              </div>
              <span class="text-xs text-slate-400">{{ formatDate(ver.createTime) }}</span>
            </div>
            <div class="flex items-center justify-between text-xs text-slate-500">
              <span
                >{{ formatFileSize(ver.fileSize) }} · {{ ver.chunkCount }} chunks</span
              >
              <div class="flex items-center gap-1">
                <a-button
                  v-if="ver.filePath"
                  type="text"
                  size="mini"
                  @click="downloadVersionFile(ver.filePath)"
                >
                  下载
                </a-button>
                <a-button
                  v-if="ver.version !== currentFileVersion"
                  type="text"
                  size="mini"
                  @click="rollbackVersion(selectedFileId!, ver.version)"
                >
                  回滚
                </a-button>
              </div>
            </div>
            <p v-if="ver.changeNote" class="text-xs text-slate-400 mt-2">
              {{ ver.changeNote }}
            </p>
          </div>
        </div>
      </a-spin>
    </a-drawer>

    <a-drawer
      v-model:visible="docDetailDrawerVisible"
      title="知识点详情"
      :width="550"
      :footer="false"
    >
      <div v-if="selectedDoc" class="space-y-4">
        <div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider"
              >内容</span
            >
            <a-button
              type="text"
              size="mini"
              @click="copyToClipboard(selectedDoc.content)"
            >
              <template #icon><Icon icon="mdi:content-copy" /></template>
              复制
            </a-button>
          </div>
          <p
            class="text-sm text-slate-700 dark:text-slate-200 whitespace-pre-wrap break-words leading-relaxed"
          >
            {{ selectedDoc.content }}
          </p>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider"
              >字符数</span
            >
            <p class="text-sm font-medium text-slate-700 dark:text-slate-200 mt-1">
              {{ selectedDoc.content.length }}
            </p>
          </div>
          <div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider"
              >文档类型</span
            >
            <p class="text-sm font-medium text-slate-700 dark:text-slate-200 mt-1">
              {{ selectedDoc.docType || "-" }}
            </p>
          </div>
        </div>

        <div
          v-if="selectedDoc.source"
          class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
        >
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider"
            >来源信息</span
          >
          <div class="mt-2 space-y-1">
            <div v-if="selectedDoc.source.filePath" class="flex items-center gap-2">
              <Icon icon="mdi:file-outline" class="text-slate-400" />
              <span class="text-sm text-slate-700 dark:text-slate-200">{{
                selectedDoc.source.filePath
              }}</span>
            </div>
            <div v-if="selectedDoc.source.pageNum" class="flex items-center gap-2">
              <Icon icon="mdi:book-open-page-variant-outline" class="text-slate-400" />
              <span class="text-sm text-slate-700 dark:text-slate-200"
                >第 {{ selectedDoc.source.pageNum }} 页</span
              >
            </div>
          </div>
        </div>

        <div
          v-if="selectedDoc.chunkIndex !== undefined"
          class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
        >
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider"
            >分块索引</span
          >
          <p class="text-sm font-medium text-slate-700 dark:text-slate-200 mt-1">
            #{{ selectedDoc.chunkIndex }}
          </p>
        </div>
      </div>
    </a-drawer>

    <a-drawer
      v-model:visible="versionUploadDrawerVisible"
      title="上传新版本"
      :width="550"
      :footer="true"
    >
      <div class="flex flex-col h-full overflow-x-hidden">
        <div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg mb-4">
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider"
            >目标文件</span
          >
          <p class="text-sm font-medium text-slate-700 dark:text-slate-200 mt-1">
            {{ versionUploadFileName }}
          </p>
        </div>

        <a-form :model="versionUploadForm" layout="vertical" class="flex-shrink-0">
          <a-form-item label="选择新版本文件" required>
            <a-upload
              :auto-upload="false"
              :file-list="
                versionUploadFile ? [{ uid: '1', name: versionUploadFile.name }] : []
              "
              :show-file-list="false"
              accept=".pdf,.docx,.xlsx,.xls,.csv,.tsv,.json,.txt,.md"
              @change="handleVersionUploadChange"
            >
              <template #upload-button>
                <a-button type="primary">
                  <template #icon><Icon icon="mdi:file-plus" /></template>
                  选择文件
                </a-button>
              </template>
            </a-upload>
            <p
              v-if="versionUploadFile"
              class="mt-2 text-sm text-slate-600 dark:text-slate-300"
            >
              已选择: {{ versionUploadFile.name }}
            </p>
          </a-form-item>
          <a-form-item label="变更说明">
            <a-input
              v-model="versionUploadForm.changeNote"
              placeholder="可选：描述本次更新的内容..."
            />
          </a-form-item>
          <div class="flex gap-4">
            <a-form-item label="最大字符数" class="flex-1">
              <a-input-number
                v-model="versionUploadForm.maxChars"
                :min="100"
                :max="2000"
                :step="100"
                style="width: 100%"
              />
            </a-form-item>
            <a-form-item label="重叠字符数" class="flex-1">
              <a-input-number
                v-model="versionUploadForm.overlap"
                :min="0"
                :max="500"
                :step="50"
                style="width: 100%"
              />
            </a-form-item>
          </div>
          <a-form-item>
            <a-button
              type="outline"
              long
              :loading="versionUploadPreviewLoading"
              :disabled="!versionUploadFile"
              @click="handleVersionUploadPreview"
            >
              <template #icon><Icon icon="mdi:text-box-search" /></template>
              预览分块
            </a-button>
          </a-form-item>
        </a-form>

        <div
          v-if="versionUploadPreviewChunks.length > 0"
          class="flex-1 flex flex-col min-h-0 border-t border-slate-200 dark:border-slate-700 -mx-6 px-6 pt-4"
        >
          <div class="flex items-center justify-between flex-shrink-0 mb-3">
            <span class="text-sm font-medium text-slate-700 dark:text-slate-300">
              分块预览 ({{ versionUploadPreviewChunks.length }} 个)
            </span>
            <a-button type="text" size="mini" @click="versionUploadPreviewChunks = []">
              清空
            </a-button>
          </div>
          <div class="flex-1 overflow-y-auto space-y-2 -mx-2 px-2">
            <div
              v-for="(chunk, index) in versionUploadPreviewChunks"
              :key="index"
              class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-bold text-slate-400"
                  >#{{ chunk.chunkIndex ?? index + 1 }}</span
                >
                <span class="text-xs text-slate-400"
                  >{{ chunk.content.length }} 字符</span
                >
              </div>
              <p
                class="text-xs text-slate-600 dark:text-slate-300 whitespace-pre-wrap break-words"
              >
                {{ chunk.content }}
              </p>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <a-space>
          <a-button @click="versionUploadDrawerVisible = false">取消</a-button>
          <a-button
            type="primary"
            :loading="versionUploadLoading"
            @click="handleVersionUpload"
          >
            确认上传
          </a-button>
        </a-space>
      </template>
    </a-drawer>

    <a-drawer
      v-model:visible="addDocDrawerVisible"
      title="新增知识点"
      :width="550"
      :footer="true"
    >
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-sm text-slate-500">共 {{ addDocList.length }} 条</span>
          <a-button type="text" size="small" @click="addDocItem">
            <template #icon><Icon icon="mdi:plus" /></template>
            添加一条
          </a-button>
        </div>

        <div
          v-for="(doc, index) in addDocList"
          :key="index"
          class="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg relative"
        >
          <a-button
            v-if="addDocList.length > 1"
            type="text"
            size="mini"
            status="danger"
            class="absolute top-2 right-2"
            @click="removeDocItem(index)"
          >
            <template #icon><Icon icon="mdi:close" /></template>
          </a-button>
          <div class="space-y-3">
            <div>
              <label class="text-xs font-medium text-slate-500 mb-1 block">问题</label>
              <a-textarea
                v-model="doc.question"
                placeholder="请输入问题..."
                :auto-size="{ minRows: 2, maxRows: 4 }"
              />
            </div>
            <div>
              <label class="text-xs font-medium text-slate-500 mb-1 block">答案</label>
              <a-textarea
                v-model="doc.answer"
                placeholder="请输入答案..."
                :auto-size="{ minRows: 2, maxRows: 6 }"
              />
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <a-space>
          <a-button @click="addDocDrawerVisible = false">取消</a-button>
          <a-button type="primary" :loading="addDocLoading" @click="handleAddDocuments">
            确认添加
          </a-button>
        </a-space>
      </template>
    </a-drawer>

    <a-modal
      v-model:visible="deleteFileVisible"
      title="确认删除"
      @ok="handleDeleteFile"
      @cancel="deleteFileVisible = false"
    >
      <p>确定要删除此文件吗？删除后无法恢复。</p>
    </a-modal>
  </div>
</template>
