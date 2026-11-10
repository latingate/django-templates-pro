import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import { TextStyle, Color, FontSize } from '@tiptap/extension-text-style'
import Highlight from '@tiptap/extension-highlight'
import Image from '@tiptap/extension-image'
import { Table, TableCell, TableHeader } from '@tiptap/extension-table'
import { Placeholder } from '@tiptap/extensions'
import BubbleMenu from '@tiptap/extension-bubble-menu'

import { TpVariable, TpConstant, TpDynamic, TpBlock, TpRepeat, TpIf, TpTableRow, BraceTrigger } from './extensions.js'
import { icons } from './icons.js'

export const PRESETS = {
  full: [
    'undo', 'redo', '|', 'blockType', 'fontSize', '|',
    'bold', 'italic', 'underline', 'strike', 'color', 'highlight', 'clear', '|',
    'alignLeft', 'alignCenter', 'alignRight', 'alignJustify', '|',
    'bulletList', 'orderedList', 'blockquote', 'hr', '|', 'link', 'image', 'table', '/',
    'variable', 'constant', 'dynamic', 'block', 'repeat', 'condition', '>', 'preview', 'fullscreen',
  ],
  simple: [
    'undo', 'redo', '|', 'blockType', '|', 'bold', 'italic', 'underline', '|',
    'alignLeft', 'alignCenter', 'alignRight', '|', 'bulletList', 'orderedList', '|', 'link', 'table', '|',
    'variable', 'constant', 'dynamic', 'block', '>', 'preview',
  ],
  minimal: ['insert', '>', 'preview'],
}

const KIND_FOR_TYPE = {
  string: 'text', text: 'text', email: 'text', url: 'text', integer: 'number', number: 'number',
  money: 'money', percent: 'percent', date: 'date', datetime: 'datetime', time: 'time', boolean: 'boolean',
}
const OP_LABELS = {
  truthy: 'has a value', falsy: 'is empty', eq: 'equals', ne: 'does not equal', gt: 'is greater than',
  gte: 'is at least', lt: 'is less than', lte: 'is at most', contains: 'contains',
}
const FONT_SIZES = ['8pt', '9pt', '10pt', '11pt', '12pt', '14pt', '16pt', '18pt', '20pt', '24pt', '28pt', '36pt']

const h = (tag, props = {}, ...children) => {
  const el = document.createElement(tag)
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue
    if (k === 'class') el.className = v
    else if (k === 'html') el.innerHTML = v
    else if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v)
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v)
    else el.setAttribute(k, v === true ? '' : v)
  }
  for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) el.append(c.nodeType ? c : document.createTextNode(String(c)))
  return el
}

const singular = (name) => {
  if (/ies$/.test(name)) return name.slice(0, -3) + 'y'
  if (/ses$/.test(name)) return name.slice(0, -2)
  if (/s$/.test(name) && name.length > 1) return name.slice(0, -1)
  return 'item'
}

function mergeNodes(lists) {
  const out = []
  const byName = new Map()
  for (const list of lists) {
    for (const node of list) {
      const existing = byName.get(node.name)
      if (!existing) {
        const copy = { ...node }
        if (copy.children) copy.children = mergeNodes([copy.children])
        if (copy.item) copy.item = mergeNodes([copy.item])
        byName.set(node.name, copy)
        out.push(copy)
      } else if (existing.kind === node.kind && node.kind === 'group') {
        existing.children = mergeNodes([existing.children, node.children])
      } else if (existing.kind === node.kind && node.kind === 'list') {
        existing.item = mergeNodes([existing.item, node.item])
      }
    }
  }
  return out
}

export class TemplateEditor {
  constructor(root, config) {
    this.root = root
    this.config = config
    this.textarea = root.querySelector('textarea')
    this.form = root.closest('form')
    this.chipViews = new Set()
    this.popover = null
    this.build()
  }

  // ------------------------------------------------------------------ setup
  build() {
    const c = this.config
    const preset = PRESETS[c.preset] ? c.preset : 'full'
    this.shell = h('div', { class: `tp-editor tp-skin-${c.skin || 'default'} tp-preset-${preset}` })
    this.toolbar = h('div', { class: 'tp-toolbar', role: 'toolbar' })
    this.surface = h('div', { class: 'tp-surface' })
    this.page = h('div', { class: 'tp-page' })
    this.surface.append(this.page)
    this.status = h('div', { class: 'tp-status' })
    this.bubble = h('div', { class: 'tp-bubble' })
    this.shell.append(this.toolbar, this.surface, this.status)
    if (c.height) this.surface.style.minHeight = `${c.height}px`
    this.root.append(this.shell)

    const ctx = this
    const extensions = [
      StarterKit.configure({
        heading: { levels: [1, 2, 3, 4] },
        link: { openOnClick: false, autolink: true, protocols: ['mailto', 'tel'] },
      }),
      TextStyle,
      Color,
      FontSize,
      Highlight.configure({ multicolor: true }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Image.configure({ allowBase64: true }),
      Table.configure({ resizable: false }),
      TpTableRow,
      TableHeader,
      TableCell,
      Placeholder.configure({ placeholder: c.placeholder || 'Start writing… type {{ to insert a field' }),
      TpVariable.configure({ ctx }),
      TpConstant.configure({ ctx }),
      TpDynamic.configure({ ctx }),
      TpBlock.configure({ ctx }),
      TpRepeat.configure({ ctx }),
      TpIf.configure({ ctx }),
      BraceTrigger.configure({ ctx }),
    ]
    if (preset === 'minimal') {
      extensions.push(BubbleMenu.configure({ element: this.bubble }))
      this.buildBubble()
    }
    this.editor = new Editor({
      element: this.page,
      extensions,
      content: (this.textarea && this.textarea.value.trim()) || '',
      onUpdate: () => this.sync(),
      onSelectionUpdate: () => this.updateToolbar(),
      onTransaction: () => this.updateToolbar(),
    })
    this.buildToolbar(c.toolbar || PRESETS[preset])
    this.watchTypeFields()
    // Node views render before `this.editor` exists; re-render them now that
    // scopes (repeat sections, repeated rows) can be resolved.
    this.refreshViews()
    this.sync()
    document.addEventListener('mousedown', (e) => {
      if (this.popover && !this.popover.contains(e.target)) this.closePopover()
    })
  }

  sync() {
    if (this.textarea) this.textarea.value = this.editor.isEmpty ? '' : this.editor.getHTML()
    this.updateStatus()
  }

  destroy() {
    this.closePopover()
    this.editor.destroy()
    this.shell.remove()
  }

  // ------------------------------------------------------------- types
  fieldValue(name) {
    if (!name || !this.form) return null
    const el = this.form.elements[name]
    if (!el) return null
    if (el instanceof RadioNodeList || (el.length !== undefined && !el.tagName)) {
      const vals = [...el].filter((i) => i.checked).map((i) => i.value)
      return vals
    }
    if (el.type === 'checkbox') return el.checked ? [el.value] : []
    if (el.multiple) return [...el.selectedOptions].map((o) => o.value)
    return el.value
  }

  activeTypes() {
    const all = this.config.types || []
    const pick = (keys) => all.filter((t) => keys.includes(t.key))
    if (this.config.templateType) return pick([this.config.templateType])
    if (this.config.typeField) {
      const v = this.fieldValue(this.config.typeField)
      const keys = Array.isArray(v) ? v : v ? [v] : []
      if (keys.length) return pick(keys)
    }
    if (this.config.typesField) {
      const v = this.fieldValue(this.config.typesField) || []
      if (v.length) return pick(v)
    }
    return all
  }

  roots() {
    const types = this.activeTypes()
    const key = types.map((t) => t.key).join(',')
    if (this._rootsKey !== key) {
      this._rootsKey = key
      this._roots = mergeNodes(types.map((t) => t.schema))
    }
    return this._roots
  }

  watchTypeFields() {
    const names = [this.config.typeField, this.config.typesField].filter(Boolean)
    if (!names.length || !this.form) return
    this.form.addEventListener('change', (e) => {
      if (names.includes(e.target.name)) this.refreshViews()
    })
  }

  refreshViews() {
    this._rootsKey = null
    for (const v of this.chipViews) v.refresh()
    this.updateStatus()
  }

  // ------------------------------------------------------------- schema
  scopesAt(pos) {
    const scopes = []
    if (!this.editor || pos === undefined || pos === null) return scopes
    let $pos
    try {
      $pos = this.editor.state.doc.resolve(pos)
    } catch (e) {
      return scopes
    }
    for (let d = 1; d <= $pos.depth; d++) {
      const n = $pos.node(d)
      let path = null
      if (n.type.name === 'tpRepeat') path = n.attrs.path
      else if (n.type.name === 'tableRow' && n.attrs.repeat) path = n.attrs.repeat
      if (!path) continue
      const list = this.resolve(path, scopes)
      scopes.push({
        alias: n.attrs.as || 'item',
        path,
        label: list ? list.label : path,
        item: list && list.kind === 'list' ? list.item : null,
      })
    }
    return scopes
  }

  resolve(path, scopes = []) {
    if (!path) return null
    const [head, ...rest] = path.split('.')
    const scope = [...scopes].reverse().find((s) => s.alias === head)
    let node = scope
      ? { kind: 'group', label: scope.label, children: scope.item || [], scope: true }
      : this.roots().find((n) => n.name === head)
    for (const part of rest) {
      if (!node || node.kind !== 'group') return null
      node = (node.children || []).find((c) => c.name === part)
    }
    return node || null
  }

  labelFor(path, scopes = []) {
    const parts = path.split('.')
    const labels = []
    for (let i = 1; i <= parts.length; i++) {
      const n = this.resolve(parts.slice(0, i).join('.'), scopes)
      labels.push(i === 1 && scopes.some((s) => s.alias === parts[0]) ? parts[0] : n ? n.label : parts[i - 1])
    }
    return labels.join(' › ')
  }

  findBlock(slug) {
    return (this.config.blocks || []).find((b) => b.slug === slug) || null
  }

  // ------------------------------------------------------------- describe
  describeChip(kind, node, pos) {
    const fmt = node.attrs.format
    if (kind === 'var') {
      const scopes = this.scopesAt(pos)
      const n = this.resolve(node.attrs.path, scopes)
      const invalid = !n || n.kind !== 'var'
      const head = node.attrs.path.split('.')[0]
      const inScope = scopes.some((sc) => sc.alias === head)
      return {
        label: invalid ? node.attrs.label || node.attrs.path : inScope ? `${head} › ${n.label}` : n.label,
        invalid,
        title: invalid
          ? `Unknown field “${node.attrs.path}” for this template type`
          : `${this.labelFor(node.attrs.path, scopes)} (${node.attrs.path}) — click to change formatting`,
        formatHint: this.formatHint(fmt || (n && n.format), n && n.type),
      }
    }
    if (kind === 'const') {
      const c = (this.config.constants || []).find((x) => x.key === node.attrs.key)
      return {
        label: c ? c.label : node.attrs.label || node.attrs.key,
        invalid: !c,
        title: c ? `Constant: ${c.value}` : `Unknown constant “${node.attrs.key}”`,
        formatHint: this.formatHint(fmt, 'string'),
      }
    }
    const d = (this.config.dynamic || []).find((x) => x.key === node.attrs.key)
    const outside = node.attrs.key === 'row_number' && !this.scopesAt(pos).length
    return {
      label: d ? d.label : node.attrs.key,
      invalid: !d || outside,
      title: outside ? 'Row number only works inside a repeat section or repeated row' : 'Filled in when the document is generated',
      formatHint: d ? this.formatHint(fmt, d.type) : '',
    }
  }

  formatHint(fmt, type) {
    if (!fmt) return ''
    const k = fmt.kind
    if (['date', 'datetime', 'time'].includes(k)) return fmt.pattern || fmt.style || ''
    if (k === 'money') return [fmt.currency, fmt.decimals !== undefined && fmt.decimals !== '' ? `${fmt.decimals}dp` : ''].filter(Boolean).join(' ')
    if (k === 'number' || k === 'percent') return fmt.decimals !== undefined && fmt.decimals !== '' ? `${fmt.decimals}dp` : ''
    if (k === 'text' && fmt.case && fmt.case !== 'none') return fmt.case
    if (k === 'boolean' && (fmt.true || fmt.false)) return `${fmt.true || 'Yes'}/${fmt.false || 'No'}`
    return ''
  }

  describeRepeat(path, as, pos) {
    const scopes = this.scopesAt(pos)
    const n = this.resolve(path, scopes)
    const invalid = !n || n.kind !== 'list'
    return {
      text: invalid ? `Repeat: unknown list “${path}”` : `Repeat for each ${this.labelFor(path, scopes)} — as “${as}”`,
      invalid,
    }
  }

  describeCondition(attrs, pos) {
    const scopes = this.scopesAt(pos)
    const n = this.resolve(attrs.path, scopes)
    const invalid = !n
    const value = ['truthy', 'falsy'].includes(attrs.op) ? '' : ` “${attrs.value}”`
    return {
      text: invalid ? `Show if: unknown field “${attrs.path}”` : `Show only if ${this.labelFor(attrs.path, scopes)} ${OP_LABELS[attrs.op] || attrs.op}${value}`,
      invalid,
    }
  }

  updateStatus() {
    if (!this.status) return
    const invalid = this.shell.querySelectorAll('.tp-chip--invalid, .tp-section--invalid, .tp-blocknode--missing').length
    const types = this.activeTypes().map((t) => t.label).join(', ')
    this.status.innerHTML = ''
    this.status.append(
      h('span', { class: 'tp-status__types' }, types ? `Fields from: ${types}` : 'No template type selected'),
      h('span', { class: 'tp-status__hint' }, 'Type {{ to insert a field'),
    )
    if (invalid) this.status.append(h('span', { class: 'tp-status__error' }, `${invalid} item(s) need attention`))
  }

  // ------------------------------------------------------------- toolbar
  smallButton(label, fn) {
    return h('button', {
      type: 'button',
      class: 'tp-mini',
      onMousedown: (e) => e.preventDefault(),
      onClick: (e) => {
        e.preventDefault()
        e.stopPropagation()
        fn()
      },
    }, label)
  }

  button(name, { icon, label, title, run, active, text }) {
    const btn = h('button', {
      type: 'button',
      class: 'tp-btn' + (text ? ' tp-btn--text' : ''),
      title: title || label,
      'aria-label': title || label,
      'data-name': name,
      onMousedown: (e) => e.preventDefault(),
      onClick: (e) => {
        e.preventDefault()
        run(e)
      },
    })
    btn.innerHTML = (icon || '') + (text ? `<span>${label}</span>` : '')
    if (active) this.activeChecks.push(() => btn.classList.toggle('is-active', !!active()))
    return btn
  }

  buildToolbar(items) {
    const ed = () => this.editor.chain().focus()
    this.activeChecks = []
    const defs = {
      undo: () => this.button('undo', { icon: icons.undo, label: 'Undo', run: () => ed().undo().run() }),
      redo: () => this.button('redo', { icon: icons.redo, label: 'Redo', run: () => ed().redo().run() }),
      bold: () => this.button('bold', { icon: icons.bold, label: 'Bold', run: () => ed().toggleBold().run(), active: () => this.editor.isActive('bold') }),
      italic: () => this.button('italic', { icon: icons.italic, label: 'Italic', run: () => ed().toggleItalic().run(), active: () => this.editor.isActive('italic') }),
      underline: () => this.button('underline', { icon: icons.underline, label: 'Underline', run: () => ed().toggleUnderline().run(), active: () => this.editor.isActive('underline') }),
      strike: () => this.button('strike', { icon: icons.strike, label: 'Strikethrough', run: () => ed().toggleStrike().run(), active: () => this.editor.isActive('strike') }),
      clear: () => this.button('clear', { icon: icons.clear, label: 'Clear formatting', run: () => ed().unsetAllMarks().clearNodes().run() }),
      alignLeft: () => this.button('alignLeft', { icon: icons.alignLeft, label: 'Align left', run: () => ed().setTextAlign('left').run(), active: () => this.editor.isActive({ textAlign: 'left' }) }),
      alignCenter: () => this.button('alignCenter', { icon: icons.alignCenter, label: 'Center', run: () => ed().setTextAlign('center').run(), active: () => this.editor.isActive({ textAlign: 'center' }) }),
      alignRight: () => this.button('alignRight', { icon: icons.alignRight, label: 'Align right', run: () => ed().setTextAlign('right').run(), active: () => this.editor.isActive({ textAlign: 'right' }) }),
      alignJustify: () => this.button('alignJustify', { icon: icons.alignJustify, label: 'Justify', run: () => ed().setTextAlign('justify').run(), active: () => this.editor.isActive({ textAlign: 'justify' }) }),
      bulletList: () => this.button('bulletList', { icon: icons.bulletList, label: 'Bullet list', run: () => ed().toggleBulletList().run(), active: () => this.editor.isActive('bulletList') }),
      orderedList: () => this.button('orderedList', { icon: icons.orderedList, label: 'Numbered list', run: () => ed().toggleOrderedList().run(), active: () => this.editor.isActive('orderedList') }),
      blockquote: () => this.button('blockquote', { icon: icons.blockquote, label: 'Quote', run: () => ed().toggleBlockquote().run(), active: () => this.editor.isActive('blockquote') }),
      hr: () => this.button('hr', { icon: icons.hr, label: 'Horizontal line', run: () => ed().setHorizontalRule().run() }),
      link: () => this.button('link', { icon: icons.link, label: 'Link', run: () => this.editLink(), active: () => this.editor.isActive('link') }),
      image: () => this.button('image', { icon: icons.image, label: 'Image', run: () => this.insertImage() }),
      table: () => this.button('table', { icon: icons.table, label: 'Table', run: (e) => this.tableMenu(e.currentTarget), active: () => this.editor.isActive('table') }),
      highlight: () => this.button('highlight', { icon: icons.highlight, label: 'Highlight', run: () => ed().toggleHighlight({ color: '#fde68a' }).run(), active: () => this.editor.isActive('highlight') }),
      color: () => {
        const input = h('input', {
          type: 'color', class: 'tp-color', title: 'Text colour', value: '#1f2937',
          onInput: (e) => this.editor.chain().focus().setColor(e.target.value).run(),
        })
        return input
      },
      blockType: () => {
        const sel = h('select', {
          class: 'tp-select', title: 'Paragraph style',
          onChange: (e) => {
            const v = e.target.value
            const c = this.editor.chain().focus()
            if (v === 'p') c.setParagraph().run()
            else if (v === 'code') c.toggleCodeBlock().run()
            else c.toggleHeading({ level: Number(v.slice(1)) }).run()
          },
        },
        h('option', { value: 'p' }, 'Paragraph'),
        h('option', { value: 'h1' }, 'Heading 1'),
        h('option', { value: 'h2' }, 'Heading 2'),
        h('option', { value: 'h3' }, 'Heading 3'),
        h('option', { value: 'h4' }, 'Heading 4'),
        h('option', { value: 'code' }, 'Code'))
        this.activeChecks.push(() => {
          let v = 'p'
          for (const l of [1, 2, 3, 4]) if (this.editor.isActive('heading', { level: l })) v = `h${l}`
          if (this.editor.isActive('codeBlock')) v = 'code'
          sel.value = v
        })
        return sel
      },
      fontSize: () => {
        const sel = h('select', {
          class: 'tp-select tp-select--narrow', title: 'Font size',
          onChange: (e) => {
            const v = e.target.value
            const c = this.editor.chain().focus()
            v ? c.setFontSize(v).run() : c.unsetFontSize().run()
          },
        }, h('option', { value: '' }, 'Size'), FONT_SIZES.map((s) => h('option', { value: s }, s)))
        this.activeChecks.push(() => {
          sel.value = this.editor.getAttributes('textStyle').fontSize || ''
        })
        return sel
      },
      variable: () => this.button('variable', { icon: icons.field, label: 'Field', title: 'Insert a field (variable)', text: true, run: () => this.openPicker({ tab: 'fields' }) }),
      constant: () => this.button('constant', { icon: icons.constant, label: 'Constant', title: 'Insert a constant (e.g. website name)', text: true, run: () => this.openPicker({ tab: 'constants' }) }),
      dynamic: () => this.button('dynamic', { icon: icons.clock, label: 'Date & time', title: 'Insert current date/time and other automatic values', text: true, run: () => this.openPicker({ tab: 'dynamic' }) }),
      block: () => this.button('block', { icon: icons.block, label: 'Block', title: 'Insert a shared block', text: true, run: () => this.openPicker({ tab: 'blocks' }) }),
      repeat: () => this.button('repeat', { icon: icons.repeat, label: 'Repeat', title: 'Repeat the selected content for each item of a list', text: true, run: () => this.insertRepeat() }),
      condition: () => this.button('condition', { icon: icons.condition, label: 'Condition', title: 'Show the selected content only if…', text: true, run: () => this.insertCondition() }),
      insert: () => this.button('insert', { icon: icons.plus, label: 'Insert field', text: true, run: () => this.openPicker({}) }),
      preview: () => (this.config.previewUrl ? this.button('preview', { icon: icons.eye, label: 'Preview', text: true, run: () => this.preview() }) : null),
      fullscreen: () => this.button('fullscreen', { icon: icons.expand, label: 'Full screen', run: () => this.shell.classList.toggle('tp-editor--fullscreen') }),
    }
    let group = h('div', { class: 'tp-group' })
    this.toolbar.append(group)
    for (const item of items) {
      if (item === '|') {
        group = h('div', { class: 'tp-group' })
        this.toolbar.append(group)
      } else if (item === '/') {
        this.toolbar.append(h('div', { class: 'tp-break' }))
        group = h('div', { class: 'tp-group' })
        this.toolbar.append(group)
      } else if (item === '>') {
        group = h('div', { class: 'tp-group tp-group--end' })
        this.toolbar.append(group)
      } else if (defs[item]) {
        const el = defs[item]()
        if (el) group.append(el)
      }
    }
    for (const g of [...this.toolbar.querySelectorAll('.tp-group')]) if (!g.children.length) g.remove()
    this.updateToolbar()
  }

  buildBubble() {
    const ed = () => this.editor.chain().focus()
    this.activeChecks = this.activeChecks || []
    this.bubble.append(
      this.button('b-bold', { icon: icons.bold, label: 'Bold', run: () => ed().toggleBold().run() }),
      this.button('b-italic', { icon: icons.italic, label: 'Italic', run: () => ed().toggleItalic().run() }),
      this.button('b-underline', { icon: icons.underline, label: 'Underline', run: () => ed().toggleUnderline().run() }),
      this.button('b-link', { icon: icons.link, label: 'Link', run: () => this.editLink() }),
      this.button('b-h2', { label: 'H', title: 'Heading', text: true, run: () => ed().toggleHeading({ level: 2 }).run() }),
      this.button('b-field', { icon: icons.field, label: 'Field', run: () => this.openPicker({}) }),
    )
  }

  updateToolbar() {
    for (const check of this.activeChecks || []) check()
  }

  // ------------------------------------------------------------- popovers
  closePopover() {
    if (this.popoverObserver) {
      this.popoverObserver.disconnect()
      this.popoverObserver = null
    }
    if (this.popover) {
      this.popover.remove()
      this.popover = null
    }
  }

  showPopover(el, anchorRect) {
    this.closePopover()
    el.classList.add('tp-pop', `tp-skin-${this.config.skin || 'default'}`)
    document.body.append(el)
    this.popover = el
    this.popoverAnchor = anchorRect || this.surface.getBoundingClientRect()
    this.positionPopover()
    // Keep it on screen when its content grows (e.g. a field is revealed).
    if (window.ResizeObserver) {
      this.popoverObserver = new ResizeObserver(() => this.positionPopover())
      this.popoverObserver.observe(el)
    }
  }

  positionPopover() {
    const el = this.popover
    if (!el) return
    const r = this.popoverAnchor
    const w = el.offsetWidth
    const hgt = el.offsetHeight
    const left = Math.min(Math.max(8, r.left), window.innerWidth - w - 8)
    let top = r.bottom + 6
    if (top + hgt > window.innerHeight - 8) top = r.top - hgt - 6
    top = Math.max(8, Math.min(top, window.innerHeight - hgt - 8))
    el.style.left = `${left}px`
    el.style.top = `${top}px`
  }

  caretRect() {
    try {
      const { from } = this.editor.state.selection
      const c = this.editor.view.coordsAtPos(from)
      return { left: c.left, right: c.right, top: c.top, bottom: c.bottom }
    } catch (e) {
      return null
    }
  }

  dialog({ title, fields, submitLabel = 'Apply', extraButtons = [], anchor }) {
    return new Promise((resolve) => {
      const form = h('form', { class: 'tp-dialog' })
      form.append(h('div', { class: 'tp-dialog__title' }, title))
      const inputs = {}
      for (const f of fields) {
        let input
        if (f.type === 'select') {
          input = h('select', { name: f.name },
            (f.options || []).map((o) => (o.group
              ? h('optgroup', { label: o.group }, o.options.map((x) => h('option', { value: x.value, selected: x.value === f.value }, x.label)))
              : h('option', { value: o.value, selected: o.value === f.value }, o.label))))
        } else {
          input = h('input', { name: f.name, type: f.type || 'text', value: f.value ?? '', placeholder: f.placeholder || '' })
        }
        inputs[f.name] = input
        const row = h('label', { class: 'tp-field' + (f.hidden ? ' is-hidden' : '') }, h('span', {}, f.label), input, f.help ? h('small', {}, f.help) : null)
        f.row = row
        form.append(row)
      }
      const values = () => Object.fromEntries(Object.entries(inputs).map(([k, el]) => [k, el.value]))
      const sync = () => fields.forEach((f) => f.showIf && f.row.classList.toggle('is-hidden', !f.showIf(values())))
      form.addEventListener('input', sync)
      form.addEventListener('change', sync)
      sync()
      const actions = h('div', { class: 'tp-dialog__actions' })
      for (const b of extraButtons) {
        actions.append(h('button', { type: 'button', class: `tp-mini ${b.danger ? 'tp-mini--danger' : ''}`, onClick: () => { this.closePopover(); resolve({ __action: b.action }) } }, b.label))
      }
      actions.append(
        h('button', { type: 'button', class: 'tp-mini', onClick: () => { this.closePopover(); resolve(null) } }, 'Cancel'),
        h('button', { type: 'submit', class: 'tp-mini tp-mini--primary' }, submitLabel),
      )
      form.append(actions)
      form.addEventListener('submit', (e) => {
        e.preventDefault()
        const v = values()
        this.closePopover()
        resolve(v)
      })
      form.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          e.preventDefault()
          this.closePopover()
          resolve(null)
        }
      })
      // Wrap the <form>: inputs named e.g. "style" would shadow form.style.
      const wrap = h('div', { class: 'tp-dialog-wrap' }, form)
      this.showPopover(wrap, anchor || this.caretRect())
      const first = form.querySelector('input, select')
      first && first.focus()
    })
  }

  // ------------------------------------------------------------- picker
  pickerItems(tab, scopes) {
    const items = []
    if (tab === 'fields') {
      const walk = (nodes, prefix, depth, groupLabel) => {
        for (const n of nodes) {
          const path = prefix ? `${prefix}.${n.name}` : n.name
          if (n.kind === 'var') items.push({ kind: 'var', path, label: n.label, sub: path, depth, help: n.help, group: groupLabel, type: n.type })
          else if (n.kind === 'group') {
            items.push({ kind: 'header', label: n.label, depth })
            walk(n.children || [], path, depth + 1, n.label)
          } else if (n.kind === 'list') items.push({ kind: 'list', path, label: n.label, sub: `${path} · list — inserts a repeat section`, depth, group: groupLabel })
        }
      }
      for (const s of [...scopes].reverse()) {
        items.push({ kind: 'header', label: `Current ${s.label} (“${s.alias}”)`, depth: 0, scope: true })
        walk(s.item || [], s.alias, 1, s.label)
      }
      walk(this.roots(), '', 0, '')
    } else if (tab === 'constants') {
      for (const c of this.config.constants || []) items.push({ kind: 'const', key: c.key, label: c.label, sub: c.value })
    } else if (tab === 'dynamic') {
      for (const d of this.config.dynamic || []) {
        if (d.key === 'row_number' && !scopes.length) continue
        items.push({ kind: 'dynamic', key: d.key, label: d.label, sub: d.type })
      }
    } else if (tab === 'blocks') {
      const types = this.activeTypes().map((t) => t.key)
      for (const b of this.config.blocks || []) {
        const fits = !b.types.length || b.types.some((t) => types.includes(t))
        if (fits) items.push({ kind: 'block', slug: b.slug, label: b.name, sub: `${b.category} · ${b.slug}` })
      }
    }
    return items
  }

  openPicker({ tab = 'fields', replacePos = null } = {}) {
    const scopes = this.scopesAt(this.editor.state.selection.from)
    const el = h('div', { class: 'tp-picker' })
    const search = h('input', { type: 'search', placeholder: 'Search…', class: 'tp-picker__search' })
    const tabs = h('div', { class: 'tp-picker__tabs' })
    const list = h('div', { class: 'tp-picker__list', role: 'listbox' })
    el.append(search, tabs, list)
    const tabDefs = [['fields', 'Fields'], ['constants', 'Constants'], ['dynamic', 'Date & time'], ['blocks', 'Blocks']]
    let current = replacePos !== null ? 'blocks' : tab
    let selectable = []
    let active = 0

    const choose = (item) => {
      this.closePopover()
      const chain = this.editor.chain().focus()
      if (item.kind === 'var') chain.insertContent({ type: 'tpVariable', attrs: { path: item.path, label: item.label } }).run()
      else if (item.kind === 'const') chain.insertContent({ type: 'tpConstant', attrs: { key: item.key, label: item.label } }).run()
      else if (item.kind === 'dynamic') chain.insertContent({ type: 'tpDynamic', attrs: { key: item.key, label: item.label } }).run()
      else if (item.kind === 'list') this.insertRepeat(item.path)
      else if (item.kind === 'block') {
        if (replacePos !== null) {
          this.editor.chain().focus().command(({ tr }) => {
            tr.setNodeMarkup(replacePos, undefined, { slug: item.slug })
            return true
          }).run()
        } else chain.insertContent({ type: 'tpBlock', attrs: { slug: item.slug } }).run()
      }
    }

    const render = () => {
      tabs.innerHTML = ''
      for (const [key, label] of tabDefs) {
        tabs.append(h('button', { type: 'button', class: 'tp-tab' + (key === current ? ' is-active' : ''), onClick: () => { current = key; active = 0; render(); search.focus() } }, label))
      }
      const q = search.value.trim().toLowerCase()
      let items = this.pickerItems(current, scopes)
      if (q) {
        items = items.filter((i) => i.kind !== 'header' && `${i.label} ${i.sub || ''} ${i.group || ''}`.toLowerCase().includes(q))
      }
      list.innerHTML = ''
      selectable = []
      if (!items.length) list.append(h('div', { class: 'tp-picker__empty' }, q ? 'Nothing matches.' : 'Nothing available here yet.'))
      for (const item of items) {
        if (item.kind === 'header') {
          list.append(h('div', { class: 'tp-picker__header' + (item.scope ? ' is-scope' : ''), style: { paddingLeft: `${10 + item.depth * 14}px` } }, item.label))
          continue
        }
        const idx = selectable.length
        const row = h('div', {
          class: `tp-picker__item tp-picker__item--${item.kind}`,
          role: 'option',
          style: { paddingLeft: `${10 + (q ? 0 : item.depth || 0) * 14}px` },
          onMousedown: (e) => e.preventDefault(),
          onClick: () => choose(item),
          onMousemove: () => { if (active !== idx) { active = idx; highlight() } },
        }, h('span', { class: 'tp-picker__label' }, item.label), item.sub ? h('span', { class: 'tp-picker__sub' }, item.sub) : null)
        selectable.push({ row, item })
        list.append(row)
      }
      highlight()
    }
    const highlight = () => {
      selectable.forEach((s, i) => s.row.classList.toggle('is-active', i === active))
      const cur = selectable[active]
      cur && cur.row.scrollIntoView({ block: 'nearest' })
    }
    search.addEventListener('input', () => { active = 0; render() })
    el.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, selectable.length - 1); highlight() }
      else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); highlight() }
      else if (e.key === 'Enter') { e.preventDefault(); selectable[active] && choose(selectable[active].item) }
      else if (e.key === 'Escape') { e.preventDefault(); this.closePopover(); this.editor.commands.focus() }
      else if (e.key === 'Tab') {
        e.preventDefault()
        const i = tabDefs.findIndex(([k]) => k === current)
        current = tabDefs[(i + (e.shiftKey ? tabDefs.length - 1 : 1)) % tabDefs.length][0]
        active = 0
        render()
      }
    })
    render()
    this.showPopover(el, this.caretRect())
    search.focus()
  }

  // ------------------------------------------------------------- formatting
  openChipPopover(kind, pos, dom) {
    const node = this.editor.state.doc.nodeAt(pos)
    if (!node) return
    let type = 'string'
    let schemaFmt = null
    if (kind === 'var') {
      const n = this.resolve(node.attrs.path, this.scopesAt(pos))
      type = n && n.type ? n.type : 'string'
      schemaFmt = n && n.format
    } else if (kind === 'dynamic') {
      const d = (this.config.dynamic || []).find((x) => x.key === node.attrs.key)
      type = d ? d.type : 'string'
      if (node.attrs.key === 'year') type = 'string'
      if (['page_number', 'page_count'].includes(node.attrs.key)) type = 'none'
    }
    const fkind = KIND_FOR_TYPE[type] || 'text'
    const fmt = { kind: fkind, ...(schemaFmt || {}), ...(node.attrs.format || {}) }
    const F = this.config.formats || {}
    const fields = []
    if (['date', 'datetime', 'time'].includes(fkind)) {
      const style = fmt.pattern ? 'custom' : fmt.style || (fkind === 'time' ? 'short' : 'medium')
      fields.push({ name: 'style', label: 'Style', type: 'select', value: style, options: [...(F.dateStyles || ['short', 'medium', 'long', 'full']).map((s) => ({ value: s, label: `${s[0].toUpperCase()}${s.slice(1)}  —  ${this.example(fkind, { style: s })}` })), { value: 'custom', label: 'Custom pattern…' }] })
      fields.push({ name: 'pattern', label: 'Pattern', value: fmt.pattern || '', placeholder: 'dd/MM/yyyy', help: 'e.g. dd/MM/yyyy · EEEE, d MMMM y · HH:mm', showIf: (v) => v.style === 'custom' })
    } else if (fkind === 'money') {
      const cur = F.currencies || ['USD', 'EUR']
      fields.push({ name: 'currency', label: 'Currency', type: 'select', value: fmt.currency || '', options: [{ value: '', label: `Site default (${F.defaultCurrency || 'USD'})` }, ...cur.map((c) => ({ value: c, label: c }))] })
      fields.push({ name: 'decimals', label: 'Decimal places', type: 'number', value: fmt.decimals ?? '', placeholder: 'auto' })
      fields.push({ name: 'symbol', label: 'Show as', type: 'select', value: fmt.symbol || '', options: [{ value: '', label: 'Symbol ($, €)' }, { value: 'code', label: 'Code (USD, EUR)' }] })
    } else if (fkind === 'number' || fkind === 'percent') {
      fields.push({ name: 'decimals', label: 'Decimal places', type: 'number', value: fmt.decimals ?? '', placeholder: 'auto' })
    } else if (fkind === 'boolean') {
      fields.push({ name: 'true', label: 'Text when yes', value: fmt.true || '', placeholder: 'Yes' })
      fields.push({ name: 'false', label: 'Text when no', value: fmt.false || '', placeholder: 'No' })
    } else if (type !== 'none') {
      fields.push({ name: 'case', label: 'Letter case', type: 'select', value: fmt.case || 'none', options: [['none', 'As entered'], ['upper', 'UPPERCASE'], ['lower', 'lowercase'], ['title', 'Title Case'], ['capitalize', 'Capitalize first letter']].map(([value, label]) => ({ value, label })) })
    }
    if (type !== 'none') fields.push({ name: 'fallback', label: 'If empty, show', value: fmt.fallback || '', placeholder: '(nothing)' })
    const title = kind === 'var' ? this.labelFor(node.attrs.path, this.scopesAt(pos)) : this.describeChip(kind, node, pos).label
    this.dialog({
      title: type === 'none' ? `${title} (filled in on each PDF/DOCX page)` : `Format: ${title}`,
      fields,
      anchor: dom.getBoundingClientRect(),
      extraButtons: [{ label: 'Remove', action: 'remove', danger: true }],
    }).then((v) => {
      if (!v) return
      if (v.__action === 'remove') {
        this.editor.chain().focus().deleteRange({ from: pos, to: pos + node.nodeSize }).run()
        return
      }
      const out = { kind: fkind }
      if (v.style && v.style !== 'custom') out.style = v.style
      if (v.style === 'custom' && v.pattern) out.pattern = v.pattern.trim()
      for (const k of ['currency', 'symbol', 'true', 'false', 'fallback']) if (v[k]) out[k] = v[k]
      if (v.case && v.case !== 'none') out.case = v.case
      if (v.decimals !== undefined && v.decimals !== '') out.decimals = Math.max(0, Math.min(10, parseInt(v.decimals, 10) || 0))
      this.editor.chain().focus().command(({ tr }) => {
        tr.setNodeMarkup(pos, undefined, { ...node.attrs, format: out })
        return true
      }).run()
    })
  }

  example(kind, { style }) {
    const locale = (this.config.formats && this.config.formats.locale || 'en-US').replace('_', '-')
    const d = new Date(2026, 0, 15, 14, 30)
    try {
      if (kind === 'date') return new Intl.DateTimeFormat(locale, { dateStyle: style }).format(d)
      if (kind === 'time') return new Intl.DateTimeFormat(locale, { timeStyle: style }).format(d)
      return new Intl.DateTimeFormat(locale, { dateStyle: style, timeStyle: 'short' }).format(d)
    } catch (e) {
      return ''
    }
  }

  // ------------------------------------------------------------- sections
  listOptions(scopes) {
    const out = []
    const walk = (nodes, prefix, groupLabel) => {
      for (const n of nodes) {
        const path = prefix ? `${prefix}.${n.name}` : n.name
        if (n.kind === 'list') out.push({ value: path, label: groupLabel ? `${groupLabel} › ${n.label}` : n.label, name: n.name })
        if (n.kind === 'group') walk(n.children || [], path, groupLabel ? `${groupLabel} › ${n.label}` : n.label)
      }
    }
    for (const s of scopes) walk(s.item || [], s.alias, s.alias)
    walk(this.roots(), '', '')
    return out
  }

  varOptions(scopes) {
    const out = []
    const walk = (nodes, prefix, groupLabel) => {
      for (const n of nodes) {
        const path = prefix ? `${prefix}.${n.name}` : n.name
        if (n.kind === 'var') out.push({ value: path, label: groupLabel ? `${groupLabel} › ${n.label}` : n.label })
        if (n.kind === 'group') walk(n.children || [], path, groupLabel ? `${groupLabel} › ${n.label}` : n.label)
      }
    }
    for (const s of scopes) walk(s.item || [], s.alias, s.alias)
    walk(this.roots(), '', '')
    return out
  }

  async repeatDialog(scopes, current = {}, extraButtons = []) {
    const lists = this.listOptions(scopes)
    if (!lists.length) {
      this.flash('This template type has no lists to repeat.')
      return null
    }
    const first = lists.find((l) => l.value === current.path) || lists[0]
    return this.dialog({
      title: 'Repeat for each item of…',
      fields: [
        { name: 'path', label: 'List', type: 'select', value: first.value, options: lists },
        { name: 'as', label: 'Call each item', value: current.as || singular(first.name), help: 'Fields of the item appear in the picker under this name.' },
      ],
      extraButtons,
    })
  }

  async insertRepeat(path) {
    const scopes = this.scopesAt(this.editor.state.selection.from)
    const v = await this.repeatDialog(scopes, { path })
    if (!v || !v.path) return
    const as = (v.as || 'item').replace(/[^A-Za-z0-9_]/g, '_').replace(/^(\d)/, '_$1') || 'item'
    const ok = this.editor.chain().focus().wrapIn('tpRepeat', { path: v.path, as }).run()
    if (!ok) this.editor.chain().focus().insertContent({ type: 'tpRepeat', attrs: { path: v.path, as }, content: [{ type: 'paragraph' }] }).run()
  }

  async conditionDialog(scopes, current = {}) {
    const vars = this.varOptions(scopes)
    if (!vars.length) {
      this.flash('This template type has no fields to test.')
      return null
    }
    return this.dialog({
      title: 'Show the content only if…',
      fields: [
        { name: 'path', label: 'Field', type: 'select', value: current.path || vars[0].value, options: vars },
        { name: 'op', label: 'Condition', type: 'select', value: current.op || 'truthy', options: Object.entries(OP_LABELS).map(([value, label]) => ({ value, label })) },
        { name: 'value', label: 'Value', value: current.value || '', showIf: (v) => !['truthy', 'falsy'].includes(v.op) },
      ],
    })
  }

  async insertCondition() {
    const scopes = this.scopesAt(this.editor.state.selection.from)
    const v = await this.conditionDialog(scopes)
    if (!v) return
    const attrs = { path: v.path, op: v.op, value: ['truthy', 'falsy'].includes(v.op) ? '' : v.value }
    const ok = this.editor.chain().focus().wrapIn('tpIf', attrs).run()
    if (!ok) this.editor.chain().focus().insertContent({ type: 'tpIf', attrs, content: [{ type: 'paragraph' }] }).run()
  }

  async editSection(kind, pos) {
    const node = this.editor.state.doc.nodeAt(pos)
    if (!node) return
    const scopes = this.scopesAt(pos)
    const v = kind === 'repeat' ? await this.repeatDialog(scopes, node.attrs) : await this.conditionDialog(scopes, node.attrs)
    if (!v) return
    const attrs = kind === 'repeat'
      ? { path: v.path, as: (v.as || 'item').replace(/[^A-Za-z0-9_]/g, '_') }
      : { path: v.path, op: v.op, value: ['truthy', 'falsy'].includes(v.op) ? '' : v.value }
    this.editor.chain().focus().command(({ tr }) => {
      tr.setNodeMarkup(pos, undefined, attrs)
      return true
    }).run()
  }

  unwrapSection(pos) {
    const node = this.editor.state.doc.nodeAt(pos)
    if (!node) return
    this.editor.chain().focus().command(({ tr }) => {
      tr.replaceWith(pos, pos + node.nodeSize, node.content)
      return true
    }).run()
  }

  // ------------------------------------------------------------- tables
  currentRow() {
    const $from = this.editor.state.selection.$from
    for (let d = $from.depth; d > 0; d--) {
      if ($from.node(d).type.name === 'tableRow') return { node: $from.node(d), pos: $from.before(d) }
    }
    return null
  }

  async repeatRow() {
    const row = this.currentRow()
    if (!row) return this.flash('Place the cursor in a table row first.')
    const scopes = this.scopesAt(row.pos)
    const v = await this.repeatDialog(scopes, { path: row.node.attrs.repeat, as: row.node.attrs.as },
      row.node.attrs.repeat ? [{ label: 'Stop repeating', action: 'stop', danger: true }] : [])
    if (!v) return
    const attrs = v.__action === 'stop'
      ? { ...row.node.attrs, repeat: null, as: null }
      : { ...row.node.attrs, repeat: v.path, as: (v.as || 'item').replace(/[^A-Za-z0-9_]/g, '_') }
    this.editor.chain().focus().command(({ tr }) => {
      tr.setNodeMarkup(row.pos, undefined, attrs)
      return true
    }).run()
  }

  tableMenu(anchor) {
    const ed = () => this.editor.chain().focus()
    const inTable = this.editor.isActive('table')
    const items = inTable
      ? [
          ['Repeat this row for each item…', () => this.repeatRow()],
          null,
          ['Add row above', () => ed().addRowBefore().run()],
          ['Add row below', () => ed().addRowAfter().run()],
          ['Delete row', () => ed().deleteRow().run()],
          null,
          ['Add column left', () => ed().addColumnBefore().run()],
          ['Add column right', () => ed().addColumnAfter().run()],
          ['Delete column', () => ed().deleteColumn().run()],
          null,
          ['Toggle header row', () => ed().toggleHeaderRow().run()],
          ['Merge cells', () => ed().mergeCells().run()],
          ['Split cell', () => ed().splitCell().run()],
          null,
          ['Delete table', () => ed().deleteTable().run()],
        ]
      : [
          ['Insert table 3 × 3', () => ed().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()],
          ['Insert table 2 × 2 (no header)', () => ed().insertTable({ rows: 2, cols: 2, withHeaderRow: false }).run()],
          ['Insert table 4 × 5', () => ed().insertTable({ rows: 5, cols: 4, withHeaderRow: true }).run()],
        ]
    const menu = h('div', { class: 'tp-menu', role: 'menu' })
    for (const it of items) {
      if (!it) { menu.append(h('div', { class: 'tp-menu__sep' })); continue }
      menu.append(h('button', { type: 'button', class: 'tp-menu__item', onMousedown: (e) => e.preventDefault(), onClick: () => { this.closePopover(); it[1]() } }, it[0]))
    }
    this.showPopover(menu, anchor.getBoundingClientRect())
  }

  // ------------------------------------------------------------- links & images
  async editLink() {
    const prev = this.editor.getAttributes('link').href || ''
    const v = await this.dialog({
      title: 'Link',
      fields: [{ name: 'href', label: 'URL', value: prev, placeholder: 'https://… or mailto:…' }],
      extraButtons: prev ? [{ label: 'Remove link', action: 'unlink', danger: true }] : [],
    })
    if (!v) return
    if (v.__action === 'unlink' || !v.href) return this.editor.chain().focus().extendMarkRange('link').unsetLink().run()
    this.editor.chain().focus().extendMarkRange('link').setLink({ href: v.href.trim() }).run()
  }

  async insertImage() {
    const v = await this.dialog({
      title: 'Image',
      fields: [
        { name: 'src', label: 'Image URL', placeholder: '/media/logo.png or https://…', help: 'PDF/DOCX output only loads images from your static/media files or allowed URL prefixes.' },
        { name: 'alt', label: 'Description (alt text)' },
        { name: 'width', label: 'Width in px (optional)', type: 'number' },
      ],
      submitLabel: 'Insert',
    })
    if (!v || !v.src) return
    this.editor.chain().focus().setImage({ src: v.src.trim(), alt: v.alt || '', ...(v.width ? { width: v.width } : {}) }).run()
  }

  // ------------------------------------------------------------- preview
  flash(message) {
    const el = h('div', { class: 'tp-flash' }, message)
    this.shell.append(el)
    setTimeout(() => el.remove(), 3200)
  }

  csrfToken() {
    const input = (this.form && this.form.querySelector('[name=csrfmiddlewaretoken]')) || document.querySelector('[name=csrfmiddlewaretoken]')
    if (input) return input.value
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
    return m ? decodeURIComponent(m[1]) : ''
  }

  async preview(fmt = 'html') {
    const types = this.activeTypes()
    const field = (name) => {
      const v = this.fieldValue(name)
      return Array.isArray(v) ? v[0] : v
    }
    const payload = {
      body: this.editor.getHTML(),
      template_type: types.length === 1 ? types[0].key : (types[0] && types[0].key) || '',
      theme: field('theme') || this.config.previewTheme || '',
      header_block: field('header_block') || '',
      footer_block: field('footer_block') || '',
      page_size: field('page_size') || '',
      orientation: field('orientation') || '',
      margin: field('margin') || '',
      extra_css: field('extra_css') || '',
      locale: field('locale') || '',
      fmt,
    }
    const modal = h('div', { class: `tp-modal tp-skin-${this.config.skin || 'default'}` })
    const frame = h('iframe', { class: 'tp-modal__frame', title: 'Preview' })
    const formats = (this.config.outputFormats || ['html', 'pdf']).filter((f) => ['html', 'pdf', 'txt'].includes(f))
    const bar = h('div', { class: 'tp-modal__bar' },
      h('strong', {}, 'Preview with sample data'),
      h('span', { class: 'tp-modal__formats' }, formats.map((f) => h('button', {
        type: 'button', class: 'tp-mini' + (f === fmt ? ' tp-mini--primary' : ''),
        onClick: () => { close(); this.preview(f) },
      }, f.toUpperCase()))),
      h('button', { type: 'button', class: 'tp-mini', onClick: () => close() }, 'Close'))
    const close = () => {
      modal.remove()
      document.removeEventListener('keydown', onKey)
    }
    const onKey = (e) => e.key === 'Escape' && close()
    document.addEventListener('keydown', onKey)
    modal.append(h('div', { class: 'tp-modal__dialog' }, bar, frame))
    modal.addEventListener('mousedown', (e) => e.target === modal && close())
    document.body.append(modal)
    frame.srcdoc = '<p style="font:14px system-ui;padding:2rem;color:#666">Rendering…</p>'
    try {
      const res = await fetch(this.config.previewUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken() },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      })
      const type = res.headers.get('Content-Type') || ''
      if (type.includes('application/pdf')) {
        const blob = await res.blob()
        frame.removeAttribute('srcdoc')
        frame.src = URL.createObjectURL(blob)
      } else if (type.includes('text/plain')) {
        const text = await res.text()
        const esc = text.replace(/&/g, '&amp;').replace(/</g, '&lt;')
        frame.srcdoc = `<pre style="font:13px/1.5 ui-monospace,monospace;padding:1.5rem;white-space:pre-wrap">${esc}</pre>`
      } else {
        frame.srcdoc = await res.text()
      }
    } catch (e) {
      frame.srcdoc = `<p style="font:14px system-ui;padding:2rem;color:#a00">Preview failed: ${String(e)}</p>`
    }
  }
}
