import { computed } from 'vue'
import { useStorage } from '@vueuse/core'

export type TileType = 'app' | 'widget' | 'folder'
export type WidgetSize = '1x1' | '2x1' | '2x2'

interface BaseItem {
  id: string
  type: TileType
  title: string
}

export interface AppItem extends BaseItem {
  type: 'app'
  icon: string
  url: string
  description?: string
  accent: string
}

export interface WidgetItem extends BaseItem {
  type: 'widget'
  size: WidgetSize
  content: string
  accent: string
}

export interface FolderItem extends BaseItem {
  type: 'folder'
  children: AppItem[]
  accent: string
}

export type GridItem = AppItem | WidgetItem | FolderItem

export interface GridPage {
  pageId: string
  title: string
  items: GridItem[]
}

function createMockPages(): GridPage[] {
  return [
    {
      pageId: 'page-1',
      title: '主屏',
      items: [
        { id: '1', type: 'app', title: 'Bilibili', icon: 'B', url: 'https://www.bilibili.com', description: '视频与直播', accent: 'from-pink-300/90 to-rose-200/75' },
        { id: '2', type: 'widget', title: '天气', size: '2x2', content: '27° · 多云转晴\n体感温度 29°\n空气质量优', accent: 'from-sky-300/80 via-cyan-200/70 to-white/30' },
        {
          id: '3',
          type: 'folder',
          title: '开发工具',
          accent: 'from-violet-300/85 to-fuchsia-200/70',
          children: [
            { id: '3-1', type: 'app', title: 'GitHub', icon: 'G', url: 'https://github.com', description: '代码托管', accent: 'from-slate-200/90 to-slate-50/75' },
            { id: '3-2', type: 'app', title: 'Vercel', icon: 'V', url: 'https://vercel.com', description: '部署面板', accent: 'from-slate-100/90 to-neutral-200/80' },
            { id: '3-3', type: 'app', title: 'Figma', icon: 'F', url: 'https://www.figma.com', description: '设计协作', accent: 'from-orange-300/90 to-pink-200/70' },
          ],
        },
        { id: '4', type: 'app', title: 'Notion', icon: 'N', url: 'https://www.notion.so', description: '文档工作区', accent: 'from-stone-200/90 to-zinc-50/80' },
        { id: '5', type: 'app', title: 'YouTube', icon: '▶', url: 'https://www.youtube.com', description: '视频平台', accent: 'from-red-300/90 to-rose-200/75' },
        { id: '6', type: 'widget', title: '待办', size: '2x1', content: '1. 设计迭代\n2. 联调接口\n3. 复盘任务', accent: 'from-amber-300/80 via-yellow-200/70 to-white/30' },
        { id: '7', type: 'app', title: 'Drive', icon: '△', url: 'https://drive.google.com', description: '云端文件', accent: 'from-lime-300/90 to-green-200/75' },
        { id: '8', type: 'app', title: 'Music', icon: '♪', url: 'https://music.apple.com', description: '专注背景音', accent: 'from-fuchsia-300/90 to-pink-200/75' },
      ],
    },
    {
      pageId: 'page-2',
      title: '效率',
      items: [
        { id: '9', type: 'app', title: 'Gmail', icon: 'M', url: 'https://mail.google.com', description: '收件箱', accent: 'from-sky-300/90 to-blue-200/75' },
        { id: '10', type: 'app', title: 'Calendar', icon: '31', url: 'https://calendar.google.com', description: '今日日程', accent: 'from-orange-300/90 to-amber-200/75' },
        { id: '11', type: 'widget', title: '进度追踪', size: '2x2', content: '本周完成 72%\n剩余 3 个里程碑\n下一节点：周五评审', accent: 'from-emerald-300/80 via-lime-200/70 to-white/30' },
        { id: '12', type: 'app', title: 'Slack', icon: 'S', url: 'https://slack.com', description: '团队沟通', accent: 'from-indigo-300/90 to-violet-200/75' },
        {
          id: '13',
          type: 'folder',
          title: '灵感库',
          accent: 'from-cyan-300/85 to-sky-200/70',
          children: [
            { id: '13-1', type: 'app', title: 'Behance', icon: 'B', url: 'https://www.behance.net', description: '案例作品', accent: 'from-blue-300/90 to-cyan-200/75' },
            { id: '13-2', type: 'app', title: 'Dribbble', icon: 'D', url: 'https://dribbble.com', description: '设计灵感', accent: 'from-rose-300/90 to-pink-200/75' },
            { id: '13-3', type: 'app', title: 'Pinterest', icon: 'P', url: 'https://pinterest.com', description: '素材收藏', accent: 'from-red-300/90 to-orange-200/75' },
          ],
        },
      ],
    },
  ]
}

function reorder<T>(list: T[], oldIndex: number, newIndex: number) {
  const next = [...list]
  const [moved] = next.splice(oldIndex, 1)
  if (moved === undefined)
    return next
  next.splice(newIndex, 0, moved)
  return next
}

export function useNewtabLayout() {
  const pages = useStorage<GridPage[]>('newtab-layout', createMockPages())
  const activePageId = useStorage<string>('newtab-active-page', pages.value[0]?.pageId || 'page-1')
  const searchTerm = useStorage('newtab-search-term', '')

  const activePage = computed(() => {
    return pages.value.find(page => page.pageId === activePageId.value) ?? pages.value[0]
  })

  const visibleItems = computed(() => {
    const page = activePage.value
    if (!page)
      return []

    const keyword = searchTerm.value.trim().toLowerCase()
    if (!keyword)
      return page.items

    return page.items.filter((item) => {
      if (item.type === 'folder')
        return item.title.toLowerCase().includes(keyword) || item.children.some(child => child.title.toLowerCase().includes(keyword))

      return item.title.toLowerCase().includes(keyword)
    })
  })

  function setActivePage(pageId: string) {
    activePageId.value = pageId
  }

  function reorderActivePage(oldIndex: number, newIndex: number) {
    const page = activePage.value
    if (!page)
      return

    const pageIndex = pages.value.findIndex(item => item.pageId === page.pageId)
    if (pageIndex < 0)
      return

    const nextPages = [...pages.value]
    nextPages[pageIndex] = {
      ...page,
      items: reorder(page.items, oldIndex, newIndex),
    }
    pages.value = nextPages
  }

  return {
    activePage,
    activePageId,
    pages,
    searchTerm,
    setActivePage,
    reorderActivePage,
    visibleItems,
  }
}
