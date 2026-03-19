import { getExtensionStorageValue, setExtensionStorageValue } from '@/utils/storage'

const ITEM_GROUPS_KEY = 'localFirst.itemGroups'
const ITEM_MAP_KEY = 'localFirst.itemMap'
const LOCAL_ASSETS_KEY = 'localFirst.assets'

interface LocalItemMap {
  [groupId: number]: Panel.ItemInfo[]
}

export interface LocalAsset extends File.Info {
  localOnly: true
}

function buildLocalId(): number {
  return Date.now() + Math.floor(Math.random() * 10000)
}

function now() {
  return new Date().toISOString()
}

function sortBySort<T extends { sort?: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => (a.sort ?? Number.MAX_SAFE_INTEGER) - (b.sort ?? Number.MAX_SAFE_INTEGER))
}

function normalizeGroup(group: Panel.ItemIconGroup, index: number): Panel.ItemIconGroup {
  return {
    ...group,
    id: group.id ?? buildLocalId(),
    title: group.title || 'APP',
    sort: group.sort ?? index + 1,
    createTime: group.createTime ?? now(),
    updateTime: now(),
  }
}

function normalizeItem(item: Panel.ItemInfo, groupId: number, index: number): Panel.ItemInfo {
  return {
    ...item,
    id: item.id ?? buildLocalId(),
    icon: item.icon ?? null,
    title: item.title,
    url: item.url,
    lanUrl: item.lanUrl ?? '',
    description: item.description ?? '',
    openMethod: item.openMethod ?? 2,
    itemIconGroupId: item.itemIconGroupId ?? groupId,
    sort: item.sort ?? index + 1,
    createTime: item.createTime ?? now(),
    updateTime: now(),
  }
}

async function getStoredGroups(): Promise<Panel.ItemIconGroup[]> {
  const groups = await getExtensionStorageValue<Panel.ItemIconGroup[]>(ITEM_GROUPS_KEY)
  if (groups && groups.length > 0)
    return sortBySort(groups)

  const defaultGroup = normalizeGroup({ title: 'APP', sort: 1 }, 0)
  await setExtensionStorageValue(ITEM_GROUPS_KEY, [defaultGroup])
  return [defaultGroup]
}

async function setStoredGroups(groups: Panel.ItemIconGroup[]) {
  await setExtensionStorageValue(ITEM_GROUPS_KEY, sortBySort(groups))
}

async function getStoredItemMap(): Promise<LocalItemMap> {
  return (await getExtensionStorageValue<LocalItemMap>(ITEM_MAP_KEY)) ?? {}
}

async function setStoredItemMap(itemMap: LocalItemMap) {
  await setExtensionStorageValue(ITEM_MAP_KEY, itemMap)
}

export async function getLocalItemGroups(): Promise<Panel.ItemIconGroup[]> {
  return await getStoredGroups()
}

export async function saveLocalItemGroup(group: Panel.ItemIconGroup): Promise<Panel.ItemIconGroup> {
  const groups = await getStoredGroups()
  const existingIndex = groups.findIndex(item => item.id === group.id)

  if (existingIndex >= 0)
    groups[existingIndex] = normalizeGroup({ ...groups[existingIndex], ...group }, existingIndex)
  else
    groups.push(normalizeGroup(group, groups.length))

  const savedGroups = sortBySort(groups).map((item, index) => ({ ...item, sort: index + 1, updateTime: now() }))
  await setStoredGroups(savedGroups)
  return savedGroups.find(item => item.id === (group.id ?? savedGroups[savedGroups.length - 1].id)) ?? savedGroups[savedGroups.length - 1]
}

export async function deleteLocalItemGroups(ids: number[]) {
  const groups = await getStoredGroups()
  const nextGroups = groups.filter(group => !ids.includes(group.id as number)).map((group, index) => ({
    ...group,
    sort: index + 1,
    updateTime: now(),
  }))
  await setStoredGroups(nextGroups.length > 0 ? nextGroups : [normalizeGroup({ title: 'APP', sort: 1 }, 0)])

  const itemMap = await getStoredItemMap()
  ids.forEach((id) => {
    delete itemMap[id]
  })
  await setStoredItemMap(itemMap)
}

export async function saveLocalItemGroupSort(sortItems: Common.SortItemRequest[]) {
  const groups = await getStoredGroups()
  const sortMap = new Map(sortItems.map(item => [item.id, item.sort]))
  const nextGroups = groups.map((group, index) => ({
    ...group,
    sort: sortMap.get(group.id as number) ?? index + 1,
    updateTime: now(),
  }))
  await setStoredGroups(nextGroups)
}

export async function getLocalItemsByGroupId(groupId: number | undefined): Promise<Panel.ItemInfo[]> {
  if (!groupId)
    return []

  const itemMap = await getStoredItemMap()
  return sortBySort(itemMap[groupId] ?? []).map((item, index) => normalizeItem(item, groupId, index))
}

export async function saveLocalItem(item: Panel.ItemInfo): Promise<Panel.ItemInfo> {
  const groups = await getStoredGroups()
  let targetGroupId = item.itemIconGroupId

  if (!targetGroupId) {
    const firstGroup = groups[0] ?? await saveLocalItemGroup({ title: 'APP' })
    targetGroupId = firstGroup.id
  }

  const itemMap = await getStoredItemMap()
  const nextItem = normalizeItem(item, targetGroupId as number, (itemMap[targetGroupId as number] ?? []).length)
  const previousGroupId = Object.keys(itemMap)
    .map(id => Number(id))
    .find(groupId => (itemMap[groupId] ?? []).some(currentItem => currentItem.id === item.id))

  if (previousGroupId && previousGroupId !== targetGroupId)
    itemMap[previousGroupId] = (itemMap[previousGroupId] ?? []).filter(currentItem => currentItem.id !== item.id)

  const currentItems = (itemMap[targetGroupId as number] ?? []).filter(currentItem => currentItem.id !== item.id)
  currentItems.push(nextItem)
  itemMap[targetGroupId as number] = sortBySort(currentItems).map((currentItem, index) => ({
    ...currentItem,
    itemIconGroupId: targetGroupId,
    sort: index + 1,
    updateTime: now(),
  }))

  await setStoredItemMap(itemMap)
  return itemMap[targetGroupId as number].find(currentItem => currentItem.id === nextItem.id) as Panel.ItemInfo
}

export async function addLocalItems(items: Panel.ItemInfo[]) {
  const savedItems: Panel.ItemInfo[] = []
  for (const item of items)
    savedItems.push(await saveLocalItem(item))
  return savedItems
}

export async function deleteLocalItems(ids: number[]) {
  const itemMap = await getStoredItemMap()
  for (const [groupId, items] of Object.entries(itemMap) as [string, Panel.ItemInfo[]][]) {
    itemMap[Number(groupId)] = items
      .filter((item: Panel.ItemInfo) => !ids.includes(item.id as number))
      .map((item: Panel.ItemInfo, index: number) => ({
        ...item,
        sort: index + 1,
        updateTime: now(),
      }))
  }

  await setStoredItemMap(itemMap)
}

export async function saveLocalItemSort(data: Panel.ItemIconSortRequest) {
  const itemMap = await getStoredItemMap()
  const currentItems = itemMap[data.itemIconGroupId] ?? []
  const sortMap = new Map(data.sortItems.map(item => [item.id, item.sort]))
  itemMap[data.itemIconGroupId] = currentItems.map((item, index) => ({
    ...item,
    sort: sortMap.get(item.id as number) ?? index + 1,
    updateTime: now(),
  }))

  await setStoredItemMap(itemMap)
}

export async function replaceLocalLayout(groups: Panel.ItemIconGroup[], itemMap: LocalItemMap) {
  const normalizedGroups = sortBySort(groups).map((group, index) => normalizeGroup(group, index))
  const nextItemMap: LocalItemMap = {}

  for (const group of normalizedGroups) {
    const groupId = group.id as number
    nextItemMap[groupId] = sortBySort(itemMap[groupId] ?? []).map((item, index) => normalizeItem({
      ...item,
      itemIconGroupId: groupId,
    }, groupId, index))
  }

  if (normalizedGroups.length === 0) {
    const defaultGroup = normalizeGroup({ title: 'APP', sort: 1 }, 0)
    await setStoredGroups([defaultGroup])
    await setStoredItemMap({})
    return
  }

  await setStoredGroups(normalizedGroups)
  await setStoredItemMap(nextItemMap)
}

function normalizePreviewUrl(rawUrl: string) {
  if (/^[a-z][a-z\d+.-]*:\/\//i.test(rawUrl))
    return rawUrl

  return `https://${rawUrl}`
}

export function resolveFaviconFallbackUrl(rawUrl: string) {
  const normalizedUrl = normalizePreviewUrl(rawUrl)
  if (typeof window !== 'undefined' && (window.location.protocol === 'chrome-extension:' || window.location.protocol === 'moz-extension:')) {
    const pageUrl = encodeURIComponent(normalizedUrl)
    return `${window.location.origin}/_favicon/?pageUrl=${pageUrl}&size=128`
  }

  return `https://www.google.com/s2/favicons?sz=128&domain_url=${encodeURIComponent(normalizedUrl)}`
}

function resolveAbsoluteUrl(baseUrl: string, maybeRelativeUrl: string) {
  if (maybeRelativeUrl.startsWith('//')) {
    const { protocol } = new URL(baseUrl)
    return `${protocol}${maybeRelativeUrl}`
  }

  return new URL(maybeRelativeUrl, baseUrl).toString()
}

function extractCandidateScore(link: HTMLLinkElement) {
  const rel = (link.getAttribute('rel') || '').toLowerCase()
  const sizes = link.getAttribute('sizes') || ''
  const maxSize = sizes.split(/\s+/).reduce((result, item) => {
    const [width] = item.split('x')
    const parsedWidth = Number(width)
    return Number.isFinite(parsedWidth) ? Math.max(result, parsedWidth) : result
  }, 0)

  let score = maxSize
  if (rel.includes('apple-touch-icon'))
    score += 1000
  else if (rel.includes('icon'))
    score += 100

  return score
}

async function findSiteIconCandidates(rawUrl: string) {
  const normalizedUrl = normalizePreviewUrl(rawUrl)
  const response = await fetch(normalizedUrl)
  if (!response.ok)
    throw new Error(`fetch page failed: ${response.status}`)

  const html = await response.text()
  const doc = new DOMParser().parseFromString(html, 'text/html')
  const links = Array.from(doc.querySelectorAll('link'))
    .filter((link) => {
      const rel = (link.getAttribute('rel') || '').toLowerCase()
      return rel.includes('icon')
    })
    .map((link) => ({
      href: link.getAttribute('href') || '',
      score: extractCandidateScore(link),
    }))
    .filter(link => Boolean(link.href))
    .sort((a, b) => b.score - a.score)
    .map(link => resolveAbsoluteUrl(normalizedUrl, link.href))

  const defaultFavicon = `${new URL(normalizedUrl).origin}/favicon.ico`
  return Array.from(new Set([...links, defaultFavicon]))
}

async function blobToDataUrl(blob: Blob): Promise<string> {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(new Error('blob to data url failed'))
    reader.readAsDataURL(blob)
  })
}

async function downloadImageAsDataUrl(url: string) {
  const response = await fetch(url)
  if (!response.ok)
    throw new Error(`fetch image failed: ${response.status}`)

  const blob = await response.blob()
  if (!blob.type.startsWith('image/'))
    throw new Error(`invalid image type: ${blob.type}`)

  return await blobToDataUrl(blob)
}

export async function buildLocalFaviconUrl(rawUrl: string) {
  try {
    const candidates = await findSiteIconCandidates(rawUrl)
    for (const candidate of candidates) {
      try {
        return await downloadImageAsDataUrl(candidate)
      }
      catch {
        // Try the next candidate until one of the icons is reachable.
      }
    }
  }
  catch {
    // Fall back to the browser-provided favicon service below.
  }

  return resolveFaviconFallbackUrl(rawUrl)
}

function getFileExtension(file: globalThis.File): string {
  const name = file.name || ''
  const ext = name.includes('.') ? name.split('.').pop() : ''
  return ext?.toLowerCase() || 'png'
}

export async function fileToDataUrl(file: globalThis.File): Promise<string> {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(new Error('read file failed'))
    reader.readAsDataURL(file)
  })
}

export async function saveLocalAsset(file: globalThis.File): Promise<LocalAsset> {
  const src = await fileToDataUrl(file)
  const assets = (await getExtensionStorageValue<LocalAsset[]>(LOCAL_ASSETS_KEY)) ?? []
  const asset: LocalAsset = {
    id: buildLocalId(),
    src,
    fileName: file.name,
    ext: getFileExtension(file),
    method: 0,
    userId: 0,
    createTime: now(),
    updateTime: now(),
    localOnly: true,
  }

  assets.unshift(asset)
  await setExtensionStorageValue(LOCAL_ASSETS_KEY, assets)
  return asset
}

export async function getLocalAssets(): Promise<LocalAsset[]> {
  return (await getExtensionStorageValue<LocalAsset[]>(LOCAL_ASSETS_KEY)) ?? []
}

export async function deleteLocalAssets(ids: number[]) {
  const assets = await getLocalAssets()
  await setExtensionStorageValue(LOCAL_ASSETS_KEY, assets.filter(asset => !ids.includes(asset.id as number)))
}
