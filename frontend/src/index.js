// Entry point: auto-initialises every [data-tp-editor] element on the page,
// including ones added later (Django admin inlines, HTMX swaps...).
import './editor.css'
import { TemplateEditor, PRESETS } from './editor.js'

const instances = new WeakMap()

export function init(root, config) {
  if (instances.has(root)) return instances.get(root)
  if (!config) {
    const id = root.getAttribute('data-tp-config')
    const script = id && document.getElementById(id)
    config = script ? JSON.parse(script.textContent) : {}
  }
  const editor = new TemplateEditor(root, config)
  instances.set(root, editor)
  root.templatesPro = editor
  return editor
}

export function initAll(scope = document) {
  scope.querySelectorAll('[data-tp-editor]').forEach((root) => {
    // Skip Django admin empty-form templates (__prefix__).
    const ta = root.querySelector('textarea')
    if (ta && ta.name && ta.name.includes('__prefix__')) return
    init(root)
  })
}

export function get(root) {
  return instances.get(root) || null
}

export { TemplateEditor, PRESETS }

if (typeof document !== 'undefined') {
  const start = () => {
    initAll()
    new MutationObserver((muts) => {
      for (const m of muts) for (const n of m.addedNodes) if (n.nodeType === 1) {
        if (n.matches && n.matches('[data-tp-editor]')) initAll(n.parentNode)
        else if (n.querySelector && n.querySelector('[data-tp-editor]')) initAll(n)
      }
    }).observe(document.body, { childList: true, subtree: true })
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start)
  else start()
}
