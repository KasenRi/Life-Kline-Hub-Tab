<script setup lang="ts">
import Sortable, { type SortableEvent } from 'sortablejs'
import { onClickOutside, useStorage } from '@vueuse/core'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type ItemType = 'app' | 'folder' | 'widget'
type WidgetSize = '2x2' | '2x4'

interface BaseItem {
  id: string
  type: ItemType
  title: string
}

interface AppItem extends BaseItem {
  type: 'app'
  icon: string
  url: string
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

const activeFolderId = ref<string | null>(null)
const clock = ref('')
const dateLabel = ref('')
const contextMenu = ref<{ show: boolean, x: number, y: number, targetId: string | null }>({
  show: false,
  x: 0,
  y: 0,
  targetId: null,
})
const omnibarRef = ref<HTMLInputElement | null>(null)
const gridRef = ref<HTMLElement | null>(null)
const contextMenuRef = ref<HTMLElement | null>(null)

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

    if (isFolderItem(item))
      return item.title.toLowerCase().includes(keyword.value) || item.children.some(child => child.title.toLowerCase().includes(keyword.value))

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

function widgetSpanClass(size: WidgetSize) {
  return size === '2x4' ? 'col-span-2 row-span-4' : 'col-span-2 row-span-2'
}

function updateClock() {
  const now = new Date()
  clock.value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  dateLabel.value = now.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    weekday: 'short',
  })
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
}

function openUrl(url: string) {
  window.location.assign(url)
}

function openApp(app: AppItem) {
  closeContextMenu()
  closeFolder()
  openUrl(app.url)
}

function openItem(item: DesktopItem) {
  closeContextMenu()

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

function cloneContextTarget() {
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
  if (contextTargetApp.value)
    console.info(`[Life Kline Hub] ${label}: ${contextTargetApp.value.title}`)
  closeContextMenu()
}

async function openContextMenu(event: MouseEvent, targetId: string) {
  const margin = 12
  contextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    targetId,
  }

  await nextTick()
  const menu = contextMenuRef.value
  if (!menu)
    return

  contextMenu.value.x = Math.min(event.clientX, window.innerWidth - menu.offsetWidth - margin)
  contextMenu.value.y = Math.min(event.clientY, window.innerHeight - menu.offsetHeight - margin)
}

function openSettings() {
  closeContextMenu()

  const browserApi = globalThis.browser as { runtime?: { openOptionsPage?: () => Promise<void> } } | undefined
  const chromeApi = globalThis.chrome as { runtime?: { openOptionsPage?: () => void } } | undefined

  if (browserApi?.runtime?.openOptionsPage) {
    void browserApi.runtime.openOptionsPage()
    return
  }

  if (chromeApi?.runtime?.openOptionsPage) {
    chromeApi.runtime.openOptionsPage()
    return
  }

  window.open(new URL('../options/index.html', window.location.href).href, '_blank', 'noopener,noreferrer')
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
    closeFolder()
  }
}

onClickOutside(contextMenuRef, () => {
  if (contextMenu.value.show)
    closeContextMenu()
})

watch(() => `${activePageId.value}:${visibleItems.value.map(item => item.id).join('|')}`, async () => {
  await nextTick()
  initSortable()
})

watch(keyword, () => {
  syncSortableState()
  closeContextMenu()
  closeFolder()
})

watch(activePageId, () => {
  closeContextMenu()
  closeFolder()
})

onMounted(async () => {
  window.addEventListener('keydown', handleWindowKeydown)
  updateClock()
  clockTimer = window.setInterval(updateClock, 60_000)
  await nextTick()
  initSortable()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
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
    @contextmenu.prevent="closeContextMenu"
  >
    <div class="absolute inset-0 bg-gradient-to-b from-slate-950/[0.04] via-slate-950/[0.12] to-slate-950/[0.32]" />
    <div class="absolute inset-x-0 bottom-0 h-56 bg-gradient-to-t from-slate-950/[0.32] to-transparent" />
    <div class="absolute -left-24 top-0 h-96 w-96 rounded-full bg-sky-200/[0.12] blur-3xl" />
    <div class="absolute right-0 top-12 h-80 w-80 rounded-full bg-amber-100/20 blur-3xl" />
    <div class="absolute bottom-0 right-0 h-96 w-96 rounded-full bg-sky-100/15 blur-3xl" />

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

          <div class="hidden text-right sm:block">
            <p class="text-4xl font-semibold tracking-tight text-white/95 drop-shadow-md">
              {{ clock }}
            </p>
            <p class="mt-1 text-sm text-white/75 drop-shadow-md">
              {{ dateLabel }}
            </p>
            <p class="mt-3 text-xs text-white/65 drop-shadow-md">
              {{ pages.length }} 页布局 · {{ totalItems }} 个入口
            </p>
          </div>
        </header>

        <form class="mt-8 flex justify-center sm:mt-10" @submit.prevent="submitOmnibar">
          <div class="relative w-full max-w-3xl md:w-[56%]">
            <input
              ref="omnibarRef"
              v-model="omnibar"
              type="text"
              placeholder="搜索应用、打开网址，或直接开始搜索"
              autocomplete="off"
              spellcheck="false"
              class="h-[3.75rem] w-full rounded-full border border-white/10 bg-black/[0.28] pl-7 pr-24 text-[15px] text-white placeholder:text-white/40 shadow-[0_20px_80px_rgba(3,7,18,0.35)] backdrop-blur-md outline-none transition focus:border-white/20 focus:ring-4 focus:ring-sky-200/25"
            >

            <button
              type="submit"
              class="absolute right-2 top-1/2 inline-flex h-10 -translate-y-1/2 items-center rounded-full border border-white/10 bg-white/10 px-4 text-sm text-white/85 backdrop-blur-md transition hover:bg-white/15"
            >
              Enter
            </button>
          </div>
        </form>

        <p class="mt-3 text-center text-xs text-white/65 drop-shadow-md">
          {{ keyword ? '筛选中，已暂停拖拽排序' : '拖动图标或小组件即可重排当前页面' }}
        </p>

        <section class="mt-10 flex-1 sm:mt-14">
          <div
            v-if="visibleItems.length"
            ref="gridRef"
            class="grid auto-rows-[98px] grid-flow-dense grid-cols-4 justify-items-center gap-x-4 gap-y-8 sm:grid-cols-6 sm:gap-x-6 lg:grid-cols-8 xl:grid-cols-10"
          >
            <template v-for="item in visibleItems" :key="item.id">
              <button
                v-if="item.type === 'app'"
                type="button"
                data-grid-item
                class="group flex w-full max-w-[92px] flex-col items-center gap-1.5 justify-self-center self-start"
                @click="openItem(item)"
                @contextmenu.stop.prevent="openContextMenu($event, item.id)"
              >
                <div class="h-14 w-14 overflow-hidden rounded-2xl shadow-[0_12px_35px_rgba(15,23,42,0.22)] transition-transform duration-300 group-hover:scale-105 transform-gpu backface-hidden [backface-visibility:hidden] will-change-transform">
                  <img
                    :src="item.icon"
                    :alt="item.title"
                    class="h-full w-full rounded-2xl object-cover shadow-sm"
                  >
                </div>
                <span class="w-full truncate text-center text-xs text-white/90 drop-shadow-md">
                  {{ item.title }}
                </span>
              </button>

              <button
                v-else-if="item.type === 'folder'"
                type="button"
                data-grid-item
                class="group flex w-full max-w-[92px] flex-col items-center gap-1.5 justify-self-center self-start"
                @click="openItem(item)"
              >
                <div class="h-14 w-14 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.18] shadow-[0_14px_35px_rgba(15,23,42,0.18)] transition-transform duration-300 group-hover:scale-105 transform-gpu backface-hidden [backface-visibility:hidden] will-change-transform backdrop-blur-md">
                  <div class="grid h-full w-full grid-cols-3 gap-1 p-2">
                    <div
                      v-for="child in item.children.slice(0, 6)"
                      :key="child.id"
                      class="overflow-hidden rounded-lg bg-white/[0.12]"
                    >
                      <img
                        :src="child.icon"
                        :alt="child.title"
                        class="h-full w-full object-cover"
                      >
                    </div>
                  </div>
                </div>
                <span class="w-full truncate text-center text-xs text-white/90 drop-shadow-md">
                  {{ item.title }}
                </span>
              </button>

              <article
                v-else
                data-grid-item
                class="group relative overflow-hidden rounded-[24px] border border-white/[0.14] bg-white/[0.16] p-4 shadow-[0_26px_80px_rgba(15,23,42,0.18)] backdrop-blur-xl transition-transform duration-300 hover:-translate-y-0.5 hover:scale-[1.01] transform-gpu backface-hidden [backface-visibility:hidden] will-change-transform"
                :class="widgetSpanClass(item.size)"
              >
                <div class="absolute inset-0" :class="item.accentClass" />
                <div class="absolute -right-10 -top-10 h-32 w-32 rounded-full blur-3xl" :class="item.glowClass" />
                <div class="absolute inset-x-0 top-0 h-px bg-white/25" />

                <div class="relative flex h-full flex-col">
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

                  <div class="mt-4 space-y-2 text-sm text-white/88">
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
            :class="page.id === activePageId ? 'w-10 border border-white/20 bg-white/30 shadow-lg backdrop-blur-md' : 'w-3 bg-white/35 hover:bg-white/50'"
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
          @click.stop
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
                @contextmenu.stop.prevent="openContextMenu($event, child.id)"
              >
                <div class="h-14 w-14 overflow-hidden rounded-2xl transition-transform duration-300 group-hover:scale-105 transform-gpu backface-hidden [backface-visibility:hidden] will-change-transform">
                  <img
                    :src="child.icon"
                    :alt="child.title"
                    class="h-full w-full rounded-2xl object-cover shadow-sm"
                  >
                </div>
                <span class="w-full truncate text-center text-xs text-white/90 drop-shadow-md">
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
      class="fixed bottom-8 right-8 z-40 flex h-12 w-12 cursor-pointer items-center justify-center overflow-hidden rounded-full border border-white/10 bg-black/20 text-white/70 shadow-lg backdrop-blur-md transition-all hover:scale-110 hover:bg-white/20 hover:text-white transform-gpu"
      @click="openSettings"
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
        class="fixed z-50 w-48 rounded-xl border border-white/10 bg-slate-900/70 py-1.5 text-sm text-white/90 shadow-2xl backdrop-blur-2xl"
        :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
        @contextmenu.stop.prevent
      >
        <ul>
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="markContextAction('编辑')">
            编辑
          </li>
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="contextTargetApp && openItemInNewTab(contextTargetApp)">
            在新标签页打开
          </li>
          <li class="cursor-pointer px-4 py-2 transition-colors hover:bg-white/10" @click="markContextAction('尺寸')">
            尺寸
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
  </div>
</template>
