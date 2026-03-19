import { createApp } from 'vue'
import App from './App.vue'
import { setupI18n } from './locales'
import { setupAssets, setupScrollbarStyle } from './plugins'
import { setupStore, useAppStore, useAuthStore, useModuleConfig, usePanelState, useUserStore } from './store'
import { setupRouter } from './router'
import { updateLocalUserInfo } from './utils/cmn'
import 'virtual:svg-icons-register' // svg图标注册

async function bootstrap() {
  const app = createApp(App)
  setupAssets()

  setupScrollbarStyle()

  setupStore(app)

  setupI18n(app)

  await setupRouter(app)
  app.mount('#app')

  void Promise.allSettled([
    useAppStore().hydrateFromStorage(),
    useAuthStore().hydrateFromStorage(),
    useUserStore().hydrateFromStorage(),
    usePanelState().hydrateFromStorage(),
    useModuleConfig().hydrateFromStorage(),
  ]).then(() => {
    void updateLocalUserInfo()
  })
}

bootstrap().catch((error) => {
  console.error('LKTab bootstrap failed:', error)
})
