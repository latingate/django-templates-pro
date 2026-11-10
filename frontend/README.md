# Editor bundle

TipTap 3 + Vite, vanilla JS. Builds one IIFE (`window.TemplatesPro`) and one CSS file into
`../src/templates_pro/static/templates_pro/editor/`.

```bash
npm install
npm run build      # production bundle (commit the output)
npm run watch      # development, with source maps
npm run contract   # round-trip demo samples through the editor schema → tests/fixtures/
```

- `src/extensions.js`: custom nodes. Their rendered HTML is the contract with the Python compiler.
- `src/editor.js`: toolbar, picker, popovers, dialogs, preview.
- `src/editor.css`: skins (`default`, `dark`, `paper`, `compact`) via CSS custom properties.
- `src/index.js`: auto-initialisation and the public JS API.
