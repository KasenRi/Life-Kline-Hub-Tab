import { addMultiple, getListByGroupId } from '@/api/panel/itemIcon'
import { deletes as deleteCloudGroups, edit as editCloudGroup, getList as getCloudGroups } from '@/api/panel/itemIconGroup'
import { get as getUserConfig, set as setUserConfig } from '@/api/panel/userConfig'
import { defaultStatePanelConfig } from '@/store/modules/panel/helper'
import { getLocalItemGroups, getLocalItemsByGroupId, replaceLocalLayout } from './panelData'

const ITEM_BATCH_SIZE = 50
type CloudSyncResult = {
  code: number
  msg: string
  data: {
    panel: Panel.panelConfig
  }
}

function buildResult(code: number, msg: string, panel: Panel.panelConfig): CloudSyncResult {
  return {
    code,
    msg,
    data: { panel },
  }
}

export async function pushLocalLayoutToCloud(panelConfig: Panel.panelConfig): Promise<CloudSyncResult> {
  const configResponse = await setUserConfig({ panel: panelConfig })
  if (configResponse.code !== 0)
    return buildResult(configResponse.code, configResponse.msg, panelConfig)

  const cloudGroupsResponse = await getCloudGroups<Common.ListResponse<Panel.ItemIconGroup[]>>()
  if (cloudGroupsResponse.code !== 0)
    return buildResult(cloudGroupsResponse.code, cloudGroupsResponse.msg, panelConfig)

  const cloudGroupIds = cloudGroupsResponse.data.list.map(group => group.id).filter(Boolean) as number[]
  if (cloudGroupIds.length > 0) {
    const deleteResponse = await deleteCloudGroups(cloudGroupIds)
    if (deleteResponse.code !== 0)
      return buildResult(deleteResponse.code, deleteResponse.msg, panelConfig)
  }

  const localGroups = await getLocalItemGroups()
  for (const localGroup of localGroups) {
    const createGroupResponse = await editCloudGroup<Panel.ItemIconGroup>({
      title: localGroup.title,
      sort: localGroup.sort,
      icon: localGroup.icon,
    })
    if (createGroupResponse.code !== 0)
      return buildResult(createGroupResponse.code, createGroupResponse.msg, panelConfig)

    const cloudGroupId = createGroupResponse.data.id
    if (!cloudGroupId)
      continue

    const localItems = await getLocalItemsByGroupId(localGroup.id)
    for (let index = 0; index < localItems.length; index += ITEM_BATCH_SIZE) {
      const batch = localItems.slice(index, index + ITEM_BATCH_SIZE).map(item => ({
        ...item,
        id: undefined,
        itemIconGroupId: cloudGroupId,
      }))
      const addResponse = await addMultiple(batch)
      if (addResponse.code !== 0)
        return buildResult(addResponse.code, addResponse.msg, panelConfig)
    }
  }

  return buildResult(0, configResponse.msg, panelConfig)
}

export async function pullCloudLayoutToLocal(): Promise<CloudSyncResult> {
  const configResponse = await getUserConfig<Panel.userConfig>()
  if (configResponse.code !== 0)
    return buildResult(configResponse.code, configResponse.msg, defaultStatePanelConfig())

  const cloudGroupsResponse = await getCloudGroups<Common.ListResponse<Panel.ItemIconGroup[]>>()
  if (cloudGroupsResponse.code !== 0)
    return buildResult(cloudGroupsResponse.code, cloudGroupsResponse.msg, configResponse.data.panel)

  const itemMap: Record<number, Panel.ItemInfo[]> = {}
  for (const group of cloudGroupsResponse.data.list) {
    if (!group.id)
      continue

    const itemsResponse = await getListByGroupId<Common.ListResponse<Panel.ItemInfo[]>>(group.id)
    if (itemsResponse.code !== 0)
      return buildResult(itemsResponse.code, itemsResponse.msg, configResponse.data.panel)

    itemMap[group.id] = itemsResponse.data.list.map(item => ({
      ...item,
      itemIconGroupId: group.id,
    }))
  }

  await replaceLocalLayout(cloudGroupsResponse.data.list, itemMap)
  return buildResult(0, configResponse.msg, configResponse.data.panel)
}
