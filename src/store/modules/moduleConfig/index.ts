import { defineStore } from 'pinia'
import type { ModuleConfigState } from './helper'
import { getLocalState, getStoredState, setLocalState } from './helper'
import { getValueByName, save } from '@/api/system/moduleConfig'

export const useModuleConfig = defineStore('module-config-store', {
  state: (): ModuleConfigState => getLocalState(),
  actions: {
    async hydrateFromStorage() {
      this.$state = await getStoredState()
      this.recordState()
    },

    getValueByNameFromLocal<T>(name: string): T | null {
      const moduleName = `module-${name}`
      return this.$state[moduleName] ?? null
    },

    saveToLocal(name: string, value: any) {
      const moduleName = `module-${name}`
      this.$state[moduleName] = value
      this.recordState()
      return value
    },

    // 保存
    // save(name: string, value: any) {
    //   const moduleName = `module-${name}`
    //   // 保存至网络
    //   console.log('保存模块配置', name, value)
    //   this.$state[moduleName] = value
    //   this.recordState()
    //   save(moduleName, value)
    // },

    // // 获取值
    // getValueByName<T>(name: string): T | null {
    //   const moduleName = `module-${name}`
    //   this.syncFromCloud(moduleName)
    //   if (this.$state[moduleName])
    //     return this.$state[moduleName]
    //   return null
    // },

    // 获取值
    async getValueByNameFromCloud<T>(name: string) {
      const moduleName = `module-${name}`
      const res = await getValueByName<T>(moduleName)
      if (res.code === 0)
        this.saveToLocal(name, res.data)
      return res
    },

    // 保存到网络
    async saveToCloud(name: string, value: any) {
      const moduleName = `module-${name}`
      this.saveToLocal(name, value)
      // 保存至网络
      return save(moduleName, value)
    },

    // 从网络同步
    // syncFromCloud(moduleName: string) {
    //   getValueByName<any>(moduleName).then(({ code, data, msg }) => {
    //     if (code === 0)
    //       this.$state[moduleName] = data
    //   })
    // },

    recordState() {
      setLocalState(this.$state)
    },
  },
})
