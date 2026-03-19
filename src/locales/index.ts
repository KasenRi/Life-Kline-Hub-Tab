import type { App } from 'vue'
import { ref } from 'vue'
import enUS from './en-US.json'
import zhCN from './zh-CN.json'
import type { Language } from '@/store/modules/app/helper'
import { getLocalSetting } from '@/store/modules/app/helper'

const defaultLocale = 'zh-CN'
const localeRef = ref<Language>(getLocalSetting().language || defaultLocale)

const messages = {
  'en-US': enUS,
  'zh-CN': zhCN,
}

function getMessageValue(source: Record<string, any>, key: string) {
  return key.split('.').reduce<any>((value, path) => value?.[path], source)
}

function interpolateMessage(message: string, params?: Record<string, any>) {
  if (!params)
    return message

  return message.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = params[key]
    return (value === undefined || value === null) ? `{${key}}` : String(value)
  })
}

export function t(key: string, ...args: any[]) {
  const [params] = args
  const currentMessages = messages[localeRef.value] ? messages[localeRef.value] : messages[defaultLocale]
  const fallbackMessages = messages[defaultLocale]
  const rawMessage = getMessageValue(currentMessages, key) ?? (getMessageValue(fallbackMessages, key))

  if (typeof rawMessage !== 'string')
    return key

  return interpolateMessage(rawMessage, params)
}

// 避免循环依赖appstore(authstore)language此处暂时先使用any
// 后面有时间调整
export function setLocale(locale: any) {
  localeRef.value = locale
}

export function setupI18n(app: App) {
  app.config.globalProperties.$t = t
}

export default {
  locale: localeRef,
}
