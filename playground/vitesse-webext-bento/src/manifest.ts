import fs from 'fs-extra'
import type { Manifest } from 'webextension-polyfill'
import type PkgType from '../package.json'
import { isDev, port, r } from '../scripts/utils'

const EXTENSION_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArV0WL8TxGXuaQIo+HwNF0kPTmle+pUwRBuO9ioUBEQ0E+OxtzKbMD4PbD92iNdRxlzt6Vx0WWIYSxL5JAkb+6AsqTh6qDUCVZSr0Ir30O7T4ZftnaG2ZAuLVsxJJciFXd3DJiy73uXOxZ3hWm+thjPPThEu7acZyXpzATnB0uWWWlR4aa2riYrVIbIx9HMK9mB201bp0OACLlvaQHTCqUlj5TD5UiXzPQ2LxCeDz0kTR4GKBJ1gXiz3gMI11QhAPS3QdjFVPZAZyEciMLBrYGZZdurcswKqmpcejIvWvZ/nVzFApTVHhU3gMrrlQaOe/mE5GNzCBb8DGpVcMcIOjtQIDAQAB'

export async function getManifest() {
  const pkg = await fs.readJSON(r('package.json')) as typeof PkgType

  // update this file to update this manifest.json
  // can also be conditional based on your need
  const manifest: Manifest.WebExtensionManifest & { key?: string } = {
    manifest_version: 3,
    name: 'Bento New Tab',
    key: EXTENSION_PUBLIC_KEY,
    version: pkg.version,
    description: 'Sun-Panel inspired static new tab UI scaffold built with Vitesse WebExt, Vue 3 and Tailwind CSS.',
    action: {
      default_icon: 'assets/icon-512.png',
      default_popup: 'dist/popup/index.html',
    },
    options_ui: {
      page: 'dist/options/index.html',
      open_in_tab: true,
    },
    chrome_url_overrides: {
      newtab: 'dist/newtab/index.html',
    },
    background: {
      service_worker: 'dist/background/index.mjs',
    },
    icons: {
      16: 'assets/icon-512.png',
      48: 'assets/icon-512.png',
      128: 'assets/icon-512.png',
    },
    permissions: [
      'storage',
    ],
    content_security_policy: {
      extension_pages: isDev
        // this is required on dev for Vite script to load
        ? `script-src \'self\' http://localhost:${port}; object-src \'self\'`
        : 'script-src \'self\'; object-src \'self\'',
    },
  }

  return manifest
}
