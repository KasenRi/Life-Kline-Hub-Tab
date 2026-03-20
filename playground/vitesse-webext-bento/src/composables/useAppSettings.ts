import { useStorage } from '@vueuse/core'

export interface AppSettings {
  themeColor: string
  backgroundBlur: number
  backgroundMaskOpacity: number
  showBackdropGlow: boolean
  openLinksInNewTab: boolean
  showSearch: boolean
  searchOpacity: number
  searchWidth: number
  searchRadius: number
  searchBlur: number
  showSearchSuggestions: boolean
  allowQuickSearch: boolean
  showClock: boolean
  showDate: boolean
  clockScale: number
  clockUse24Hour: boolean
  showScreenSaverQuote: boolean
  screenSaverOpacity: number
  enableShortcutHints: boolean
  showShortcutBadge: boolean
  iconColumn: number
  iconSize: number
  iconRadius: number
  iconGap: number
  showIconLabels: boolean
  iconLabelOpacity: number
  autoFetchFavicon: boolean
  backupAutoSave: boolean
  backupIncludeIcons: boolean
  backupIncludeWidgets: boolean
  backupRetentionDays: number
  contactEmail: string
  donateUrl: string
  privacyPolicyUrl: string
  changelogChannel: string
}

export function createDefaultAppSettings(): AppSettings {
  return {
    themeColor: '#7dd3fc',
    backgroundBlur: 28,
    backgroundMaskOpacity: 32,
    showBackdropGlow: true,
    openLinksInNewTab: true,
    showSearch: true,
    searchOpacity: 100,
    searchWidth: 56,
    searchRadius: 999,
    searchBlur: 18,
    showSearchSuggestions: true,
    allowQuickSearch: true,
    showClock: true,
    showDate: true,
    clockScale: 100,
    clockUse24Hour: false,
    showScreenSaverQuote: true,
    screenSaverOpacity: 75,
    enableShortcutHints: true,
    showShortcutBadge: true,
    iconColumn: 12,
    iconSize: 56,
    iconRadius: 50,
    iconGap: 18,
    showIconLabels: true,
    iconLabelOpacity: 90,
    autoFetchFavicon: true,
    backupAutoSave: true,
    backupIncludeIcons: true,
    backupIncludeWidgets: true,
    backupRetentionDays: 14,
    contactEmail: 'support@lifeklinehub.com',
    donateUrl: 'https://buymeacoffee.com/lifeklinehub',
    privacyPolicyUrl: 'https://lifeklinehub.com/privacy',
    changelogChannel: 'Stable',
  }
}

let settingsRef: ReturnType<typeof useStorage<AppSettings>> | null = null

export function useAppSettings() {
  if (!settingsRef)
    settingsRef = useStorage<AppSettings>('life-kline-hub.app-settings.v1', createDefaultAppSettings())

  return settingsRef
}
