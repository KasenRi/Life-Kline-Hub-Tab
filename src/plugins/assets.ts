import 'katex/dist/katex.min.css'
import '@/styles/lib/tailwind.css'
import '@/styles/lib/highlight.less'
import '@/styles/lib/github-markdown.less'
import '@/styles/global.less'

/** Tailwind's Preflight Style Override */
function naiveStyleOverride() {
  const meta = document.createElement('meta')
  meta.name = 'naive-ui-style'
  document.head.appendChild(meta)
}

function setupCustomAssets() {
  const cssHref = new URL('./custom/index.css', window.location.href).toString()
  const jsSrc = new URL('./custom/index.js', window.location.href).toString()

  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = cssHref
  document.head.appendChild(link)

  const script = document.createElement('script')
  script.src = jsSrc
  document.body.appendChild(script)
}

function setupAssets() {
  naiveStyleOverride()
  setupCustomAssets()
}

export default setupAssets
