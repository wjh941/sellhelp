import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8001'

const elementPlusIconNames = new Set([
  'ArrowDown', 'Box', 'ChatDotRound', 'Check', 'Close', 'Delete', 'Document', 'DocumentChecked',
  'Download', 'EditPen', 'Expand', 'Fold', 'FolderOpened', 'Goods', 'Histogram', 'Money', 'Moon',
  'Odometer', 'OfficeBuilding', 'PieChart', 'Plus', 'Printer', 'Promotion', 'Rank', 'Refresh',
  'RefreshLeft', 'Search', 'Setting', 'Shop', 'Sunny', 'SwitchButton', 'Tickets', 'TrendCharts',
  'Upload', 'User', 'UserFilled', 'Wallet', 'WarningFilled',
])

const elementPlusIconResolver = (name) => {
  if (elementPlusIconNames.has(name)) return { name, from: '@element-plus/icons-vue' }
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
    fs: {
      allow: [path.resolve(__dirname)],
    },
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true
      }
    }
  }
})
