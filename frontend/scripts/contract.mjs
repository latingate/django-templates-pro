// Contract check between the editor and the Python compiler.
//
// 1. Parses every sample template/block through the real TipTap schema
//    (with our custom nodes) and serialises it back with getHTML(), exactly
//    like the browser does.
// 2. Writes the results to tests/fixtures/editor_roundtrip/*.html.
// tests/test_contract.py then compiles each file and asserts the output is
// identical to compiling the original sample.
//
//   npm run contract
import { readFileSync, writeFileSync, readdirSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Window } from 'happy-dom'

const win = new Window()
for (const k of ['window', 'document', 'navigator', 'Node', 'HTMLElement', 'DOMParser', 'Element', 'getComputedStyle', 'MutationObserver']) {
  Object.defineProperty(globalThis, k, { value: k === 'window' ? win : win[k], configurable: true, writable: true })
}

const { Editor } = await import('@tiptap/core')
const StarterKit = (await import('@tiptap/starter-kit')).default
const TextAlign = (await import('@tiptap/extension-text-align')).default
const { TextStyle, Color, FontSize } = await import('@tiptap/extension-text-style')
const Highlight = (await import('@tiptap/extension-highlight')).default
const Image = (await import('@tiptap/extension-image')).default
const { Table, TableCell, TableHeader } = await import('@tiptap/extension-table')
const ext = await import('../src/extensions.js')

const here = dirname(fileURLToPath(import.meta.url))
const samples = join(here, '../../example/demo/samples')
const out = join(here, '../../tests/fixtures/editor_roundtrip')
mkdirSync(out, { recursive: true })

const extensions = [
  StarterKit.configure({ heading: { levels: [1, 2, 3, 4] }, link: { openOnClick: false } }),
  TextStyle, Color, FontSize, Highlight.configure({ multicolor: true }),
  TextAlign.configure({ types: ['heading', 'paragraph'] }), Image.configure({ allowBase64: true }),
  Table.configure({ resizable: false }), ext.TpTableRow, TableHeader, TableCell,
  ext.TpVariable, ext.TpConstant, ext.TpDynamic, ext.TpBlock, ext.TpRepeat, ext.TpIf,
]

let n = 0
for (const kind of ['templates', 'blocks']) {
  for (const file of readdirSync(join(samples, kind)).filter((f) => f.endsWith('.html'))) {
    const src = readFileSync(join(samples, kind, file), 'utf8')
    const editor = new Editor({ extensions, content: src, element: document.createElement('div') })
    writeFileSync(join(out, `${kind}--${file}`), editor.getHTML())
    editor.destroy()
    n++
  }
}
console.log(`wrote ${n} round-tripped samples to tests/fixtures/editor_roundtrip/`)
