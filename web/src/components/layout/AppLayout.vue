<script setup lang="ts">
// import { useAppStore } from '@/stores/app'
import Footer from "./Footer.vue";
import Header from "./Header.vue";
import Sidebar from "./Sidebar.vue";

// const appStore = useAppStore()
</script>

<template>
  <div
    class="flex h-screen w-full overflow-hidden bg-background-light dark:bg-background-dark"
  >
    <Sidebar />
    <div class="flex flex-1 flex-col overflow-hidden">
      <Header />
      <main class="flex-1 overflow-auto bg-slate-50 dark:bg-slate-900">
        <router-view />
      </main>
      <Footer />
    </div>
  </div>
</template>
