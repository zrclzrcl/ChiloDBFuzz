import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        name: 'Logs',
        component: () => import('../views/Logs.vue'),
        meta: { title: '日志监控' }
    },
    {
        path: '/plot',
        name: 'Plot',
        component: () => import('../views/Plot.vue'),
        meta: { title: '数据大屏' }
    },
    {
        path: '/bitmap',
        name: 'Bitmap',
        component: () => import('../views/Bitmap.vue'),
        meta: { title: 'Bitmap 热力图' }
    },
    {
        path: '/settings',
        name: 'Settings',
        component: () => import('../views/Settings.vue'),
        meta: { title: '系统设置' }
    },
    {
        path: '/downloads',
        name: 'Downloads',
        component: () => import('../views/Downloads.vue'),
        meta: { title: '结果下载' }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach((to, from, next) => {
    document.title = `${to.meta.title} - ChiloDisco` || 'ChiloDisco'
    next()
})

export default router
