<script setup lang="ts">
import { onClickOutside } from '@vueuse/core'
import { computed, ref } from 'vue'
import { useAppSettings, type AppSettings } from '~/composables/useAppSettings'

type SettingsTab =
  | 'general'
  | 'icons'
  | 'search'
  | 'clock'
  | 'quote'
  | 'shortcuts'
  | 'backup'
  | 'changelog'
  | 'contact'

type NumericSettingKey =
  | 'backgroundBlur'
  | 'backgroundMaskOpacity'
  | 'searchOpacity'
  | 'searchWidth'
  | 'searchRadius'
  | 'searchBlur'
  | 'clockScale'
  | 'screenSaverOpacity'
  | 'iconColumn'
  | 'iconSize'
  | 'iconRadius'
  | 'iconGap'
  | 'iconLabelOpacity'
  | 'backupRetentionDays'

type BooleanSettingKey =
  | 'showBackdropGlow'
  | 'openLinksInNewTab'
  | 'showSearch'
  | 'showSearchSuggestions'
  | 'allowQuickSearch'
  | 'showClock'
  | 'showDate'
  | 'clockUse24Hour'
  | 'showScreenSaverQuote'
  | 'enableShortcutHints'
  | 'showShortcutBadge'
  | 'showIconLabels'
  | 'autoFetchFavicon'
  | 'backupAutoSave'
  | 'backupIncludeIcons'
  | 'backupIncludeWidgets'

const emit = defineEmits<{
  close: []
}>()

const panelRef = ref<HTMLElement | null>(null)
const activeTab = ref<SettingsTab>('general')
const settings = useAppSettings()

const navItems: Array<{ id: SettingsTab, label: string, desc: string }> = [
  { id: 'general', label: '通用', desc: '桌面基础行为' },
  { id: 'icons', label: '图标', desc: '网格与视觉' },
  { id: 'search', label: '搜索框', desc: 'Omnibar 样式' },
  { id: 'clock', label: '时钟', desc: '时间显示' },
  { id: 'quote', label: '屏保一言', desc: '占位设置' },
  { id: 'shortcuts', label: '快捷键', desc: '键位提示' },
  { id: 'backup', label: '数据备份', desc: '导入导出' },
  { id: 'changelog', label: '版本日志', desc: '更新记录' },
  { id: 'contact', label: '联系我们', desc: '支持与反馈' },
]

const themePresets = ['#7dd3fc', '#f59e0b', '#34d399', '#f472b6', '#c084fc', '#ffffff']

const tabTitle = computed(() => {
  return navItems.find(item => item.id === activeTab.value)?.label ?? '设置'
})

const tabDescription = computed(() => {
  return navItems.find(item => item.id === activeTab.value)?.desc ?? ''
})

function close() {
  emit('close')
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function toggleSetting(key: BooleanSettingKey) {
  settings.value[key] = !settings.value[key] as AppSettings[BooleanSettingKey]
}

function setNumericSetting(key: NumericSettingKey, value: number, min: number, max: number) {
  settings.value[key] = clamp(Math.round(value), min, max) as AppSettings[NumericSettingKey]
}

function nudgeNumericSetting(key: NumericSettingKey, delta: number, min: number, max: number) {
  setNumericSetting(key, Number(settings.value[key]) + delta, min, max)
}

function handleRangeInput(key: NumericSettingKey, event: Event, min: number, max: number) {
  const target = event.target as HTMLInputElement | null
  if (!target)
    return

  setNumericSetting(key, Number(target.value), min, max)
}

function setThemeColor(color: string) {
  settings.value.themeColor = color
}

onClickOutside(panelRef, close)
</script>

<template>
  <div
    class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
    @click="close"
    @contextmenu.stop.prevent
  >
    <div
      ref="panelRef"
      class="flex h-[min(88vh,600px)] w-[min(92vw,800px)] overflow-hidden rounded-2xl border border-white/10 bg-[#1a1b26] shadow-2xl"
      data-floating-panel
      @click.stop
      @contextmenu.stop.prevent
    >
      <aside class="flex w-48 shrink-0 flex-col bg-[#151621] p-4">
        <div class="mb-5 rounded-2xl border border-white/6 bg-white/[0.03] p-4">
          <div class="flex items-center gap-3">
            <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400/80 to-cyan-200/70 text-lg font-semibold text-slate-950">
              LK
            </div>
            <div>
              <p class="text-sm font-medium text-white">
                Life Kline Hub
              </p>
              <p class="mt-1 text-xs text-slate-400">
                Desktop Settings
              </p>
            </div>
          </div>
        </div>

        <nav class="space-y-1.5">
          <button
            v-for="item in navItems"
            :key="item.id"
            type="button"
            class="w-full rounded-xl px-3 py-2.5 text-left transition-colors"
            :class="activeTab === item.id ? 'bg-blue-600/20 text-white shadow-[inset_0_0_0_1px_rgba(96,165,250,0.2)]' : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200'"
            @click="activeTab = item.id"
          >
            <div class="text-sm font-medium">
              {{ item.label }}
            </div>
            <div class="mt-1 text-[11px] text-inherit/70">
              {{ item.desc }}
            </div>
          </button>
        </nav>
      </aside>

      <section class="flex flex-1 flex-col overflow-hidden">
        <header class="flex items-start justify-between border-b border-white/6 px-8 pb-5 pt-7">
          <div>
            <p class="text-xs uppercase tracking-[0.28em] text-slate-500">
              Settings
            </p>
            <h2 class="mt-2 text-2xl font-semibold text-white">
              {{ tabTitle }}
            </h2>
            <p class="mt-1 text-sm text-slate-400">
              {{ tabDescription }}
            </p>
          </div>

          <button
            type="button"
            class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/6 bg-white/[0.04] text-slate-400 transition hover:bg-white/[0.08] hover:text-white"
            @click="close"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-4 w-4">
              <path d="M6 6l12 12M18 6 6 18" stroke-linecap="round" />
            </svg>
          </button>
        </header>

        <div class="flex-1 overflow-y-auto p-8 [scrollbar-color:rgba(148,163,184,0.45)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-white/10">
          <template v-if="activeTab === 'general'">
            <div class="space-y-4">
              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    主题色
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    控制全局高亮与面板偏色基调。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <input
                    v-model="settings.themeColor"
                    type="color"
                    class="h-11 w-11 cursor-pointer rounded-xl border border-white/10 bg-transparent p-1"
                  >
                  <div class="flex gap-2">
                    <button
                      v-for="color in themePresets"
                      :key="color"
                      type="button"
                      class="h-7 w-7 rounded-full border border-white/10 transition hover:scale-105"
                      :style="{ backgroundColor: color }"
                      @click="setThemeColor(color)"
                    />
                  </div>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    壁纸模糊
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    调整前景玻璃层与背景景深的融合强度。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('backgroundBlur', -2, 0, 60)">
                    -
                  </button>
                  <input
                    :value="settings.backgroundBlur"
                    type="range"
                    min="0"
                    max="60"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('backgroundBlur', $event, 0, 60)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('backgroundBlur', 2, 0, 60)">
                    +
                  </button>
                  <span class="w-8 text-right text-sm text-slate-300">{{ settings.backgroundBlur }}</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    蒙层透明度
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    控制壁纸暗部遮罩，不影响组件自身透明度。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('backgroundMaskOpacity', -5, 0, 100)">
                    -
                  </button>
                  <input
                    :value="settings.backgroundMaskOpacity"
                    type="range"
                    min="0"
                    max="100"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('backgroundMaskOpacity', $event, 0, 100)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('backgroundMaskOpacity', 5, 0, 100)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.backgroundMaskOpacity }}%</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    背景氛围光
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    开启后保留桌面角落的柔和环境光斑。
                  </p>
                </div>
                <button
                  type="button"
                  class="relative inline-flex h-7 w-12 items-center rounded-full transition"
                  :class="settings.showBackdropGlow ? 'bg-blue-500' : 'bg-white/10'"
                  @click="toggleSetting('showBackdropGlow')"
                >
                  <span
                    class="inline-block h-5 w-5 rounded-full bg-white transition"
                    :class="settings.showBackdropGlow ? 'translate-x-6' : 'translate-x-1'"
                  />
                </button>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    新标签打开链接
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    保持桌面停留，应用和书签通过新标签页打开。
                  </p>
                </div>
                <button
                  type="button"
                  class="relative inline-flex h-7 w-12 items-center rounded-full transition"
                  :class="settings.openLinksInNewTab ? 'bg-blue-500' : 'bg-white/10'"
                  @click="toggleSetting('openLinksInNewTab')"
                >
                  <span
                    class="inline-block h-5 w-5 rounded-full bg-white transition"
                    :class="settings.openLinksInNewTab ? 'translate-x-6' : 'translate-x-1'"
                  />
                </button>
              </div>
            </div>
          </template>

          <template v-else-if="activeTab === 'icons'">
            <div class="space-y-4">
              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    图标列数
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    控制桌面每页默认可容纳的图标密度。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconColumn', -1, 6, 16)">
                    -
                  </button>
                  <input
                    :value="settings.iconColumn"
                    type="range"
                    min="6"
                    max="16"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('iconColumn', $event, 6, 16)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconColumn', 1, 6, 16)">
                    +
                  </button>
                  <span class="w-8 text-right text-sm text-slate-300">{{ settings.iconColumn }}</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    图标尺寸
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    正方形图标本体的基础尺寸。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconSize', -2, 40, 88)">
                    -
                  </button>
                  <input
                    :value="settings.iconSize"
                    type="range"
                    min="40"
                    max="88"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('iconSize', $event, 40, 88)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconSize', 2, 40, 88)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.iconSize }}px</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    图标圆角
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    调节图标卡面的圆润程度。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconRadius', -5, 10, 50)">
                    -
                  </button>
                  <input
                    :value="settings.iconRadius"
                    type="range"
                    min="10"
                    max="50"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('iconRadius', $event, 10, 50)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconRadius', 5, 10, 50)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.iconRadius }}%</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    图标间距
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    控制桌面图标与 widget 之间的节奏感。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconGap', -1, 8, 32)">
                    -
                  </button>
                  <input
                    :value="settings.iconGap"
                    type="range"
                    min="8"
                    max="32"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('iconGap', $event, 8, 32)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconGap', 1, 8, 32)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.iconGap }}px</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    显示图标名称
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    保持桌面标签常驻，适合入口较多的布局。
                  </p>
                </div>
                <button
                  type="button"
                  class="relative inline-flex h-7 w-12 items-center rounded-full transition"
                  :class="settings.showIconLabels ? 'bg-blue-500' : 'bg-white/10'"
                  @click="toggleSetting('showIconLabels')"
                >
                  <span
                    class="inline-block h-5 w-5 rounded-full bg-white transition"
                    :class="settings.showIconLabels ? 'translate-x-6' : 'translate-x-1'"
                  />
                </button>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    名称透明度
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    让文字与壁纸对比保持在舒适范围。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconLabelOpacity', -5, 40, 100)">
                    -
                  </button>
                  <input
                    :value="settings.iconLabelOpacity"
                    type="range"
                    min="40"
                    max="100"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('iconLabelOpacity', $event, 40, 100)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('iconLabelOpacity', 5, 40, 100)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.iconLabelOpacity }}%</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    自动抓取网站图标
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    新增图标时根据 URL 自动补全 favicon。
                  </p>
                </div>
                <button
                  type="button"
                  class="relative inline-flex h-7 w-12 items-center rounded-full transition"
                  :class="settings.autoFetchFavicon ? 'bg-blue-500' : 'bg-white/10'"
                  @click="toggleSetting('autoFetchFavicon')"
                >
                  <span
                    class="inline-block h-5 w-5 rounded-full bg-white transition"
                    :class="settings.autoFetchFavicon ? 'translate-x-6' : 'translate-x-1'"
                  />
                </button>
              </div>
            </div>
          </template>

          <template v-else-if="activeTab === 'search'">
            <div class="space-y-4">
              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    显示搜索框
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    控制桌面顶部 Omnibar 是否显示。
                  </p>
                </div>
                <button
                  type="button"
                  class="relative inline-flex h-7 w-12 items-center rounded-full transition"
                  :class="settings.showSearch ? 'bg-blue-500' : 'bg-white/10'"
                  @click="toggleSetting('showSearch')"
                >
                  <span
                    class="inline-block h-5 w-5 rounded-full bg-white transition"
                    :class="settings.showSearch ? 'translate-x-6' : 'translate-x-1'"
                  />
                </button>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    搜索框透明度
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    调节胶囊框与壁纸叠加时的通透感。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('searchOpacity', -5, 20, 100)">
                    -
                  </button>
                  <input
                    :value="settings.searchOpacity"
                    type="range"
                    min="20"
                    max="100"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('searchOpacity', $event, 20, 100)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('searchOpacity', 5, 20, 100)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.searchOpacity }}%</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    搜索框宽度
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    以桌面内容宽度为基准调整搜索框比例。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('searchWidth', -2, 36, 80)">
                    -
                  </button>
                  <input
                    :value="settings.searchWidth"
                    type="range"
                    min="36"
                    max="80"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('searchWidth', $event, 36, 80)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('searchWidth', 2, 36, 80)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.searchWidth }}%</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    搜索框圆角
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    控制胶囊轮廓的圆润程度。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('searchRadius', -20, 24, 999)">
                    -
                  </button>
                  <input
                    :value="settings.searchRadius"
                    type="range"
                    min="24"
                    max="999"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('searchRadius', $event, 24, 999)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('searchRadius', 20, 24, 999)">
                    +
                  </button>
                  <span class="w-12 text-right text-sm text-slate-300">{{ settings.searchRadius }}</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    搜索框模糊
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    调节 Omnibar 的毛玻璃强度。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('searchBlur', -1, 0, 32)">
                    -
                  </button>
                  <input
                    :value="settings.searchBlur"
                    type="range"
                    min="0"
                    max="32"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('searchBlur', $event, 0, 32)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('searchBlur', 1, 0, 32)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.searchBlur }}px</span>
                </div>
              </div>

              <div class="grid gap-4 md:grid-cols-2">
                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      搜索建议
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      为联想结果预留设置位。
                    </p>
                  </div>
                  <button
                    type="button"
                    class="relative inline-flex h-7 w-12 items-center rounded-full transition"
                    :class="settings.showSearchSuggestions ? 'bg-blue-500' : 'bg-white/10'"
                    @click="toggleSetting('showSearchSuggestions')"
                  >
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.showSearchSuggestions ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>

                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      快捷搜索
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      保留多引擎切换能力的开关位。
                    </p>
                  </div>
                  <button
                    type="button"
                    class="relative inline-flex h-7 w-12 items-center rounded-full transition"
                    :class="settings.allowQuickSearch ? 'bg-blue-500' : 'bg-white/10'"
                    @click="toggleSetting('allowQuickSearch')"
                  >
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.allowQuickSearch ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="activeTab === 'clock'">
            <div class="space-y-4">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      显示时钟
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      保留右上角时间模块。
                    </p>
                  </div>
                  <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.showClock ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('showClock')">
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.showClock ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>

                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      显示日期
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      同步控制时钟下方的日期行。
                    </p>
                  </div>
                  <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.showDate ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('showDate')">
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.showDate ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    时钟缩放
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    调整右上角时间模块的视觉比重。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('clockScale', -5, 70, 130)">
                    -
                  </button>
                  <input
                    :value="settings.clockScale"
                    type="range"
                    min="70"
                    max="130"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('clockScale', $event, 70, 130)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('clockScale', 5, 70, 130)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.clockScale }}%</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    24 小时制
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    为时钟格式预留切换位。
                  </p>
                </div>
                <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.clockUse24Hour ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('clockUse24Hour')">
                  <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.clockUse24Hour ? 'translate-x-6' : 'translate-x-1'" />
                </button>
              </div>
            </div>
          </template>

          <template v-else-if="activeTab === 'quote'">
            <div class="space-y-4">
              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    屏保一言
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    预留后续接入 quote / 一言服务的开关位。
                  </p>
                </div>
                <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.showScreenSaverQuote ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('showScreenSaverQuote')">
                  <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.showScreenSaverQuote ? 'translate-x-6' : 'translate-x-1'" />
                </button>
              </div>

              <div class="flex items-center justify-between gap-6 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                <div>
                  <p class="font-medium text-white">
                    屏保透明度
                  </p>
                  <p class="mt-1 text-xs text-slate-400">
                    控制后续 quote 面板的存在感。
                  </p>
                </div>
                <div class="flex items-center gap-3">
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('screenSaverOpacity', -5, 20, 100)">
                    -
                  </button>
                  <input
                    :value="settings.screenSaverOpacity"
                    type="range"
                    min="20"
                    max="100"
                    class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                    @input="handleRangeInput('screenSaverOpacity', $event, 20, 100)"
                  >
                  <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('screenSaverOpacity', 5, 20, 100)">
                    +
                  </button>
                  <span class="w-10 text-right text-sm text-slate-300">{{ settings.screenSaverOpacity }}%</span>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="activeTab === 'shortcuts'">
            <div class="space-y-4">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      快捷键提示
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      为图标编辑态与搜索态显示提示标签。
                    </p>
                  </div>
                  <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.enableShortcutHints ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('enableShortcutHints')">
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.enableShortcutHints ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>

                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      搜索框快捷键标签
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      为 `Cmd / Ctrl + K` 保留可视化提示。
                    </p>
                  </div>
                  <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.showShortcutBadge ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('showShortcutBadge')">
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.showShortcutBadge ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>
              </div>

              <div class="rounded-2xl border border-dashed border-white/10 bg-white/[0.03] p-5 text-sm text-slate-400">
                当前为占位页，后续可在这里接入完整快捷键编辑器、冲突检测与导入导出。
              </div>
            </div>
          </template>

          <template v-else-if="activeTab === 'backup'">
            <div class="space-y-4">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      自动保存
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      在本地存储发生变化时自动更新快照。
                    </p>
                  </div>
                  <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.backupAutoSave ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('backupAutoSave')">
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.backupAutoSave ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>

                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      备份图标资源
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      导出时包含用户自定义图标和缩略图。
                    </p>
                  </div>
                  <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.backupIncludeIcons ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('backupIncludeIcons')">
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.backupIncludeIcons ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>

                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      备份小组件布局
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      同步导出 widget 尺寸与位置数据。
                    </p>
                  </div>
                  <button type="button" class="relative inline-flex h-7 w-12 items-center rounded-full transition" :class="settings.backupIncludeWidgets ? 'bg-blue-500' : 'bg-white/10'" @click="toggleSetting('backupIncludeWidgets')">
                    <span class="inline-block h-5 w-5 rounded-full bg-white transition" :class="settings.backupIncludeWidgets ? 'translate-x-6' : 'translate-x-1'" />
                  </button>
                </div>

                <div class="flex items-center justify-between gap-4 rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-4">
                  <div>
                    <p class="font-medium text-white">
                      保留天数
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      控制本地快照的最长保留周期。
                    </p>
                  </div>
                  <div class="flex items-center gap-3">
                    <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('backupRetentionDays', -1, 1, 90)">
                      -
                    </button>
                    <input
                      :value="settings.backupRetentionDays"
                      type="range"
                      min="1"
                      max="90"
                      class="h-2 w-40 cursor-pointer appearance-none rounded-full bg-white/10 accent-blue-500"
                      @input="handleRangeInput('backupRetentionDays', $event, 1, 90)"
                    >
                    <button type="button" class="h-9 w-9 rounded-xl bg-[#111522] text-lg text-slate-300 transition hover:bg-[#161b29]" @click="nudgeNumericSetting('backupRetentionDays', 1, 1, 90)">
                      +
                    </button>
                    <span class="w-10 text-right text-sm text-slate-300">{{ settings.backupRetentionDays }}d</span>
                  </div>
                </div>
              </div>

              <div class="grid gap-4 md:grid-cols-3">
                <button type="button" class="rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-5 text-left transition hover:bg-white/[0.08]">
                  <p class="font-medium text-white">
                    导出配置
                  </p>
                  <p class="mt-2 text-xs text-slate-400">
                    导出当前桌面布局、图标配置与偏好设置。
                  </p>
                </button>
                <button type="button" class="rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-5 text-left transition hover:bg-white/[0.08]">
                  <p class="font-medium text-white">
                    导入配置
                  </p>
                  <p class="mt-2 text-xs text-slate-400">
                    从本地 JSON 文件恢复桌面状态。
                  </p>
                </button>
                <button type="button" class="rounded-2xl border border-rose-400/20 bg-rose-400/[0.05] px-4 py-5 text-left transition hover:bg-rose-400/[0.1]">
                  <p class="font-medium text-rose-100">
                    恢复默认
                  </p>
                  <p class="mt-2 text-xs text-rose-200/70">
                    清空自定义布局并回到初始桌面模板。
                  </p>
                </button>
              </div>
            </div>
          </template>

          <template v-else-if="activeTab === 'changelog'">
            <div class="space-y-4">
              <div class="rounded-2xl border border-white/5 bg-white/[0.03] p-5">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-xs uppercase tracking-[0.28em] text-slate-500">
                      Channel
                    </p>
                    <p class="mt-2 text-lg font-medium text-white">
                      {{ settings.changelogChannel }}
                    </p>
                  </div>
                  <span class="rounded-full border border-white/8 bg-white/[0.04] px-3 py-1 text-xs text-slate-300">
                    v0.0.1
                  </span>
                </div>
              </div>

              <div class="space-y-3">
                <div class="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
                  <p class="font-medium text-white">
                    新标签页桌面布局
                  </p>
                  <p class="mt-2 text-sm text-slate-400">
                    持续迭代新标签页画布、图标、文件夹与 widget 的空间质感。
                  </p>
                </div>
                <div class="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
                  <p class="font-medium text-white">
                    全局设置面板
                  </p>
                  <p class="mt-2 text-sm text-slate-400">
                    当前版本新增统一设置面板与本地存储配置对象。
                  </p>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="activeTab === 'contact'">
            <div class="space-y-4">
              <div class="rounded-2xl border border-white/5 bg-white/[0.03] p-5">
                <p class="text-xs uppercase tracking-[0.28em] text-slate-500">
                  邮箱
                </p>
                <p class="mt-2 text-base font-medium text-white">
                  {{ settings.contactEmail }}
                </p>
                <p class="mt-2 text-sm text-slate-400">
                  需求反馈、Bug 报告与定制合作都可以通过这个邮箱联系。
                </p>
              </div>

              <div class="grid gap-4 md:grid-cols-2">
                <div class="rounded-2xl border border-white/5 bg-white/[0.03] p-5">
                  <p class="font-medium text-white">
                    打赏支持
                  </p>
                  <p class="mt-2 break-all text-sm text-slate-400">
                    {{ settings.donateUrl }}
                  </p>
                </div>

                <div class="rounded-2xl border border-white/5 bg-white/[0.03] p-5">
                  <p class="font-medium text-white">
                    隐私政策
                  </p>
                  <p class="mt-2 break-all text-sm text-slate-400">
                    {{ settings.privacyPolicyUrl }}
                  </p>
                </div>
              </div>

              <div class="rounded-2xl border border-white/5 bg-white/[0.03] p-5 text-sm text-slate-400">
                当前设置面板为 Local-First 存储，不会主动上传你的桌面数据。后续如增加云同步，会在这里明确说明同步范围与隐私边界。
              </div>
            </div>
          </template>

          <template v-else>
            <div class="rounded-2xl border border-dashed border-white/10 bg-white/[0.03] p-6 text-sm text-slate-400">
              这一页当前作为占位区域，后续会继续补全更细的配置项与交互。
            </div>
          </template>
        </div>
      </section>
    </div>
  </div>
</template>
