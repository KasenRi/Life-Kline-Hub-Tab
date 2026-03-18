import { defineStore } from 'pinia'
import type { UserState } from './helper'
import { defaultSetting, getLocalState, getStoredState, setLocalState } from './helper'

export const useUserStore = defineStore('user-store', {
  state: (): UserState => getLocalState(),
  actions: {
    async hydrateFromStorage() {
      this.$state = await getStoredState()
      this.recordState()
    },

    updateUserInfo(userInfo: User.Info) {
      this.userInfo = { ...this.userInfo, ...userInfo }
      this.recordState()
    },

    // updateUserHeadImage(userInfo: User.Info) {
    //   this.userInfo = { ...this.userInfo, ...userInfo }
    //   this.recordState()
    // },

    resetUserInfo() {
      this.userInfo = { ...defaultSetting().userInfo }
      this.recordState()
    },

    recordState() {
      setLocalState(this.$state)
    },
  },
})
