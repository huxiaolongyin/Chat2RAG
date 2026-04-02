<script setup lang="ts">
import { Icon } from "@iconify/vue"
import { ref } from "vue"

defineProps<{
  isLoading: boolean
}>()

const emit = defineEmits<{
  sendMessage: [text: string, image: string]
}>()

const inputText = ref("")
const inputImage = ref("")
const fileInput = ref<HTMLInputElement | null>(null)

function handleImageSelect(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file || !file.type.startsWith("image/")) return

  const reader = new FileReader()
  reader.onload = (e) => {
    inputImage.value = e.target?.result as string
  }
  reader.readAsDataURL(file)
}

function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  for (const item of items) {
    if (item.type.startsWith("image/")) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        const reader = new FileReader()
        reader.onload = (e) => {
          inputImage.value = e.target?.result as string
        }
        reader.readAsDataURL(file)
      }
      break
    }
  }
}

function removeImage() {
  inputImage.value = ""
  if (fileInput.value) {
    fileInput.value.value = ""
  }
}

function triggerFileInput() {
  fileInput.value?.click()
}

function handleSend() {
  if (!inputText.value.trim() && !inputImage.value) return
  emit("sendMessage", inputText.value, inputImage.value)
  inputText.value = ""
  inputImage.value = ""
  if (fileInput.value) {
    fileInput.value.value = ""
  }
}
</script>

<template>
  <div class="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
    <div v-if="inputImage" class="mb-2 relative inline-block">
      <img
        :src="inputImage"
        class="max-w-[120px] max-h-[120px] rounded-lg object-cover border border-slate-200 dark:border-slate-700"
        alt="preview"
      />
      <button
        class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center hover:bg-red-600 transition-colors"
        @click="removeImage"
      >
        <Icon icon="mdi:close" class="text-xs" />
      </button>
    </div>
    <div
      class="relative flex items-center gap-2 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-2 pr-3 focus-within:border-primary transition-all"
    >
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleImageSelect" />
      <button
        class="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        @click="triggerFileInput"
      >
        <Icon icon="mdi:image-outline" class="text-lg" />
      </button>
      <textarea
        v-model="inputText"
        class="flex-1 bg-transparent border-none focus:ring-0 text-sm resize-none py-2 max-h-32 custom-scrollbar outline-none"
        placeholder="输入消息..."
        rows="1"
        @keydown.enter.exact.prevent="handleSend"
        @paste="handlePaste"
      ></textarea>
      <a-button
        type="primary"
        shape="circle"
        :disabled="(!inputText.trim() && !inputImage) || isLoading"
        :loading="isLoading"
        @click="handleSend"
      >
        <template #icon><Icon icon="mdi:send" /></template>
      </a-button>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}
</style>