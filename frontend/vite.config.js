import { defineConfig } from 'vite'
import { resolve } from 'node:path'

// Builds a single IIFE bundle (global `TemplatesPro`) straight into the Django
// app's static directory, so projects using the package need no Node toolchain.
export default defineConfig(({ mode }) => ({
  build: {
    outDir: resolve(__dirname, '../src/templates_pro/static/templates_pro/editor'),
    emptyOutDir: true,
    sourcemap: mode === 'development',
    minify: mode !== 'development',
    lib: {
      entry: resolve(__dirname, 'src/index.js'),
      name: 'TemplatesPro',
      formats: ['iife'],
      fileName: () => 'templates-pro-editor.js',
      cssFileName: 'templates-pro-editor',
    },
  },
}))
