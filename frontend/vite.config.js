import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import path from 'path'

const elementPlusIconResolver = (name) => {
  if (name in ElementPlusIconsVue) return { name, from: '@element-plus/icons-vue' }
}

export default defineConfig({
  plugins: [
    vue(),
    Components({
      dts: false,
      resolvers: [ElementPlusResolver({ importStyle: 'sass' }), elementPlusIconResolver],
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 8080,
    strictPort: true,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true
      }
    }
  }
})
