import { defineStore } from 'pinia'
import { getStorage, getStoredStorage, removeToken as hRemoveToken, setStorage } from './helper'
import { VisitMode } from '@/enums/auth'

// interface SessionResponse {
//   auth: boolean
// }

export interface AuthState {
  token: string | null
  userInfo: User.Info | null
  // session: SessionResponse | null
  visitMode: VisitMode
}

const defaultState: AuthState = {
  token: null,
  userInfo: null,
  visitMode: VisitMode.VISIT_MODE_PUBLIC,
}

export const useAuthStore = defineStore('auth-store', {
  state: (): AuthState => getStorage() || defaultState,

  getters: {
    hasToken: state => Boolean(state.token),
    isLoggedIn: state => Boolean(state.token) && state.visitMode === VisitMode.VISIT_MODE_LOGIN,
  },

  actions: {
    async hydrateFromStorage() {
      this.$state = (await getStoredStorage()) || { ...defaultState }
      this.saveStorage()
    },

    setToken(token: string | null) {
      this.token = token
      this.saveStorage()
    },

    setUserInfo(userInfo: User.Info | null) {
      this.userInfo = userInfo
      this.saveStorage()
    },

    setVisitMode(visitMode: VisitMode) {
      this.visitMode = visitMode
      this.saveStorage()
    },

    saveStorage() {
      setStorage(this.$state)
    },

    applyLogin(userInfo: User.Info, token: string) {
      this.token = token
      this.userInfo = userInfo
      this.visitMode = VisitMode.VISIT_MODE_LOGIN
      this.saveStorage()
    },

    setLoggedOut() {
      this.$state = { ...defaultState }
      this.saveStorage()
    },

    removeToken() {
      this.$state = { ...defaultState }
      hRemoveToken()
    },
  },

})
