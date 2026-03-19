import { getExtensionStorageValue, removeExtensionStorageValue, setExtensionStorageValue, ss } from '@/utils/storage'

const LOCAL_NAME = 'appSetting'

export type Theme = 'light' | 'dark' | 'auto'

export type Language = 'zh-CN' | 'en-US'

export interface AppState {
  siderCollapsed: boolean
  theme: Theme
  language: Language
}

export function defaultSetting(): AppState {
  return { siderCollapsed: false, theme: 'auto', language: 'zh-CN' }
}

export function getLocalSetting(): AppState {
  const localSetting: AppState | undefined = ss.get(LOCAL_NAME)
  return { ...defaultSetting(), ...localSetting }
}

export async function getStoredSetting(): Promise<AppState> {
  const localSetting: AppState | undefined = await getExtensionStorageValue<AppState>(LOCAL_NAME)
  return { ...defaultSetting(), ...localSetting }
}

export function setLocalSetting(setting: AppState): void {
  ss.set(LOCAL_NAME, setting)
  void setExtensionStorageValue(LOCAL_NAME, setting)
}

export function removeLocalState() {
  ss.remove(LOCAL_NAME)
  void removeExtensionStorageValue(LOCAL_NAME)
}
