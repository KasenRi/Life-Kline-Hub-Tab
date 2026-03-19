function isAbsoluteUrl(url: string) {
  return /^https?:\/\//i.test(url)
}

export function isExtensionRuntime() {
  return typeof window !== 'undefined'
    && (window.location.protocol === 'chrome-extension:' || window.location.protocol === 'moz-extension:')
}

export function resolveApiBaseURL() {
  const apiUrl = import.meta.env.VITE_GLOB_API_URL

  if (!isExtensionRuntime() || isAbsoluteUrl(apiUrl))
    return apiUrl

  const backendBase = import.meta.env.VITE_APP_API_BASE_URL
  return new URL('api/', backendBase).toString().replace(/\/$/, '')
}
