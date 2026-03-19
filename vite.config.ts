import path from 'path'
import { writeFileSync } from 'fs'
import type { PluginOption } from 'vite'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { createSvgIconsPlugin } from 'vite-plugin-svg-icons'

const EXTENSION_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwx4Yt0yMsRcnWJV9nPHPoa81MAMc+oXjz7LUVNRaySliIc8eym9KgGBuO6CKSBXFPLbV3pEGb+jMkhnOfIKc/MVQlsb4Qx4cTSbPTo3gb9WDV+HDDQmvhPmYC3g9sO34jl/1UH6PpB/RAyWKh07XTubWo3oJTxBBAZXK263X0JNk4W8rEYUSETe4ZYEDG9UIYRNku6/myBda4jJpH4/C3uBkZWWRQaR0uWuN33y1ZNKr7p1DvP/n3d5nR75uak0/IZ+imomvI6k4d7egC1IXDWyNMB/foVsxaGuEJMemHAqa2Muwt6TcO7Hv7klWvAUJJNArLOcHjipQXC3uLZTw3wIDAQAB'

function getExtensionVersion(versionTag: string) {
  const match = versionTag.match(/^(\d{4})(\d{2})(\d{2})$/)
  if (!match)
    return '0.1.0'

  const [, year, month, day] = match
  return `${Number(year)}.${Number(month)}.${Number(day)}.0`
}

function getHostPermissions(apiBaseUrl: string) {
  const baseUrl = new URL(apiBaseUrl)
  const origins = new Set<string>([
    `${baseUrl.origin}/*`,
  ])

  if (baseUrl.hostname === '127.0.0.1')
    origins.add(`${baseUrl.protocol}//localhost:${baseUrl.port}/*`)

  if (baseUrl.hostname === 'localhost')
    origins.add(`${baseUrl.protocol}//127.0.0.1:${baseUrl.port}/*`)

  return Array.from(origins)
}

function createExtensionManifestPlugin(env: ImportMetaEnv): PluginOption {
  const hostPermissions = getHostPermissions(env.VITE_APP_API_BASE_URL)
  const connectOrigins = hostPermissions.map(pattern => pattern.replace(/\/\*$/, ''))

  return {
    name: 'mv3-manifest',
    closeBundle() {
      const manifest = {
        manifest_version: 3,
        name: 'LKTab',
        short_name: 'LKTab',
        description: 'Local-first new tab dashboard with optional local backend sync.',
        key: EXTENSION_PUBLIC_KEY,
        version: getExtensionVersion(env.VITE_APP_VERSION || ''),
        version_name: env.VITE_APP_VERSION || 'dev',
        icons: {
          16: 'favicon.ico',
          32: 'favicon.ico',
          48: 'logo.png',
          128: 'logo.png',
        },
        permissions: ['storage'],
        host_permissions: hostPermissions,
        chrome_url_overrides: {
          newtab: 'index.html',
        },
        action: {
          default_title: 'LKTab',
        },
        content_security_policy: {
          extension_pages: `script-src 'self'; object-src 'self'; img-src 'self' data: blob: http: https:; style-src 'self' 'unsafe-inline'; connect-src 'self' ${connectOrigins.join(' ')};`,
        },
      }

      writeFileSync(path.resolve(process.cwd(), 'dist', 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf-8')
    },
  }
}

function setupPlugins(env: ImportMetaEnv): PluginOption[] {
  return [
    vue(),
    createExtensionManifestPlugin(env),
    env.VITE_GLOB_APP_PWA === 'true' && VitePWA({
      injectRegister: 'auto',
      manifest: {
        name: 'Sun-Panel',
        short_name: 'Sun-Panel',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
    createSvgIconsPlugin({
      iconDirs: [path.resolve(process.cwd(), 'src/assets/svg-icons')],
      symbolId: '[name]',
    }),
  ]
}

export default defineConfig((env) => {
  const viteEnv = loadEnv(env.mode, process.cwd()) as unknown as ImportMetaEnv

  return {
    base: './',
    resolve: {
      alias: {
        '@': path.resolve(process.cwd(), 'src'),
      },
    },
    plugins: setupPlugins(viteEnv),
    server: {
      host: '0.0.0.0',
      port: 1002,
      open: false,
      proxy: {
        '/api': {
          target: viteEnv.VITE_APP_API_BASE_URL,
          changeOrigin: true, // 允许跨域
          rewrite: path => path.replace('/api/', '/api/'),
        },
        '/uploads': {
          target: viteEnv.VITE_APP_API_BASE_URL,
          changeOrigin: true, // 允许跨域
          rewrite: path => path.replace('/uploads/', '/uploads/'),
        },
      },
    },
    build: {
      minify: 'terser',
      reportCompressedSize: false,
      sourcemap: false,
      commonjsOptions: {
        ignoreTryCatch: false,
      },
      terserOptions: {
        compress: {
          drop_console: true,
        },
      },
    },
  }
})
