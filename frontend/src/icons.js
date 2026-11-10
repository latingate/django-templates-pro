// Small inline SVG icons (drawn for this project; 24x24 viewBox, stroke = currentColor).
const svg = (body) =>
  `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`

export const icons = {
  undo: svg('<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>'),
  redo: svg('<path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/>'),
  bold: svg('<path d="M7 4h6a4 4 0 0 1 0 8H7z"/><path d="M7 12h7a4 4 0 0 1 0 8H7z"/>'),
  italic: svg('<path d="M14 4h-4M14 20h-4M15 4 9 20"/>'),
  underline: svg('<path d="M7 4v7a5 5 0 0 0 10 0V4"/><path d="M5 21h14"/>'),
  strike: svg('<path d="M4 12h16"/><path d="M16 6.5A4.5 3.5 0 0 0 8 8c0 4 8 2 8 6a4.5 3.5 0 0 1-8.5 1.5"/>'),
  alignLeft: svg('<path d="M4 6h16M4 10h10M4 14h16M4 18h10"/>'),
  alignCenter: svg('<path d="M4 6h16M7 10h10M4 14h16M7 18h10"/>'),
  alignRight: svg('<path d="M4 6h16M10 10h10M4 14h16M10 18h10"/>'),
  alignJustify: svg('<path d="M4 6h16M4 10h16M4 14h16M4 18h16"/>'),
  bulletList: svg('<circle cx="5" cy="7" r="1"/><circle cx="5" cy="12" r="1"/><circle cx="5" cy="17" r="1"/><path d="M9 7h11M9 12h11M9 17h11"/>'),
  orderedList: svg('<path d="M4 6h1v4M4 10h2M4 14h2l-2 3h2"/><path d="M10 7h10M10 12h10M10 17h10"/>'),
  blockquote: svg('<path d="M6 17h3l2-4V7H5v6h3zM14 17h3l2-4V7h-6v6h3z"/>'),
  hr: svg('<path d="M3 12h18"/><path d="M8 7h8M8 17h8" opacity=".4"/>'),
  link: svg('<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'),
  image: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>'),
  table: svg('<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M3 15h18M9 4v16M15 4v16"/>'),
  highlight: svg('<path d="m9 11 6-6 4 4-6 6z"/><path d="M9 11 5 15v4h4l4-4"/><path d="M3 21h8"/>'),
  clear: svg('<path d="M5 5h11M10 5 7 19"/><path d="m14 14 6 6M20 14l-6 6"/>'),
  eye: svg('<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
  expand: svg('<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>'),
  field: svg('<path d="M8 4c-2 0-3 1-3 3v2c0 1-1 2-2 3 1 1 2 2 2 3v2c0 2 1 3 3 3M16 4c2 0 3 1 3 3v2c0 1 1 2 2 3-1 1-2 2-2 3v2c0 2-1 3-3 3"/>'),
  constant: svg('<path d="m12 3 8 9-8 9-8-9z"/>'),
  clock: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  block: svg('<rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1" stroke-dasharray="2 2"/>'),
  repeat: svg('<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 0 1 4-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 0 1-4 4H4"/>'),
  condition: svg('<path d="M6 3v6a3 3 0 0 0 3 3h6a3 3 0 0 1 3 3v6"/><path d="M18 3v6"/><circle cx="18" cy="3" r="0.5"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
}
