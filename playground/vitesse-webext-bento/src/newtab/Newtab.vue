<script setup lang="ts">
import Sortable, { type SortableEvent } from 'sortablejs'
import { onClickOutside, useStorage } from '@vueuse/core'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import SettingsModal from '~/components/SettingsModal.vue'
import { useAppSettings } from '~/composables/useAppSettings'

type ItemType = 'app' | 'folder' | 'widget'
type WidgetSize = '1x1' | '1x2' | '2x1' | '2x2' | '2x4'

interface BaseItem {
  id: string
  type: ItemType
  title: string
}

interface AppItem extends BaseItem {
  type: 'app'
  icon: string
  url: string
  desc?: string
  shortcut?: string
}

interface FolderItem extends BaseItem {
  type: 'folder'
  children: AppItem[]
}

interface WidgetItem extends BaseItem {
  type: 'widget'
  size: WidgetSize
  eyebrow: string
  value: string
  lines: string[]
  footer: string
  accentClass: string
  glowClass: string
}

type DesktopItem = AppItem | FolderItem | WidgetItem

interface DesktopPage {
  id: string
  title: string
  items: DesktopItem[]
}

interface SavedBookmark {
  id: string
  title: string
  url: string
  icon: string
}

interface AppLocation {
  pageIndex: number
  itemIndex: number
  childIndex: number | null
  app: AppItem
}

interface WidgetLocation {
  pageIndex: number
  itemIndex: number
  widget: WidgetItem
}

type IconModalTab = 'store' | 'custom' | 'widget'
type IconModalMode = 'add' | 'edit'

interface IconModalForm {
  title: string
  url: string
  desc: string
  icon: string
  shortcut: string
}

const scenicWallpaper = svgToDataUrl(`
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" fill="none">
    <defs>
      <linearGradient id="sky" x1="960" y1="36" x2="960" y2="718" gradientUnits="userSpaceOnUse">
        <stop stop-color="#DDF1FF" />
        <stop offset="0.28" stop-color="#9DD2FF" />
        <stop offset="0.6" stop-color="#5C8FD1" />
        <stop offset="1" stop-color="#1A3560" />
      </linearGradient>
      <linearGradient id="lake" x1="960" y1="612" x2="960" y2="1080" gradientUnits="userSpaceOnUse">
        <stop stop-color="#2A5C86" />
        <stop offset="0.45" stop-color="#0D203B" />
        <stop offset="1" stop-color="#050B16" />
      </linearGradient>
      <linearGradient id="sunGlow" x1="1240" y1="104" x2="1240" y2="352" gradientUnits="userSpaceOnUse">
        <stop stop-color="#FFF5D8" stop-opacity="0.98" />
        <stop offset="1" stop-color="#FFF1C7" stop-opacity="0" />
      </linearGradient>
      <linearGradient id="peakA" x1="0" y1="428" x2="0" y2="850" gradientUnits="userSpaceOnUse">
        <stop stop-color="#4E7AA6" />
        <stop offset="1" stop-color="#132845" />
      </linearGradient>
      <linearGradient id="peakB" x1="0" y1="504" x2="0" y2="932" gradientUnits="userSpaceOnUse">
        <stop stop-color="#2B517C" />
        <stop offset="1" stop-color="#0B172A" />
      </linearGradient>
      <linearGradient id="mist" x1="960" y1="456" x2="960" y2="696" gradientUnits="userSpaceOnUse">
        <stop stop-color="white" stop-opacity="0.28" />
        <stop offset="1" stop-color="white" stop-opacity="0" />
      </linearGradient>
      <filter id="blur" x="-240" y="-240" width="2400" height="1560" filterUnits="userSpaceOnUse">
        <feGaussianBlur stdDeviation="64" />
      </filter>
    </defs>

    <rect width="1920" height="1080" fill="url(#sky)" />
    <rect y="610" width="1920" height="470" fill="url(#lake)" />
    <circle cx="1290" cy="178" r="150" fill="url(#sunGlow)" />

    <g opacity="0.52" filter="url(#blur)">
      <circle cx="314" cy="196" r="160" fill="#FFFFFF" />
      <circle cx="1546" cy="246" r="210" fill="#FFE7B4" />
      <circle cx="1502" cy="778" r="240" fill="#9ED4FF" />
      <circle cx="760" cy="820" r="220" fill="#B5DDFF" />
    </g>

    <path d="M0 664L164 592L310 532L440 552L588 462L732 548L896 406L1078 556L1248 414L1382 516L1554 430L1740 550L1920 502V1080H0V664Z" fill="url(#peakA)" />
    <path d="M0 770L180 656L342 700L524 586L664 672L842 576L1004 686L1176 622L1360 726L1546 640L1714 720L1920 642V1080H0V770Z" fill="url(#peakB)" />
    <path d="M0 612C164 594 316 594 456 598C670 604 916 620 1180 616C1464 612 1710 566 1920 564V690H0V612Z" fill="url(#mist)" />
    <path d="M0 748C170 730 338 736 502 740C730 746 958 772 1186 762C1454 750 1714 704 1920 688V1080H0V748Z" fill="white" fill-opacity="0.08" />
  </svg>
`)

function svgToDataUrl(svg: string) {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

function makeIcon(label: string, from: string, to: string) {
  return svgToDataUrl(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" fill="none">
      <defs>
        <linearGradient id="g" x1="14" y1="14" x2="114" y2="114" gradientUnits="userSpaceOnUse">
          <stop stop-color="${from}" />
          <stop offset="1" stop-color="${to}" />
        </linearGradient>
      </defs>
      <rect width="128" height="128" rx="30" fill="url(#g)" />
      <circle cx="101" cy="26" r="24" fill="rgba(255,255,255,0.22)" />
      <circle cx="28" cy="108" r="30" fill="rgba(255,255,255,0.12)" />
      <text
        x="64"
        y="70"
        text-anchor="middle"
        font-size="42"
        font-weight="700"
        font-family="Inter, SF Pro Display, system-ui, sans-serif"
        fill="white"
      >
        ${label}
      </text>
    </svg>
  `)
}

function createApp(id: string, title: string, url: string, label: string, from: string, to: string): AppItem {
  return {
    id,
    type: 'app',
    title,
    url,
    icon: makeIcon(label, from, to),
    desc: '',
    shortcut: '',
  }
}

function createWidget(
  id: string,
  title: string,
  size: WidgetSize,
  eyebrow: string,
  value: string,
  lines: string[],
  footer: string,
  accentClass: string,
  glowClass: string,
): WidgetItem {
  return {
    id,
    type: 'widget',
    title,
    size,
    eyebrow,
    value,
    lines,
    footer,
    accentClass,
    glowClass,
  }
}

function createMockPages(): DesktopPage[] {
  const tradingView = createApp('app-tradingview', 'TradingView', 'https://www.tradingview.com', 'TV', '#2563EB', '#0EA5E9')
  const notion = createApp('app-notion', 'Notion', 'https://www.notion.so', 'N', '#111827', '#4B5563')
  const linear = createApp('app-linear', 'Linear', 'https://linear.app', 'L', '#312E81', '#7C3AED')
  const figma = createApp('app-figma', 'Figma', 'https://www.figma.com', 'F', '#F97316', '#EC4899')
  const gmail = createApp('app-gmail', 'Gmail', 'https://mail.google.com', 'M', '#2563EB', '#EF4444')
  const docs = createApp('app-docs', 'Docs', 'https://docs.google.com', 'D', '#2563EB', '#38BDF8')
  const calendar = createApp('app-calendar', 'Calendar', 'https://calendar.google.com', '31', '#F97316', '#FB7185')
  const bilibili = createApp('app-bilibili', 'Bilibili', 'https://www.bilibili.com', 'B', '#0EA5E9', '#38BDF8')
  const youtube = createApp('app-youtube', 'YouTube', 'https://www.youtube.com', 'YT', '#DC2626', '#FB7185')
  const github = createApp('app-github', 'GitHub', 'https://github.com', 'GH', '#0F172A', '#334155')
  const fastapi = createApp('app-fastapi', 'FastAPI', 'https://fastapi.tiangolo.com', 'FA', '#0F766E', '#14B8A6')
  const tailwind = createApp('app-tailwind', 'Tailwind', 'https://tailwindcss.com', 'TW', '#0284C7', '#22D3EE')
  const vue = createApp('app-vue', 'Vue 3', 'https://vuejs.org', 'V', '#059669', '#34D399')
  const vercel = createApp('app-vercel', 'Vercel', 'https://vercel.com', 'V', '#111827', '#4B5563')
  const supabase = createApp('app-supabase', 'Supabase', 'https://supabase.com', 'S', '#059669', '#86EFAC')
  const x = createApp('app-x', 'X', 'https://x.com', 'X', '#0F172A', '#475569')
  const spotify = createApp('app-spotify', 'Spotify', 'https://open.spotify.com', 'S', '#166534', '#22C55E')
  const reddit = createApp('app-reddit', 'Reddit', 'https://www.reddit.com', 'R', '#EA580C', '#F97316')
  const medium = createApp('app-medium', 'Medium', 'https://medium.com', 'M', '#111827', '#15803D')
  const appleMusic = createApp('app-apple-music', 'Apple Music', 'https://music.apple.com', 'AM', '#BE185D', '#F472B6')
  const claude = createApp('app-claude', 'Claude', 'https://claude.ai', 'C', '#9A3412', '#FDBA74')
  const openai = createApp('app-openai', 'OpenAI', 'https://platform.openai.com', 'AI', '#064E3B', '#10B981')

  return [
    {
      id: 'page-home',
      title: '主屏',
      items: [
        createWidget(
          'widget-weather',
          '天气',
          '2x2',
          'Hangzhou',
          '26°',
          ['多云转晴，体感 28°', '湿度 58%，西南风 3 级', '空气质量优，适合外出'],
          '下午 4:20 日落，夜间温度 18°',
          'bg-gradient-to-br from-sky-300/25 via-white/10 to-white/0',
          'bg-sky-300/25',
        ),
        tradingView,
        notion,
        {
          id: 'folder-dev',
          type: 'folder',
          title: '开发',
          children: [github, fastapi, tailwind, vue, vercel, supabase],
        },
        figma,
        createWidget(
          'widget-todo',
          '今日推进',
          '2x4',
          'Local First',
          '3 / 5',
          ['重写 Newtab DOM 结构', '接入 SortableJS 排序预留', '整理 Folder / Widget 交互', '补齐离线存储 mock 数据', '回归视觉细节与响应式'],
          '优先保证 0 毫秒启动，再考虑联网能力',
          'bg-gradient-to-br from-emerald-300/18 via-white/10 to-white/0',
          'bg-emerald-300/20',
        ),
        linear,
        docs,
        calendar,
        gmail,
        {
          id: 'folder-media',
          type: 'folder',
          title: '内容',
          children: [bilibili, youtube, x, reddit, medium, spotify],
        },
        appleMusic,
        claude,
        openai,
      ],
    },
    {
      id: 'page-focus',
      title: '效率',
      items: [
        createWidget(
          'widget-market',
          '市场脉搏',
          '2x2',
          'Life Kline',
          'BTC 84.2K',
          ['ETH 4.8K，SOL 205', '今日关注：量价与情绪背离', '晚间复盘窗口 21:30'],
          '这里先保留静态 mock，后续接 Python API',
          'bg-gradient-to-br from-amber-300/20 via-white/10 to-white/0',
          'bg-amber-300/25',
        ),
        tradingView,
        notion,
        linear,
        figma,
        createWidget(
          'widget-rhythm',
          '专注节奏',
          '2x4',
          'Deep Work',
          '95 min',
          ['09:00 - 10:35 设计推敲', '11:00 - 12:00 接口对齐', '14:00 - 15:30 视觉 polish', '16:00 - 17:00 测试与清理'],
          '把高认知任务放在前两个专注块',
          'bg-gradient-to-br from-violet-300/22 via-white/10 to-white/0',
          'bg-violet-300/25',
        ),
        github,
        vue,
        tailwind,
        vercel,
        supabase,
        {
          id: 'folder-ai',
          type: 'folder',
          title: 'AI',
          children: [openai, claude, github, notion, docs, gmail],
        },
      ],
    },
  ]
}

function reorder<T>(items: T[], oldIndex: number, newIndex: number) {
  const next = [...items]
  const [moved] = next.splice(oldIndex, 1)
  if (moved === undefined)
    return next

  next.splice(newIndex, 0, moved)
  return next
}

function isAppItem(item: DesktopItem): item is AppItem {
  return item.type === 'app'
}

function isFolderItem(item: DesktopItem): item is FolderItem {
  return item.type === 'folder'
}

const pages = useStorage<DesktopPage[]>('life-kline-hub.pages.v1', createMockPages())
const activePageId = useStorage<string>('life-kline-hub.active-page.v1', 'page-home')
const omnibar = useStorage<string>('life-kline-hub.omnibar.v1', '')
const savedBookmarks = useStorage<SavedBookmark[]>('life-kline-hub.bookmarks.v1', [])
const appSettings = useAppSettings()

const activeFolderId = ref<string | null>(null)
const clock = ref('')
const dateLabel = ref('')
const isSettingsOpen = ref(false)
const contextMenu = ref<{ show: boolean, x: number, y: number, targetId: string | null }>({
  show: false,
  x: 0,
  y: 0,
  targetId: null,
})
const contextMenuTargetType = ref<ItemType | null>(null)
const desktopMenu = ref({
  show: false,
  x: 0,
  y: 0,
})
const iconModal = ref<{
  show: boolean
  mode: IconModalMode
  form: IconModalForm
}>({
  show: false,
  mode: 'add',
  form: {
    title: '',
    url: '',
    desc: '',
    icon: '',
    shortcut: '',
  },
})
const iconModalTab = ref<IconModalTab>('custom')
const omnibarRef = ref<HTMLInputElement | null>(null)
const gridRef = ref<HTMLElement | null>(null)
const contextMenuRef = ref<HTMLElement | null>(null)
const desktopMenuRef = ref<HTMLElement | null>(null)
const iconModalPanelRef = ref<HTMLElement | null>(null)
const iconUploadInputRef = ref<HTMLInputElement | null>(null)
const iconModalTargetId = ref<string | null>(null)
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1440)

let sortable: Sortable | null = null
let clockTimer: number | null = null

const activePage = computed(() => pages.value.find(page => page.id === activePageId.value) ?? pages.value[0] ?? null)
const keyword = computed(() => omnibar.value.trim().toLowerCase())
const totalItems = computed(() => pages.value.reduce((sum, page) => sum + page.items.length, 0))

const visibleItems = computed<DesktopItem[]>(() => {
  const page = activePage.value
  if (!page)
    return []

  if (!keyword.value)
    return page.items

  return page.items.filter((item) => {
    if (isAppItem(item))
      return item.title.toLowerCase().includes(keyword.value)
        || item.url.toLowerCase().includes(keyword.value)
        || (item.desc ?? '').toLowerCase().includes(keyword.value)
        || (item.shortcut ?? '').toLowerCase().includes(keyword.value)

    if (isFolderItem(item))
      return item.title.toLowerCase().includes(keyword.value) || item.children.some(child =>
        child.title.toLowerCase().includes(keyword.value)
        || child.url.toLowerCase().includes(keyword.value)
        || (child.desc ?? '').toLowerCase().includes(keyword.value)
        || (child.shortcut ?? '').toLowerCase().includes(keyword.value))

    return item.title.toLowerCase().includes(keyword.value)
      || item.eyebrow.toLowerCase().includes(keyword.value)
      || item.value.toLowerCase().includes(keyword.value)
      || item.footer.toLowerCase().includes(keyword.value)
      || item.lines.some(line => line.toLowerCase().includes(keyword.value))
  })
})

const activeFolder = computed<FolderItem | null>(() => {
  const page = activePage.value
  if (!page || !activeFolderId.value)
    return null

  const folder = page.items.find(item => item.id === activeFolderId.value)
  return folder && isFolderItem(folder) ? folder : null
})
const contextTargetApp = computed(() => findAppLocation(contextMenu.value.targetId)?.app ?? null)
const contextTargetWidget = computed(() => findWidgetLocation(contextMenu.value.targetId)?.widget ?? null)
const iconPreviewSrc = computed(() => {
  const providedIcon = iconModal.value.form.icon.trim()
  if (providedIcon)
    return providedIcon

  return makeSolidIcon(iconModal.value.form.title || 'App')
})
const shortcutBadgeLabel = computed(() => (/Mac|iPhone|iPad|iPod/.test(globalThis.navigator?.platform ?? '') ? '⌘K' : 'Ctrl K'))
const quoteCardStyle = computed(() => ({
  opacity: appSettings.value.screenSaverOpacity / 100,
  borderColor: withAlpha(appSettings.value.themeColor, 0.16),
  boxShadow: `0 18px 60px ${withAlpha('#020617', 0.28)}`,
}))
const quoteText = computed(() => {
  return `Local First means the desktop is ready before the network is.`
})
const quoteMeta = computed(() => `Life Kline Hub · ${activePage.value?.title ?? 'Workspace'}`)
const themeTextStyle = computed(() => ({
  color: withAlpha(appSettings.value.themeColor, 0.92),
}))
const themeGlowStyle = computed(() => ({
  background: `radial-gradient(circle at center, ${withAlpha(appSettings.value.themeColor, 0.3)} 0%, transparent 72%)`,
}))
const wallpaperBlurStyle = computed(() => ({
  backdropFilter: `blur(${appSettings.value.backgroundBlur}px)`,
}))
const backgroundMaskStyle = computed(() => ({
  background: `linear-gradient(to bottom, ${withAlpha('#020617', appSettings.value.backgroundMaskOpacity / 650)}, ${withAlpha('#020617', appSettings.value.backgroundMaskOpacity / 350)}, ${withAlpha('#020617', appSettings.value.backgroundMaskOpacity / 180)})`,
}))
const backgroundFloorStyle = computed(() => ({
  background: `linear-gradient(to top, ${withAlpha('#020617', appSettings.value.backgroundMaskOpacity / 160)}, transparent)`,
}))
const clockBlockStyle = computed(() => ({
  transform: `scale(${appSettings.value.clockScale / 100})`,
  transformOrigin: 'top right',
}))
const effectiveGridColumns = computed(() => {
  const preferred = appSettings.value.iconColumn
  if (viewportWidth.value < 640)
    return Math.min(preferred, 4)
  if (viewportWidth.value < 1024)
    return Math.min(preferred, 6)
  if (viewportWidth.value < 1280)
    return Math.min(preferred, 8)
  return preferred
})
const gridStyle = computed(() => {
  const rowSize = Math.max(98, Math.round(appSettings.value.iconSize * 1.76))
  return {
    gridTemplateColumns: `repeat(${effectiveGridColumns.value}, minmax(0, 1fr))`,
    gridAutoRows: `${rowSize}px`,
    columnGap: `${appSettings.value.iconGap}px`,
    rowGap: `${Math.max(24, appSettings.value.iconGap + 12)}px`,
  }
})
const iconPixelSize = computed(() => `${appSettings.value.iconSize}px`)
const iconRadiusPx = computed(() => `${Math.round((appSettings.value.iconSize / 2) * (appSettings.value.iconRadius / 100))}px`)
const iconButtonStyle = computed(() => ({
  maxWidth: `${appSettings.value.iconSize + 36}px`,
}))
const iconSurfaceStyle = computed(() => ({
  width: iconPixelSize.value,
  height: iconPixelSize.value,
}))
const iconImageStyle = computed(() => ({
  borderRadius: iconRadiusPx.value,
}))
const iconBackdropStyle = computed(() => ({
  borderRadius: iconRadiusPx.value,
  borderColor: withAlpha(appSettings.value.themeColor, 0.12),
  boxShadow: `0 10px 40px ${withAlpha('#020617', 0.18)}`,
}))
const folderThumbRadiusStyle = computed(() => ({
  borderRadius: `${Math.max(6, Math.round(appSettings.value.iconSize * 0.14))}px`,
}))
const searchWrapStyle = computed(() => ({
  maxWidth: `${clamp(Math.round(viewportWidth.value * (appSettings.value.searchWidth / 100)), 420, 960)}px`,
}))
const searchInputStyle = computed(() => ({
  borderRadius: `${appSettings.value.searchRadius}px`,
  backdropFilter: `blur(${appSettings.value.searchBlur}px)`,
  boxShadow: `0 20px 80px ${withAlpha('#020617', 0.35)}, 0 0 0 1px ${withAlpha(appSettings.value.themeColor, 0.08)}`,
}))
const searchBadgeStyle = computed(() => ({
  borderColor: withAlpha(appSettings.value.themeColor, 0.16),
  backgroundColor: withAlpha('#0f172a', 0.3),
  color: withAlpha(appSettings.value.themeColor, 0.92),
}))
const activePageDotStyle = computed(() => ({
  backgroundColor: withAlpha(appSettings.value.themeColor, 0.3),
  borderColor: withAlpha(appSettings.value.themeColor, 0.24),
  boxShadow: `0 10px 30px ${withAlpha(appSettings.value.themeColor, 0.22)}`,
}))
const inactivePageDotStyle = computed(() => ({
  backgroundColor: withAlpha(appSettings.value.themeColor, 0.24),
}))
const settingsButtonStyle = computed(() => ({
  borderColor: withAlpha(appSettings.value.themeColor, 0.14),
  boxShadow: `0 18px 48px ${withAlpha(appSettings.value.themeColor, 0.14)}`,
}))
const searchSuggestions = computed(() => {
  if (!appSettings.value.showSearchSuggestions || !keyword.value)
    return []

  return visibleItems.value
    .flatMap((item) => {
      if (isAppItem(item))
        return [{ id: item.id, title: item.title, kind: 'app' as const }]
      if (isFolderItem(item))
        return item.children.map(child => ({ id: child.id, title: child.title, kind: 'folder-app' as const }))
      return [{ id: item.id, title: item.title, kind: 'widget' as const }]
    })
    .slice(0, 4)
})

function hexToRgb(hex: string) {
  const normalized = hex.replace('#', '')
  const value = normalized.length === 3
    ? normalized.split('').map(char => char + char).join('')
    : normalized

  if (!/^[0-9a-f]{6}$/i.test(value))
    return { r: 125, g: 211, b: 252 }

  const int = Number.parseInt(value, 16)
  return {
    r: (int >> 16) & 255,
    g: (int >> 8) & 255,
    b: int & 255,
  }
}

function withAlpha(hex: string, alpha: number) {
  const { r, g, b } = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${Math.max(0, Math.min(1, alpha))})`
}

function widgetSpanClass(size: WidgetSize) {
  if (size === '1x2')
    return 'row-span-2'
  if (size === '2x1')
    return 'col-span-2'
  if (size === '2x2')
    return 'col-span-2 row-span-2'
  if (size === '2x4')
    return 'col-span-4 row-span-2'
  return ''
}

function updateClock() {
  const now = new Date()
  clock.value = now.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    hour12: !appSettings.value.clockUse24Hour,
  })
  dateLabel.value = now.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    weekday: 'short',
  })
}

function updateViewportMetrics() {
  viewportWidth.value = window.innerWidth
}

function setActivePage(pageId: string) {
  activePageId.value = pageId
}

function closeFolder() {
  activeFolderId.value = null
}

function closeContextMenu() {
  contextMenu.value.show = false
  contextMenu.value.targetId = null
  contextMenuTargetType.value = null
}

function closeDesktopMenu() {
  desktopMenu.value.show = false
}

function createEmptyIconForm(): IconModalForm {
  return {
    title: '',
    url: '',
    desc: '',
    icon: '',
    shortcut: '',
  }
}

function closeIconModal() {
  iconModal.value.show = false
  iconModal.value.mode = 'add'
  iconModal.value.form = createEmptyIconForm()
  iconModalTab.value = 'custom'
  iconModalTargetId.value = null
}

function openUrl(url: string) {
  if (appSettings.value.openLinksInNewTab) {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }

  window.location.assign(url)
}

function openApp(app: AppItem) {
  closeContextMenu()
  closeDesktopMenu()
  closeFolder()
  openUrl(app.url)
}

function openItem(item: DesktopItem) {
  closeContextMenu()
  closeDesktopMenu()

  if (isAppItem(item)) {
    openApp(item)
    return
  }

  if (isFolderItem(item))
    activeFolderId.value = item.id
}

function openItemInNewTab(app: AppItem) {
  closeContextMenu()
  window.open(app.url, '_blank', 'noopener,noreferrer')
}

function buildCopyId(sourceId: string) {
  return `${sourceId}-copy-${Date.now().toString(36)}`
}

function buildAppId() {
  return `app-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
}

function getTitleLabel(title: string) {
  const normalized = title.trim()
  if (!normalized)
    return 'A'

  const compact = normalized.replace(/\s+/g, '')
  return compact.slice(0, 2).toUpperCase()
}

function hashString(input: string) {
  return [...input].reduce((hash, char) => ((hash << 5) - hash + char.charCodeAt(0)) | 0, 0)
}

function makeSolidIcon(title: string) {
  const palette = [
    ['#2563EB', '#60A5FA'],
    ['#0F766E', '#2DD4BF'],
    ['#7C3AED', '#A78BFA'],
    ['#BE185D', '#FB7185'],
    ['#EA580C', '#FDBA74'],
    ['#166534', '#4ADE80'],
    ['#0F172A', '#475569'],
  ] as const
  const index = Math.abs(hashString(title || 'app')) % palette.length
  const [from, to] = palette[index]
  return makeIcon(getTitleLabel(title), from, to)
}

function findAppLocation(targetId: string | null): AppLocation | null {
  const page = activePage.value
  if (!page || !targetId)
    return null

  const pageIndex = pages.value.findIndex(item => item.id === page.id)
  if (pageIndex < 0)
    return null

  for (const [itemIndex, item] of page.items.entries()) {
    if (isAppItem(item) && item.id === targetId) {
      return {
        pageIndex,
        itemIndex,
        childIndex: null,
        app: item,
      }
    }

    if (isFolderItem(item)) {
      const childIndex = item.children.findIndex(child => child.id === targetId)
      if (childIndex >= 0) {
        return {
          pageIndex,
          itemIndex,
          childIndex,
          app: item.children[childIndex],
        }
      }
    }
  }

  return null
}

function findWidgetLocation(targetId: string | null): WidgetLocation | null {
  const page = activePage.value
  if (!page || !targetId)
    return null

  const pageIndex = pages.value.findIndex(item => item.id === page.id)
  if (pageIndex < 0)
    return null

  const itemIndex = page.items.findIndex(item => item.id === targetId && item.type === 'widget')
  if (itemIndex < 0)
    return null

  const widget = page.items[itemIndex]
  if (!widget || widget.type !== 'widget')
    return null

  return {
    pageIndex,
    itemIndex,
    widget,
  }
}

function cloneContextTarget() {
  const widgetLocation = findWidgetLocation(contextMenu.value.targetId)
  if (widgetLocation) {
    const page = activePage.value
    if (!page)
      return

    const duplicate: WidgetItem = {
      ...widgetLocation.widget,
      id: buildCopyId(widgetLocation.widget.id),
      title: `${widgetLocation.widget.title} 副本`,
    }

    const nextPages = [...pages.value]
    const nextPage: DesktopPage = {
      ...page,
      items: [...page.items],
    }
    nextPage.items.splice(widgetLocation.itemIndex + 1, 0, duplicate)
    nextPages[widgetLocation.pageIndex] = nextPage
    pages.value = nextPages
    closeContextMenu()
    return
  }

  const location = findAppLocation(contextMenu.value.targetId)
  if (!location)
    return

  const page = activePage.value
  if (!page)
    return

  const duplicate: AppItem = {
    ...location.app,
    id: buildCopyId(location.app.id),
    title: `${location.app.title} 副本`,
  }

  const nextPages = [...pages.value]
  const nextPage: DesktopPage = {
    ...page,
    items: [...page.items],
  }

  if (location.childIndex == null) {
    nextPage.items.splice(location.itemIndex + 1, 0, duplicate)
  }
  else {
    const folder = nextPage.items[location.itemIndex]
    if (!folder || !isFolderItem(folder))
      return

    const nextChildren = [...folder.children]
    nextChildren.splice(location.childIndex + 1, 0, duplicate)
    nextPage.items[location.itemIndex] = {
      ...folder,
      children: nextChildren,
    }
  }

  nextPages[location.pageIndex] = nextPage
  pages.value = nextPages
  closeContextMenu()
}

function deleteContextTarget() {
  const widgetLocation = findWidgetLocation(contextMenu.value.targetId)
  if (widgetLocation) {
    const page = activePage.value
    if (!page)
      return

    const nextPages = [...pages.value]
    const nextPage: DesktopPage = {
      ...page,
      items: [...page.items],
    }
    nextPage.items.splice(widgetLocation.itemIndex, 1)
    nextPages[widgetLocation.pageIndex] = nextPage
    pages.value = nextPages
    closeContextMenu()
    return
  }

  const location = findAppLocation(contextMenu.value.targetId)
  if (!location)
    return

  const page = activePage.value
  if (!page)
    return

  const nextPages = [...pages.value]
  const nextPage: DesktopPage = {
    ...page,
    items: [...page.items],
  }

  if (location.childIndex == null) {
    nextPage.items.splice(location.itemIndex, 1)
  }
  else {
    const folder = nextPage.items[location.itemIndex]
    if (!folder || !isFolderItem(folder))
      return

    const nextChildren = [...folder.children]
    nextChildren.splice(location.childIndex, 1)
    nextPage.items[location.itemIndex] = {
      ...folder,
      children: nextChildren,
    }

    if (activeFolderId.value === folder.id && nextChildren.length === 0)
      closeFolder()
  }

  nextPages[location.pageIndex] = nextPage
  pages.value = nextPages
  closeContextMenu()
}

function importContextTargetToBookmarks() {
  const app = contextTargetApp.value
  if (!app)
    return

  if (!savedBookmarks.value.some(bookmark => bookmark.url === app.url)) {
    savedBookmarks.value = [
      ...savedBookmarks.value,
      {
        id: `bookmark-${app.id}`,
        title: app.title,
        url: app.url,
        icon: app.icon,
      },
    ]
  }

  const browserApi = globalThis.browser as { runtime?: { id?: string }, bookmarks?: { create: (input: { title: string, url: string }) => Promise<unknown> } } | undefined
  const chromeApi = globalThis.chrome as { runtime?: { id?: string }, bookmarks?: { create: (input: { title: string, url: string }, callback?: () => void) => void } } | undefined

  try {
    if (browserApi?.runtime?.id && browserApi.bookmarks?.create)
      void browserApi.bookmarks.create({ title: app.title, url: app.url })
    else if (chromeApi?.runtime?.id && chromeApi.bookmarks?.create)
      chromeApi.bookmarks.create({ title: app.title, url: app.url })
  }
  catch (error) {
    console.warn('Failed to import bookmark via extension API.', error)
  }

  closeContextMenu()
}

function markContextAction(label: string) {
  const target = contextTargetApp.value ?? contextTargetWidget.value
  const suffix = target ? `: ${target.title}` : ''
  console.info(`[Life Kline Hub] ${label}${suffix}`)
  closeContextMenu()
  closeDesktopMenu()
}

function openContextTarget() {
  const widget = contextTargetWidget.value
  if (widget) {
    console.info(`[Life Kline Hub] open widget: ${widget.title}`)
    closeContextMenu()
    return
  }

  const app = contextTargetApp.value
  if (app)
    openItemInNewTab(app)
}

function updateAppByLocation(location: AppLocation, updater: (app: AppItem) => AppItem) {
  const page = activePage.value
  if (!page)
    return

  const nextPages = [...pages.value]
  const nextPage: DesktopPage = {
    ...page,
    items: [...page.items],
  }

  if (location.childIndex == null) {
    const current = nextPage.items[location.itemIndex]
    if (!current || !isAppItem(current))
      return

    nextPage.items[location.itemIndex] = updater(current)
  }
  else {
    const folder = nextPage.items[location.itemIndex]
    if (!folder || !isFolderItem(folder))
      return

    const nextChildren = [...folder.children]
    nextChildren[location.childIndex] = updater(nextChildren[location.childIndex])
    nextPage.items[location.itemIndex] = {
      ...folder,
      children: nextChildren,
    }
  }

  nextPages[location.pageIndex] = nextPage
  pages.value = nextPages
}

function normalizeAppForm(form: IconModalForm): AppItem {
  const title = form.title.trim() || '新图标'
  const icon = form.icon.trim() || makeSolidIcon(title)
  const url = form.url.trim() || 'https://example.com'

  return {
    id: buildAppId(),
    type: 'app',
    title,
    url,
    icon,
    desc: form.desc.trim(),
    shortcut: form.shortcut.trim(),
  }
}

function openAddIconModal() {
  closeContextMenu()
  closeDesktopMenu()
  iconModal.value = {
    show: true,
    mode: 'add',
    form: createEmptyIconForm(),
  }
  iconModalTab.value = 'custom'
  iconModalTargetId.value = null
}

function openWidgetTabModal() {
  closeContextMenu()
  closeDesktopMenu()
  iconModal.value.show = true
  iconModal.value.mode = 'add'
  iconModal.value.form = createEmptyIconForm()
  iconModalTab.value = 'widget'
  iconModalTargetId.value = null
}

function openEditIconModal() {
  const app = contextTargetApp.value
  if (!app)
    return

  closeContextMenu()
  closeDesktopMenu()
  iconModal.value = {
    show: true,
    mode: 'edit',
    form: {
      title: app.title,
      url: app.url,
      desc: app.desc ?? '',
      icon: app.icon,
      shortcut: app.shortcut ?? '',
    },
  }
  iconModalTab.value = 'custom'
  iconModalTargetId.value = app.id
}

function saveIconModal() {
  if (iconModalTab.value !== 'custom')
    return

  const preparedApp = normalizeAppForm(iconModal.value.form)
  const page = activePage.value
  if (!page)
    return

  if (iconModal.value.mode === 'edit') {
    const location = findAppLocation(iconModalTargetId.value)
    if (!location)
      return

    updateAppByLocation(location, app => ({
      ...app,
      title: preparedApp.title,
      url: preparedApp.url,
      icon: preparedApp.icon,
      desc: preparedApp.desc,
      shortcut: preparedApp.shortcut,
    }))
  }
  else {
    const pageIndex = pages.value.findIndex(item => item.id === page.id)
    if (pageIndex < 0)
      return

    const nextPages = [...pages.value]
    nextPages[pageIndex] = {
      ...page,
      items: [...page.items, preparedApp],
    }
    pages.value = nextPages
  }

  closeIconModal()
}

function buildNormalizedUrl(raw: string) {
  const input = raw.trim()
  if (!input)
    return ''

  return /^https?:\/\//i.test(input) ? input : `https://${input}`
}

function fetchIconForModal() {
  const raw = iconModal.value.form.url.trim()
  if (!raw)
    return

  const target = buildNormalizedUrl(raw)
  iconModal.value.form.icon = `https://www.google.com/s2/favicons?sz=128&domain_url=${encodeURIComponent(target)}`
}

function autoFetchIcon() {
  if (!appSettings.value.autoFetchFavicon || iconModal.value.form.icon.trim())
    return

  const target = buildNormalizedUrl(iconModal.value.form.url)
  if (!target)
    return

  try {
    const parsed = new URL(target)
    if (!parsed.hostname)
      return
  }
  catch {
    return
  }

  fetchIconForModal()
}

function useSolidIconForModal() {
  iconModal.value.form.icon = makeSolidIcon(iconModal.value.form.title || 'App')
}

function triggerIconUpload() {
  iconUploadInputRef.value?.click()
}

function handleIconUpload(event: Event) {
  const input = event.target as HTMLInputElement | null
  const file = input?.files?.[0]
  if (!file)
    return

  const reader = new FileReader()
  reader.onload = () => {
    if (typeof reader.result === 'string')
      iconModal.value.form.icon = reader.result
  }
  reader.readAsDataURL(file)

  if (input)
    input.value = ''
}

async function positionMenu(panelRef: { value: HTMLElement | null }, position: { x: number, y: number }, setPosition: (coords: { x: number, y: number }) => void) {
  const margin = 12
  await nextTick()
  const panel = panelRef.value
  if (!panel)
    return

  setPosition({
    x: Math.max(margin, Math.min(position.x, window.innerWidth - panel.offsetWidth - margin)),
    y: Math.max(margin, Math.min(position.y, window.innerHeight - panel.offsetHeight - margin)),
  })
}

async function openContextMenu(event: MouseEvent, targetId: string, targetType: ItemType) {
  closeDesktopMenu()
  contextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    targetId,
  }
  contextMenuTargetType.value = targetType

  await positionMenu(contextMenuRef, { x: event.clientX, y: event.clientY }, ({ x, y }) => {
    contextMenu.value.x = x
    contextMenu.value.y = y
  })
}

function updateContextWidgetSize(size: WidgetSize) {
  const location = findWidgetLocation(contextMenu.value.targetId)
  if (!location)
    return

  const page = activePage.value
  if (!page)
    return

  const nextPages = [...pages.value]
  const nextPage: DesktopPage = {
    ...page,
    items: [...page.items],
  }
  const widget = nextPage.items[location.itemIndex]
  if (!widget || widget.type !== 'widget')
    return

  nextPage.items[location.itemIndex] = {
    ...widget,
    size,
  }
  nextPages[location.pageIndex] = nextPage
  pages.value = nextPages
  closeContextMenu()
}

async function openDesktopMenu(event: MouseEvent) {
  if (iconModal.value.show || activeFolder.value || isSettingsOpen.value)
    return

  const target = event.target as HTMLElement | null
  if (target?.closest('[data-grid-item],[data-floating-panel],[data-prevent-desktop-menu]'))
    return

  closeContextMenu()
  closeFolder()

  desktopMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
  }

  await positionMenu(desktopMenuRef, { x: event.clientX, y: event.clientY }, ({ x, y }) => {
    desktopMenu.value.x = x
    desktopMenu.value.y = y
  })
}

function openSettings() {
  closeContextMenu()
  closeDesktopMenu()
  isSettingsOpen.value = true
}

function applySuggestion(title: string) {
  omnibar.value = title
  omnibarRef.value?.focus()
}

function submitQuickSearch(engine: 'google' | 'github' | 'youtube') {
  const query = omnibar.value.trim()
  if (!query)
    return

  if (engine === 'github') {
    openUrl(`https://github.com/search?q=${encodeURIComponent(query)}`)
    return
  }

  if (engine === 'youtube') {
    openUrl(`https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`)
    return
  }

  openUrl(`https://www.google.com/search?q=${encodeURIComponent(query)}`)
}

function findMatchedApp(search: string) {
  const page = activePage.value
  if (!page)
    return null

  for (const item of page.items) {
    if (isAppItem(item) && item.title.toLowerCase().includes(search))
      return item

    if (isFolderItem(item)) {
      const match = item.children.find(child => child.title.toLowerCase().includes(search))
      if (match)
        return match
    }
  }

  return null
}

function resolveOmnibarTarget(input: string) {
  if (/^https?:\/\//i.test(input))
    return input

  if (/^[\w.-]+\.[a-z]{2,}(\/.*)?$/i.test(input))
    return `https://${input}`

  return `https://www.google.com/search?q=${encodeURIComponent(input)}`
}

function submitOmnibar() {
  const raw = omnibar.value.trim()
  if (!raw)
    return

  const matchedApp = findMatchedApp(raw.toLowerCase())
  if (matchedApp && (matchedApp.title.toLowerCase() === raw.toLowerCase() || visibleItems.value.length === 1)) {
    openApp(matchedApp)
    return
  }

  openUrl(resolveOmnibarTarget(raw))
}

function reorderActivePage(oldIndex: number, newIndex: number) {
  if (oldIndex === newIndex || keyword.value)
    return

  const page = activePage.value
  if (!page)
    return

  const pageIndex = pages.value.findIndex(item => item.id === page.id)
  if (pageIndex < 0)
    return

  const nextPages = [...pages.value]
  nextPages[pageIndex] = {
    ...page,
    items: reorder(page.items, oldIndex, newIndex),
  }
  pages.value = nextPages
}

function syncSortableState() {
  sortable?.option('disabled', Boolean(keyword.value))
}

function initSortable() {
  if (!gridRef.value)
    return

  sortable?.destroy()
  sortable = Sortable.create(gridRef.value, {
    animation: 220,
    easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
    ghostClass: 'opacity-30',
    chosenClass: 'scale-105',
    dragClass: 'rotate-1',
    draggable: '[data-grid-item]',
    onEnd(event: SortableEvent) {
      if (event.oldIndex == null || event.newIndex == null)
        return

      reorderActivePage(event.oldIndex, event.newIndex)
    },
  })

  syncSortableState()
}

function handleWindowKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    omnibarRef.value?.focus()
    omnibarRef.value?.select()
    return
  }

  if (event.key === 'Escape') {
    closeContextMenu()
    closeDesktopMenu()
    closeIconModal()
    closeFolder()
    isSettingsOpen.value = false
  }
}

onClickOutside(contextMenuRef, () => {
  if (contextMenu.value.show)
    closeContextMenu()
})

onClickOutside(desktopMenuRef, () => {
  if (desktopMenu.value.show)
    closeDesktopMenu()
})

onClickOutside(iconModalPanelRef, () => {
  if (iconModal.value.show)
    closeIconModal()
})

watch(() => `${activePageId.value}:${visibleItems.value.map(item => item.id).join('|')}`, async () => {
  await nextTick()
  initSortable()
})

watch(keyword, () => {
  syncSortableState()
  closeContextMenu()
  closeDesktopMenu()
  closeFolder()
  closeIconModal()
})

watch(activePageId, () => {
  closeContextMenu()
  closeDesktopMenu()
  closeFolder()
  closeIconModal()
})

watch(() => appSettings.value.clockUse24Hour, () => {
  updateClock()
})

onMounted(async () => {
  window.addEventListener('keydown', handleWindowKeydown)
  window.addEventListener('resize', updateViewportMetrics)
  updateViewportMetrics()
  updateClock()
  clockTimer = window.setInterval(updateClock, 60_000)
  await nextTick()
  initSortable()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
  window.removeEventListener('resize', updateViewportMetrics)
  if (clockTimer != null)
    window.clearInterval(clockTimer)
  sortable?.destroy()
  sortable = null
})
</script>

<template>
  <div
    class="relative isolate min-h-screen overflow-hidden bg-slate-950 bg-cover bg-center bg-no-repeat text-white"
    :style="{ backgroundImage: `url(${scenicWallpaper})` }"
    @contextmenu.prevent="openDesktopMenu"
  >
    <div class="absolute inset-0" :style="wallpaperBlurStyle" />
    <div class="absolute inset-0" :style="backgroundMaskStyle" />
    <div class="absolute inset-x-0 bottom-0 h-56" :style="backgroundFloorStyle" />
    <template v-if="appSettings.showBackdropGlow">
      <div class="absolute -left-24 top-0 h-96 w-96 rounded-full blur-3xl" :style="themeGlowStyle" />
      <div class="absolute right-0 top-12 h-80 w-80 rounded-full bg-amber-100/20 blur-3xl" />
      <div class="absolute bottom-0 right-0 h-96 w-96 rounded-full blur-3xl" :style="themeGlowStyle" />
    </template>

    <main class="relative z-10 min-h-screen px-5 pb-8 pt-6 sm:px-8 lg:px-12">
      <div class="mx-auto flex min-h-screen max-w-[1400px] flex-col">
        <header class="flex items-start justify-between gap-6">
          <div class="drop-shadow-md">
            <p class="text-[11px] uppercase tracking-[0.38em] text-white/60">
              Life Kline Hub
            </p>
            <h1 class="mt-3 text-2xl font-semibold tracking-tight text-white/95 sm:text-[2rem]">
              {{ activePage?.title || '主屏' }}
            </h1>
            <p class="mt-1 text-sm text-white/75 drop-shadow-md">
              Local-First 桌面工作台，离线即可直接渲染。
            </p>
          </div>

          <div v-if="appSettings.showClock" class="hidden text-right sm:block" :style="clockBlockStyle">
            <p class="text-4xl font-semibold tracking-tight text-white/95 drop-shadow-md">
              {{ clock }}
            </p>
            <p v-if="appSettings.showDate" class="mt-1 text-sm text-white/75 drop-shadow-md">
              {{ dateLabel }}
            </p>
            <p class="mt-3 text-xs text-white/65 drop-shadow-md">
              {{ pages.length }} 页布局 · {{ totalItems }} 个入口
            </p>
          </div>
        </header>

        <form
          v-if="appSettings.showSearch"
          class="mt-8 flex justify-center sm:mt-10"
          :style="{ opacity: appSettings.searchOpacity / 100 }"
          @submit.prevent="submitOmnibar"
        >
          <div class="relative w-full" :style="searchWrapStyle">
            <input
              ref="omnibarRef"
              v-model="omnibar"
              type="text"
              placeholder="搜索应用、打开网址，或直接开始搜索"
              autocomplete="off"
              spellcheck="false"
              class="h-[3.75rem] w-full rounded-full border border-white/10 bg-black/[0.28] pl-7 pr-24 text-[15px] text-white placeholder:text-white/40 shadow-[0_20px_80px_rgba(3,7,18,0.35)] backdrop-blur-md outline-none transition focus:border-white/20 focus:ring-4 focus:ring-sky-200/25"
              :style="searchInputStyle"
            >

            <button
              type="submit"
              class="absolute right-2 top-1/2 inline-flex h-10 -translate-y-1/2 items-center rounded-full border border-white/10 bg-white/10 px-4 text-sm text-white/85 backdrop-blur-md transition hover:bg-white/15"
            >
              Enter
            </button>

            <div
              v-if="appSettings.showShortcutBadge"
              class="absolute right-[5.6rem] top-1/2 hidden -translate-y-1/2 rounded-full border px-2.5 py-1 text-[11px] font-medium sm:inline-flex"
              :style="searchBadgeStyle"
            >
              {{ shortcutBadgeLabel }}
            </div>
          </div>
        </form>

        <div v-if="searchSuggestions.length && appSettings.showSearch" class="mt-4 flex flex-wrap items-center justify-center gap-2">
          <button
            v-for="suggestion in searchSuggestions"
            :key="suggestion.id"
            type="button"
            class="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-white/80 backdrop-blur-md transition hover:bg-white/12"
            @click="applySuggestion(suggestion.title)"
          >
            {{ suggestion.title }}
          </button>
        </div>

        <div v-if="appSettings.allowQuickSearch && appSettings.showSearch" class="mt-4 flex items-center justify-center gap-2 text-xs">
          <button type="button" class="rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-white/70 backdrop-blur-sm transition hover:bg-white/12 hover:text-white" @click="submitQuickSearch('google')">
            Google
          </button>
          <button type="button" class="rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-white/70 backdrop-blur-sm transition hover:bg-white/12 hover:text-white" @click="submitQuickSearch('github')">
            GitHub
          </button>
          <button type="button" class="rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-white/70 backdrop-blur-sm transition hover:bg-white/12 hover:text-white" @click="submitQuickSearch('youtube')">
            YouTube
          </button>
        </div>

        <p class="mt-3 text-center text-xs text-white/65 drop-shadow-md">
          {{ keyword ? '筛选中，已暂停拖拽排序' : '拖动图标或小组件即可重排当前页面' }}
        </p>

        <section class="mt-10 flex-1 sm:mt-14">
          <div
            v-if="visibleItems.length"
            ref="gridRef"
            class="grid grid-flow-dense justify-items-center"
            :style="gridStyle"
          >
            <template v-for="item in visibleItems" :key="item.id">
              <button
                v-if="item.type === 'app'"
                type="button"
                data-grid-item
                data-item-type="app"
                class="group flex w-full flex-col items-center justify-self-center self-start"
                :style="iconButtonStyle"
                @click="openItem(item)"
                @contextmenu.stop.prevent="openContextMenu($event, item.id, item.type)"
              >
                <div
                  class="relative z-10 transition-transform duration-300 group-hover:scale-105 transform-gpu will-change-transform backface-hidden [backface-visibility:hidden]"
                  :style="iconSurfaceStyle"
                >
                  <div class="absolute inset-0 -z-10 overflow-hidden bg-white/10 backdrop-blur-xl border" :style="iconBackdropStyle" />
                  <img
                    :src="item.icon"
                    :alt="item.title"
                    class="relative h-full w-full object-cover shadow-sm"
                    :style="iconImageStyle"
                  >
                </div>
                <span
                  v-if="appSettings.showIconLabels"
                  class="mt-1.5 w-full truncate text-center text-xs text-white/90 drop-shadow-md"
                  :style="{ opacity: appSettings.iconLabelOpacity / 100 }"
                >
                  {{ item.title }}
                </span>
                <span
                  v-if="appSettings.enableShortcutHints && item.shortcut"
                  class="mt-1 rounded-full border border-white/10 bg-black/20 px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-white/60 backdrop-blur-sm"
                >
                  {{ item.shortcut }}
                </span>
              </button>

              <button
                v-else-if="item.type === 'folder'"
                type="button"
                data-grid-item
                data-item-type="folder"
                class="group flex w-full flex-col items-center justify-self-center self-start"
                :style="iconButtonStyle"
                @click="openItem(item)"
                @contextmenu.stop.prevent
              >
                <div
                  class="relative z-10 transition-transform duration-300 group-hover:scale-105 transform-gpu will-change-transform backface-hidden [backface-visibility:hidden]"
                  :style="iconSurfaceStyle"
                >
                  <div class="absolute inset-0 -z-10 overflow-hidden bg-white/[0.18] backdrop-blur-xl border" :style="iconBackdropStyle" />
                  <div class="relative grid h-full w-full grid-cols-3 gap-1 p-2">
                    <div
                      v-for="child in item.children.slice(0, 6)"
                      :key="child.id"
                      class="overflow-hidden bg-white/[0.12]"
                      :style="folderThumbRadiusStyle"
                    >
                      <img
                        :src="child.icon"
                        :alt="child.title"
                        class="h-full w-full object-cover"
                      >
                    </div>
                  </div>
                </div>
                <span
                  v-if="appSettings.showIconLabels"
                  class="mt-1.5 w-full truncate text-center text-xs text-white/90 drop-shadow-md"
                  :style="{ opacity: appSettings.iconLabelOpacity / 100 }"
                >
                  {{ item.title }}
                </span>
              </button>

              <article
                v-else
                data-grid-item
                data-item-type="widget"
                class="group relative isolate h-full w-full cursor-pointer self-stretch justify-self-stretch transition-transform duration-300 hover:-translate-y-0.5 hover:scale-[1.01] transform-gpu will-change-transform backface-hidden [backface-visibility:hidden]"
                :class="widgetSpanClass(item.size)"
                @contextmenu.stop.prevent="openContextMenu($event, item.id, item.type)"
              >
                <div class="absolute inset-0 -z-10 h-full w-full overflow-hidden rounded-[24px] border border-white/[0.14] bg-white/[0.16] shadow-[0_26px_80px_rgba(15,23,42,0.18)] backdrop-blur-xl">
                  <div class="absolute inset-0" :class="item.accentClass" />
                  <div class="absolute -right-10 -top-10 h-32 w-32 rounded-full blur-3xl" :class="item.glowClass" />
                  <div class="absolute inset-x-0 top-0 h-px bg-white/25" />
                </div>

                <div class="relative flex h-full w-full min-h-0 flex-col justify-between overflow-hidden p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-[11px] uppercase tracking-[0.28em] text-white/60">
                        {{ item.eyebrow }}
                      </p>
                      <h2 class="mt-2 text-lg font-semibold tracking-tight text-white">
                        {{ item.title }}
                      </h2>
                    </div>

                    <span class="rounded-full border border-white/10 bg-black/15 px-2.5 py-1 text-[10px] uppercase tracking-[0.24em] text-white/65">
                      {{ item.size }}
                    </span>
                  </div>

                  <div class="mt-4 text-3xl font-semibold tracking-tight text-white">
                    {{ item.value }}
                  </div>

                  <div class="mt-4 min-h-0 flex-1 space-y-2 overflow-y-auto text-sm text-white/88 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                    <p
                      v-for="line in item.lines"
                      :key="line"
                      class="rounded-2xl border border-white/10 bg-white/[0.08] px-3 py-2 backdrop-blur-sm"
                    >
                      {{ line }}
                    </p>
                  </div>

                  <p class="mt-auto pt-4 text-xs text-white/65">
                    {{ item.footer }}
                  </p>
                </div>
              </article>
            </template>
          </div>

          <div
            v-else
            class="flex h-40 items-center justify-center text-sm text-white/70 drop-shadow-md"
          >
            没有匹配的内容，按 Enter 可直接使用 Omnibar 搜索。
          </div>
        </section>

        <footer class="mt-8 flex items-center justify-center gap-3 pb-2 sm:mt-10">
          <button
            v-for="page in pages"
            :key="page.id"
            type="button"
            :aria-label="page.title"
            class="h-3 rounded-full transition-all duration-300"
            :class="page.id === activePageId ? 'w-10 border shadow-lg backdrop-blur-md' : 'w-3 hover:bg-white/50'"
            :style="page.id === activePageId ? activePageDotStyle : inactivePageDotStyle"
            @click="setActivePage(page.id)"
          />
        </footer>
      </div>
    </main>

    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="activeFolder"
        class="fixed inset-0 z-30 flex items-end bg-slate-950/[0.28] p-4 backdrop-blur-sm sm:items-center sm:justify-center"
        @click="closeFolder"
      >
        <div
          class="relative w-full max-w-2xl overflow-hidden rounded-[32px] border border-white/[0.12] bg-black/[0.22] p-6 shadow-[0_30px_100px_rgba(15,23,42,0.35)] backdrop-blur-2xl"
          data-floating-panel
          @click.stop
          @contextmenu.stop.prevent
        >
          <div class="absolute inset-0 bg-gradient-to-br from-white/15 via-white/5 to-transparent" />

          <div class="relative">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-[11px] uppercase tracking-[0.3em] text-white/60">
                  Folder
                </p>
                <h2 class="mt-2 text-2xl font-semibold tracking-tight text-white">
                  {{ activeFolder.title }}
                </h2>
                <p class="mt-1 text-sm text-white/70">
                  {{ activeFolder.children.length }} 个应用
                </p>
              </div>

              <button
                type="button"
                class="rounded-full border border-white/10 bg-white/10 px-4 py-2 text-sm text-white/80 backdrop-blur-md transition hover:bg-white/15"
                @click="closeFolder"
              >
                关闭
              </button>
            </div>

            <div class="mt-6 grid grid-cols-3 gap-5 sm:grid-cols-4">
              <button
                v-for="child in activeFolder.children"
                :key="child.id"
                type="button"
                class="group flex flex-col items-center gap-2"
                @click="openApp(child)"
                @contextmenu.stop.prevent="openContextMenu($event, child.id, child.type)"
              >
                <div
                  class="relative z-10 transition-transform duration-300 group-hover:scale-105 transform-gpu will-change-transform backface-hidden [backface-visibility:hidden]"
                  :style="iconSurfaceStyle"
                >
                  <div class="absolute inset-0 -z-10 overflow-hidden bg-white/10 backdrop-blur-xl border" :style="iconBackdropStyle" />
                  <img
                    :src="child.icon"
                    :alt="child.title"
                    class="relative h-full w-full object-cover shadow-sm"
                    :style="iconImageStyle"
                  >
                </div>
                <span
                  v-if="appSettings.showIconLabels"
                  class="w-full truncate text-center text-xs text-white/90 drop-shadow-md"
                  :style="{ opacity: appSettings.iconLabelOpacity / 100 }"
                >
                  {{ child.title }}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <button
      type="button"
      title="设置"
      aria-label="打开设置"
      data-prevent-desktop-menu
      class="fixed bottom-8 right-8 z-40 flex h-12 w-12 cursor-pointer items-center justify-center overflow-hidden rounded-full border border-white/10 bg-black/20 text-white/70 shadow-lg backdrop-blur-md transition-all hover:scale-110 hover:bg-white/20 hover:text-white transform-gpu"
      :style="settingsButtonStyle"
      @click="openSettings"
      @contextmenu.stop.prevent
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="h-5 w-5"
      >
        <path d="M12 3.75 13.3 5.7a1 1 0 0 0 .86.46h2.2a1 1 0 0 1 .9.56l.88 1.77a1 1 0 0 0 .74.54l2.14.31a1 1 0 0 1 .55 1.7l-1.55 1.51a1 1 0 0 0-.29.88l.36 2.13a1 1 0 0 1-1.45 1.05l-1.96-1.03a1 1 0 0 0-.94 0l-1.96 1.03a1 1 0 0 1-1.45-1.05l.36-2.13a1 1 0 0 0-.29-.88L2.17 10.3a1 1 0 0 1 .55-1.7l2.14-.31a1 1 0 0 0 .74-.54l.88-1.77a1 1 0 0 1 .9-.56h2.2a1 1 0 0 0 .86-.46L12 3.75Z" />
        <circle cx="12" cy="12" r="3.1" />
      </svg>
    </button>

    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="contextMenu.show"
        ref="contextMenuRef"
        data-floating-panel
        class="fixed z-50 w-48 rounded-xl border border-white/10 bg-slate-900/70 py-1.5 text-sm text-white/90 shadow-2xl backdrop-blur-2xl"
        :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
        @contextmenu.stop.prevent
      >
        <ul>
          <li
            class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10"
            @click="contextMenuTargetType === 'widget' ? openContextTarget() : openEditIconModal()"
          >
            {{ contextMenuTargetType === 'widget' ? '打开小组件' : '编辑' }}
          </li>
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="contextTargetApp && openItemInNewTab(contextTargetApp)">
            在新标签页打开
          </li>
          <li
            class="group relative cursor-pointer px-4 py-2 transition-colors hover:bg-white/10"
          >
            <div class="flex items-center justify-between">
              <span>尺寸</span>
              <span class="text-white/45">&gt;</span>
            </div>

            <div
              v-if="contextMenuTargetType === 'widget'"
              class="absolute left-full top-0 hidden pl-2 group-hover:block"
            >
              <div class="w-28 rounded-xl border border-white/10 bg-slate-900/70 py-1.5 text-sm text-white/90 shadow-2xl backdrop-blur-2xl">
                <ul>
                  <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="updateContextWidgetSize('1x1')">
                    XS 1x1
                  </li>
                  <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="updateContextWidgetSize('1x2')">
                    S 1x2
                  </li>
                  <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="updateContextWidgetSize('2x1')">
                    M 2x1
                  </li>
                  <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="updateContextWidgetSize('2x2')">
                    L 2x2
                  </li>
                  <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="updateContextWidgetSize('2x4')">
                    XL 2x4
                  </li>
                </ul>
              </div>
            </div>
          </li>
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="cloneContextTarget">
            克隆
          </li>
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="importContextTargetToBookmarks">
            导入到书签
          </li>
          <div class="my-1 h-px bg-white/10" />
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="markContextAction('批量编辑')">
            批量编辑
          </li>
          <li class="cursor-pointer px-4 py-2 text-rose-200 transition-colors hover:bg-white/10" @click="deleteContextTarget">
            删除
          </li>
        </ul>
      </div>
    </transition>

    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="desktopMenu.show"
        ref="desktopMenuRef"
        data-floating-panel
        class="fixed z-50 w-48 rounded-xl border border-white/10 bg-slate-900/70 py-1.5 text-sm text-white/90 shadow-2xl backdrop-blur-2xl"
        :style="{ left: `${desktopMenu.x}px`, top: `${desktopMenu.y}px` }"
        @contextmenu.stop.prevent
      >
        <ul>
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="openAddIconModal">
            新增图标
          </li>
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="openWidgetTabModal">
            小组件商店
          </li>
          <li class="flex cursor-pointer items-center justify-between px-4 py-2 transition-colors hover:bg-white/10" @click="markContextAction('壁纸')">
            <span>壁纸</span>
            <span class="text-white/45">&gt;</span>
          </li>
          <li class="flex cursor-pointer items-center justify-between px-4 py-2 transition-colors hover:bg-white/10" @click="openSettings">
            <span>设置</span>
            <span class="text-white/45">&gt;</span>
          </li>
          <div class="my-1 h-px bg-white/10" />
          <li class="flex cursor-pointer items-center justify-between px-4 py-2 transition-colors hover:bg-white/10" @click="markContextAction('图标排列')">
            <span>图标排列</span>
            <span class="text-white/45">&gt;</span>
          </li>
          <li class="flex cursor-pointer items-center justify-between px-4 py-2 transition-colors hover:bg-white/10" @click="markContextAction('文件夹合并')">
            <span>文件夹合并</span>
            <span class="text-white/45">&gt;</span>
          </li>
        </ul>
      </div>
    </transition>

    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="iconModal.show"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm"
        @click="closeIconModal"
        @contextmenu.stop.prevent
      >
        <div
          ref="iconModalPanelRef"
          data-floating-panel
          class="flex w-[400px] max-w-full flex-col rounded-2xl border border-white/5 bg-[#1e2330] p-4 text-sm text-gray-200 shadow-2xl"
          @click.stop
        >
          <div class="mb-4 flex rounded-xl bg-[#151924] p-1">
            <button
              type="button"
              class="flex-1 rounded-lg px-3 py-2 text-xs transition-colors"
              :class="iconModalTab === 'store' ? 'bg-blue-600/30 text-white' : 'text-gray-400 hover:text-gray-200'"
              @click="iconModalTab = 'store'"
            >
              图标商店
            </button>
            <button
              type="button"
              class="flex-1 rounded-lg px-3 py-2 text-xs transition-colors"
              :class="iconModalTab === 'custom' ? 'bg-blue-600/30 text-white' : 'text-gray-400 hover:text-gray-200'"
              @click="iconModalTab = 'custom'"
            >
              图标自定义
            </button>
            <button
              type="button"
              class="flex-1 rounded-lg px-3 py-2 text-xs transition-colors"
              :class="iconModalTab === 'widget' ? 'bg-blue-600/30 text-white' : 'text-gray-400 hover:text-gray-200'"
              @click="iconModalTab = 'widget'"
            >
              小组件
            </button>
          </div>

          <template v-if="iconModalTab === 'custom'">
            <div class="space-y-3">
              <label class="block">
                <span class="mb-1.5 block text-xs text-gray-400">外链地址</span>
                <input
                  v-model="iconModal.form.url"
                  type="text"
                  placeholder="https://example.com"
                  class="w-full rounded-lg bg-[#151924] px-3 py-2 outline-none ring-blue-500 focus:ring-1"
                  @blur="autoFetchIcon"
                >
              </label>

              <label class="block">
                <span class="mb-1.5 block text-xs text-gray-400">图标链接</span>
                <input
                  v-model="iconModal.form.icon"
                  type="text"
                  placeholder="https://example.com/icon.png"
                  class="w-full rounded-lg bg-[#151924] px-3 py-2 outline-none ring-blue-500 focus:ring-1"
                >
              </label>

              <label class="block">
                <span class="mb-1.5 block text-xs text-gray-400">图标名称</span>
                <input
                  v-model="iconModal.form.title"
                  type="text"
                  placeholder="输入图标名称"
                  class="w-full rounded-lg bg-[#151924] px-3 py-2 outline-none ring-blue-500 focus:ring-1"
                >
              </label>

              <label class="block">
                <span class="mb-1.5 block text-xs text-gray-400">图标描述</span>
                <input
                  v-model="iconModal.form.desc"
                  type="text"
                  placeholder="输入图标描述"
                  class="w-full rounded-lg bg-[#151924] px-3 py-2 outline-none ring-blue-500 focus:ring-1"
                >
              </label>

              <label class="block">
                <span class="mb-1.5 block text-xs text-gray-400">快捷键</span>
                <input
                  v-model="iconModal.form.shortcut"
                  type="text"
                  placeholder="例如：Cmd+K"
                  class="w-full rounded-lg bg-[#151924] px-3 py-2 outline-none ring-blue-500 focus:ring-1"
                >
              </label>
            </div>

            <div class="mt-5">
              <div class="flex justify-center">
                <div class="relative h-20 w-20 overflow-hidden rounded-2xl bg-[#151924]">
                  <div class="absolute inset-0 rounded-2xl border border-white/5 bg-white/[0.04]" />
                  <img
                    :src="iconPreviewSrc"
                    alt="图标预览"
                    class="relative h-full w-full object-cover"
                  >
                </div>
              </div>

              <div class="mt-4 flex justify-center gap-2">
                <button
                  type="button"
                  class="rounded-lg bg-[#151924] px-3 py-2 text-xs text-gray-200 transition hover:bg-[#202635]"
                  @click="fetchIconForModal"
                >
                  抓取图标
                </button>
                <button
                  type="button"
                  class="rounded-lg bg-[#151924] px-3 py-2 text-xs text-gray-200 transition hover:bg-[#202635]"
                  @click="useSolidIconForModal"
                >
                  纯色图标
                </button>
                <button
                  type="button"
                  class="rounded-lg bg-[#151924] px-3 py-2 text-xs text-gray-200 transition hover:bg-[#202635]"
                  @click="triggerIconUpload"
                >
                  上传图标
                </button>
              </div>
            </div>
          </template>

          <div
            v-else
            class="flex min-h-[320px] items-center justify-center rounded-xl bg-[#151924] text-center text-sm text-gray-400"
          >
            {{ iconModalTab === 'store' ? '图标商店正在规划中。' : '小组件商店正在规划中。' }}
          </div>

          <div class="mt-5 flex justify-end gap-2">
            <button
              type="button"
              class="rounded-lg bg-[#151924] px-4 py-2 text-gray-300 transition hover:bg-[#202635]"
              @click="closeIconModal"
            >
              取消
            </button>
            <button
              type="button"
              class="rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-900/60 disabled:text-white/50"
              :disabled="iconModalTab !== 'custom'"
              @click="saveIconModal"
            >
              保存
            </button>
          </div>
        </div>
      </div>
    </transition>

    <input
      ref="iconUploadInputRef"
      type="file"
      accept="image/*"
      class="hidden"
      @change="handleIconUpload"
    >

    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-2"
    >
      <div
        v-if="appSettings.showScreenSaverQuote"
        class="pointer-events-none fixed bottom-8 left-8 z-20 hidden max-w-sm rounded-[28px] border bg-black/15 px-5 py-4 backdrop-blur-xl md:block"
        :style="quoteCardStyle"
      >
        <p class="text-sm leading-6 text-white/88">
          {{ quoteText }}
        </p>
        <p class="mt-3 text-[11px] uppercase tracking-[0.26em]" :style="themeTextStyle">
          {{ quoteMeta }}
        </p>
      </div>
    </transition>

    <SettingsModal v-if="isSettingsOpen" @close="isSettingsOpen = false" />
  </div>
</template>
