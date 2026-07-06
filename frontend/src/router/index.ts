import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/app/'),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/pages/Dashboard.vue'),
    },
    {
      path: '/connection',
      name: 'Connection',
      component: () => import('@/pages/Connection.vue'),
    },
    {
      path: '/tools',
      name: 'ToolConsole',
      component: () => import('@/pages/ToolConsole.vue'),
    },
    {
      path: '/files',
      name: 'FileBrowser',
      component: () => import('@/pages/FileBrowser.vue'),
    },
    {
      path: '/skills',
      name: 'SkillsView',
      component: () => import('@/pages/SkillsView.vue'),
    },
    {
      path: '/prompt',
      name: 'PromptViewer',
      component: () => import('@/pages/PromptViewer.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/pages/Settings.vue'),
    },
  ],
})

export default router
