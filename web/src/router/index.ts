import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页', icon: 'home' },
  },
  {
    path: '/debug',
    name: 'InteractiveDebug',
    component: () => import('@/views/debug/InteractiveDebug.vue'),
    meta: { title: '交互调试', icon: 'chat' },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    meta: { title: '知识库管理', icon: 'database' },
    children: [
      {
        path: '',
        name: 'KnowledgeList',
        component: () => import('@/views/knowledge/KnowledgeList.vue'),
        meta: { title: '知识库列表' },
      },
      {
        path: ':name',
        name: 'KnowledgeDetail',
        component: () => import('@/views/knowledge/KnowledgeDetail.vue'),
        meta: { title: '知识库详情' },
      },
    ],
  },
  {
    path: '/rules',
    name: 'Rules',
    meta: { title: '规则配置', icon: 'rule' },
    children: [
      {
        path: 'commands',
        name: 'Commands',
        component: () => import('@/views/command/CommandList.vue'),
        meta: { title: '命令词管理', icon: 'terminal' },
      },
      {
        path: 'sensitive',
        name: 'Sensitive',
        component: () => import('@/views/sensitive/SensitiveList.vue'),
        meta: { title: '敏感词管理', icon: 'shield' },
      },
      {
        path: 'flows',
        name: 'Flows',
        component: () => import('@/views/flow/FlowList.vue'),
        meta: { title: '流程管理', icon: 'fork' },
      },
    ],
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('@/views/tool/ToolList.vue'),
    meta: { title: '工具管理', icon: 'tool' },
  },
  {
    path: '/models',
    name: 'Models',
    meta: { title: '模型管理', icon: 'model' },
    children: [
      {
        path: 'providers',
        name: 'ModelProviders',
        component: () => import('@/views/model/ModelProvider.vue'),
        meta: { title: '渠道商管理', icon: 'cloud' },
      },
      {
        path: 'sources',
        name: 'ModelSources',
        component: () => import('@/views/model/ModelSource.vue'),
        meta: { title: '模型源管理', icon: 'cpu' },
      },
    ],
  },
  {
    path: '/prompts',
    name: 'Prompts',
    component: () => import('@/views/prompt/PromptList.vue'),
    meta: { title: '提示词管理', icon: 'edit' },
  },
  {
    path: '/robot',
    name: 'Robot',
    meta: { title: '机器人控制', icon: 'robot' },
    children: [
      {
        path: 'expressions',
        name: 'Expressions',
        component: () => import('@/views/robot/ExpressionList.vue'),
        meta: { title: '表情管理', icon: 'face' },
      },
      {
        path: 'actions',
        name: 'Actions',
        component: () => import('@/views/robot/ActionList.vue'),
        meta: { title: '动作管理', icon: 'directions-run' },
      },
    ],
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: () => import('@/views/analytics/Analytics.vue'),
    meta: { title: '数据分析', icon: 'chart' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/Settings.vue'),
    meta: { title: '系统设置', icon: 'setting' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - Chat2RAG`
  }
  next()
})

export default router