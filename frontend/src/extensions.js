// Custom TipTap nodes for django-templates-pro.
//
// The HTML these nodes render IS the contract with the Python compiler
// (src/templates_pro/core/compiler.py). Change both together.

import { Node, Extension, mergeAttributes } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { TableRow } from '@tiptap/extension-table'

const safeJSON = (raw) => {
  if (!raw) return null
  try {
    const v = JSON.parse(raw)
    return v && typeof v === 'object' ? v : null
  } catch (e) {
    return null
  }
}

const fmtAttr = {
  default: null,
  parseHTML: (el) => safeJSON(el.getAttribute('data-format')),
  renderHTML: (a) => (a.format && Object.keys(a.format).length ? { 'data-format': JSON.stringify(a.format) } : {}),
}
const labelAttr = {
  default: '',
  parseHTML: (el) => (el.textContent || '').trim(),
  renderHTML: () => ({}),
}

function chipNode({ name, kind, keyAttr, keyData }) {
  return Node.create({
    name,
    group: 'inline',
    inline: true,
    atom: true,
    selectable: true,
    draggable: true,

    addOptions() {
      return { ctx: null }
    },

    addAttributes() {
      return {
        [keyAttr]: {
          default: '',
          parseHTML: (el) => el.getAttribute(keyData) || '',
          renderHTML: (a) => ({ [keyData]: a[keyAttr] }),
        },
        format: fmtAttr,
        label: labelAttr,
      }
    },

    parseHTML() {
      return [{ tag: `span[data-tp="${kind}"]` }]
    },

    renderHTML({ node, HTMLAttributes }) {
      return ['span', mergeAttributes({ 'data-tp': kind }, HTMLAttributes), node.attrs.label || node.attrs[keyAttr]]
    },

    renderText({ node }) {
      return `{${node.attrs.label || node.attrs[keyAttr]}}`
    },

    addNodeView() {
      const ctx = this.options.ctx
      return ({ node, getPos, editor }) => {
        const dom = document.createElement('span')
        dom.contentEditable = 'false'
        let current = node
        const view = {
          refresh() {
            const info = ctx ? ctx.describeChip(kind, current, getPos()) : { label: current.attrs.label }
            dom.className = `tp-chip tp-chip--${kind}` + (info.invalid ? ' tp-chip--invalid' : '')
            dom.title = info.title || ''
            dom.innerHTML = ''
            const icon = document.createElement('span')
            icon.className = 'tp-chip__icon'
            icon.textContent = { var: '{ }', const: '◆', dynamic: '⏱' }[kind]
            const text = document.createElement('span')
            text.className = 'tp-chip__label'
            text.textContent = info.label
            dom.append(icon, text)
            if (info.formatHint) {
              const hint = document.createElement('span')
              hint.className = 'tp-chip__hint'
              hint.textContent = info.formatHint
              dom.append(hint)
            }
          },
        }
        dom.addEventListener('mousedown', (e) => e.preventDefault())
        dom.addEventListener('click', (e) => {
          e.preventDefault()
          if (ctx && editor.isEditable) ctx.openChipPopover(kind, getPos(), dom)
        })
        view.refresh()
        ctx && ctx.chipViews.add(view)
        return {
          dom,
          update(updated) {
            if (updated.type !== current.type) return false
            const changed = updated.attrs !== current.attrs && JSON.stringify(updated.attrs) !== JSON.stringify(current.attrs)
            current = updated
            // Re-render only on real changes: rebuilding the DOM on every selection
            // change would swallow clicks on the chip.
            if (changed) view.refresh()
            return true
          },
          destroy() {
            ctx && ctx.chipViews.delete(view)
          },
          ignoreMutation: () => true,
        }
      }
    },
  })
}

export const TpVariable = chipNode({ name: 'tpVariable', kind: 'var', keyAttr: 'path', keyData: 'data-path' })
export const TpConstant = chipNode({ name: 'tpConstant', kind: 'const', keyAttr: 'key', keyData: 'data-key' })
export const TpDynamic = chipNode({ name: 'tpDynamic', kind: 'dynamic', keyAttr: 'key', keyData: 'data-key' })

export const TpBlock = Node.create({
  name: 'tpBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  addOptions() {
    return { ctx: null }
  },

  addAttributes() {
    return {
      slug: {
        default: '',
        parseHTML: (el) => el.getAttribute('data-slug') || '',
        renderHTML: (a) => ({ 'data-slug': a.slug }),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-tp="block"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-tp': 'block' }, HTMLAttributes)]
  },

  addNodeView() {
    const ctx = this.options.ctx
    return ({ node, getPos, editor }) => {
      const dom = document.createElement('div')
      dom.contentEditable = 'false'
      let current = node
      const view = {
        refresh() {
          const block = ctx ? ctx.findBlock(current.attrs.slug) : null
          dom.className = 'tp-blocknode' + (block ? '' : ' tp-blocknode--missing')
          dom.innerHTML = ''
          const bar = document.createElement('div')
          bar.className = 'tp-blocknode__bar'
          const title = document.createElement('span')
          title.className = 'tp-blocknode__title'
          title.textContent = block ? `Shared block: ${block.name}` : `Missing block: ${current.attrs.slug}`
          const note = document.createElement('span')
          note.className = 'tp-blocknode__note'
          note.textContent = block ? 'edit it under Blocks; changes apply everywhere' : 'create it or remove this'
          const actions = document.createElement('span')
          actions.className = 'tp-blocknode__actions'
          if (ctx && editor.isEditable) {
            const change = ctx.smallButton('Change', () => ctx.openPicker({ tab: 'blocks', replacePos: getPos() }))
            const remove = ctx.smallButton('Remove', () => {
              const pos = getPos()
              editor.chain().focus().deleteRange({ from: pos, to: pos + current.nodeSize }).run()
            })
            actions.append(change, remove)
          }
          bar.append(title, note, actions)
          const body = document.createElement('div')
          body.className = 'tp-blocknode__preview'
          if (block) body.innerHTML = block.html || '<p><em>(empty block)</em></p>'
          dom.append(bar, body)
        },
      }
      view.refresh()
      ctx && ctx.chipViews.add(view)
      return {
        dom,
        update(updated) {
          if (updated.type !== current.type) return false
          const changed = JSON.stringify(updated.attrs) !== JSON.stringify(current.attrs)
          current = updated
          if (changed) view.refresh()
          return true
        },
        destroy() {
          ctx && ctx.chipViews.delete(view)
        },
        stopEvent: (e) => e.target.closest && !!e.target.closest('button'),
        ignoreMutation: () => true,
      }
    }
  },
})

function sectionNode({ name, kind, attrs, describe }) {
  return Node.create({
    name,
    group: 'block',
    content: 'block+',
    defining: true,

    addOptions() {
      return { ctx: null }
    },

    addAttributes() {
      const out = {}
      for (const [attr, data, dflt] of attrs) {
        out[attr] = {
          default: dflt,
          parseHTML: (el) => el.getAttribute(data) ?? dflt,
          renderHTML: (a) => ({ [data]: a[attr] }),
        }
      }
      return out
    },

    parseHTML() {
      return [{ tag: `div[data-tp="${kind}"]` }]
    },

    renderHTML({ HTMLAttributes }) {
      return ['div', mergeAttributes({ 'data-tp': kind }, HTMLAttributes), 0]
    },

    addNodeView() {
      const ctx = this.options.ctx
      return ({ node, getPos, editor }) => {
        const dom = document.createElement('div')
        dom.className = `tp-section tp-section--${kind}`
        const bar = document.createElement('div')
        bar.className = 'tp-section__bar'
        bar.contentEditable = 'false'
        const content = document.createElement('div')
        content.className = 'tp-section__content'
        dom.append(bar, content)
        let current = node
        const view = {
          refresh() {
            const info = ctx ? describe(ctx, current, getPos()) : { text: kind }
            bar.innerHTML = ''
            dom.classList.toggle('tp-section--invalid', !!info.invalid)
            const label = document.createElement('span')
            label.className = 'tp-section__label'
            label.textContent = info.text
            bar.append(label)
            if (ctx && editor.isEditable) {
              const actions = document.createElement('span')
              actions.className = 'tp-section__actions'
              actions.append(
                ctx.smallButton('Edit', () => ctx.editSection(kind, getPos())),
                ctx.smallButton('Unwrap', () => ctx.unwrapSection(getPos())),
              )
              bar.append(actions)
            }
          },
        }
        view.refresh()
        ctx && ctx.chipViews.add(view)
        return {
          dom,
          contentDOM: content,
          update(updated) {
            if (updated.type !== current.type) return false
            const changed = updated.attrs !== current.attrs && JSON.stringify(updated.attrs) !== JSON.stringify(current.attrs)
            current = updated
            // Re-render only on real changes: rebuilding the DOM on every selection
            // change would swallow clicks on the chip.
            if (changed) view.refresh()
            return true
          },
          destroy() {
            ctx && ctx.chipViews.delete(view)
          },
          stopEvent: (e) => bar.contains(e.target),
          ignoreMutation: (m) => bar.contains(m.target),
        }
      }
    },
  })
}

export const TpRepeat = sectionNode({
  name: 'tpRepeat',
  kind: 'repeat',
  attrs: [
    ['path', 'data-path', ''],
    ['as', 'data-as', 'item'],
  ],
  describe: (ctx, node, pos) => ctx.describeRepeat(node.attrs.path, node.attrs.as, pos),
})

export const TpIf = sectionNode({
  name: 'tpIf',
  kind: 'if',
  attrs: [
    ['path', 'data-path', ''],
    ['op', 'data-op', 'truthy'],
    ['value', 'data-value', ''],
  ],
  describe: (ctx, node, pos) => ctx.describeCondition(node.attrs, pos),
})

// Table rows can repeat for each item of a list.
export const TpTableRow = TableRow.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      repeat: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-tp-repeat'),
        renderHTML: (a) => (a.repeat ? { 'data-tp-repeat': a.repeat, 'data-tp-as': a.as || 'item' } : {}),
      },
      as: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-tp-as'),
        renderHTML: () => ({}),
      },
    }
  },
})

// Typing "{{" opens the insert picker.
export const BraceTrigger = Extension.create({
  name: 'tpBraceTrigger',
  addOptions() {
    return { ctx: null }
  },
  addProseMirrorPlugins() {
    const ctx = this.options.ctx
    return [
      new Plugin({
        key: new PluginKey('tpBraceTrigger'),
        props: {
          handleTextInput(view, from, to, text) {
            if (text !== '{' || !ctx) return false
            const before = view.state.doc.textBetween(Math.max(0, from - 1), from, '\n', '\n')
            if (before !== '{') return false
            view.dispatch(view.state.tr.delete(from - 1, to))
            ctx.openPicker({})
            return true
          },
        },
      }),
    ]
  },
})
