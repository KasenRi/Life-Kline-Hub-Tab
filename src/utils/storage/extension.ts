import { ss } from './local'

type ChromeStorageArea = {
  get: (keys: string | string[] | null, callback: (items: Record<string, any>) => void) => void
  set: (items: Record<string, any>, callback?: () => void) => void
  remove: (keys: string | string[], callback?: () => void) => void
}

function getChromeStorageArea(): ChromeStorageArea | null {
  const runtime = globalThis as typeof globalThis & {
    chrome?: {
      runtime?: { lastError?: Error }
      storage?: { local?: ChromeStorageArea }
    }
  }

  return runtime.chrome?.storage?.local ?? null
}

export async function getExtensionStorageValue<T>(key: string): Promise<T | undefined> {
  const storageArea = getChromeStorageArea()

  if (!storageArea)
    return ss.get(key)

  return await new Promise<T | undefined>((resolve) => {
    storageArea.get(key, (items) => {
      resolve(items[key] as T | undefined)
    })
  })
}

export async function setExtensionStorageValue<T>(key: string, value: T): Promise<void> {
  ss.set(key, value)

  const storageArea = getChromeStorageArea()
  if (!storageArea)
    return

  await new Promise<void>((resolve) => {
    storageArea.set({ [key]: value }, () => resolve())
  })
}

export async function removeExtensionStorageValue(key: string): Promise<void> {
  ss.remove(key)

  const storageArea = getChromeStorageArea()
  if (!storageArea)
    return

  await new Promise<void>((resolve) => {
    storageArea.remove(key, () => resolve())
  })
}
