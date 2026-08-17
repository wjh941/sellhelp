import { createApp } from 'vue'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'

import App from './App.vue'
import router from './router'
import './styles/main.scss'
import { readTheme } from './utils/operationUi'

const app = createApp(App)
document.documentElement.dataset.theme = readTheme(localStorage)

app.use(router)
app.mount('#app')
