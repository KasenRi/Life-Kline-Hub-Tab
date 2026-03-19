import browser from 'webextension-polyfill'

browser.runtime.onInstalled.addListener(() => {
  // Keep the service worker lightweight for the static new tab scaffold.
  return undefined
})
