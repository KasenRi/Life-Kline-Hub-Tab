import { ss } from './local'

interface ChromeStorageArea {
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

const STORAGE_TIMEOUT_MS = 400

function withTimeout<T>(task: Promise<T>, fallback: () => T): Promise<T> {
  return new Promise<T>((resolve) => {
    const timer = window.setTimeout(() => {
      resolve(fallback())
    }, STORAGE_TIMEOUT_MS)

    task.then((value) => {
      window.clearTimeout(timer)
      resolve(value)
    }).catch(() => {
      window.clearTimeout(timer)
      resolve(fallback())
    })
  })
}

export async function getExtensionStorageValue<T>(key: string): Promise<T | undefined> {
  const storageArea = getChromeStorageArea()

  if (!storageArea)
    return ss.get(key)

  return await withTimeout(
    new Promise<T | undefined>((resolve, reject) => {
      try {
        storageArea.get(key, (items) => {
          resolve(items[key] as T | undefined)
        })
      }
      catch (error) {
        reject(error)
      }
    }),
    () => ss.get(key),
  )
}

export async function setExtensionStorageValue<T>(key: string, value: T): Promise<void> {
  ss.set(key, value)

  const storageArea = getChromeStorageArea()
  if (!storageArea)
    return

  await withTimeout(
    new Promise<void>((resolve, reject) => {
      try {
        storageArea.set({ [key]: value }, () => resolve())
      }
      catch (error) {
        reject(error)
      }
    }),
    () => undefined,
  )
}

export async function removeExtensionStorageValue(key: string): Promise<void> {
  ss.remove(key)

  const storageArea = getChromeStorageArea()
  if (!storageArea)
    return

  await withTimeout(
    new Promise<void>((resolve, reject) => {
      try {
        storageArea.remove(key, () => resolve())
      }
      catch (error) {
        reject(error)
      }
    }),
    () => undefined,
  )
}
