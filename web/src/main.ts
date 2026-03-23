import { createApp } from 'vue'
import ArcoVue from '@arco-design/web-vue'
import pinia from './stores'
import router from './router'
import { setupRouterGuard } from './router/guard'
import App from './App.vue'
import './assets/styles/main.css'
import '@arco-design/web-vue/dist/arco.css'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(ArcoVue)

setupRouterGuard(router)

app.mount('#app')