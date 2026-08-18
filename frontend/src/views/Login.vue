<template>
  <main class="login-page">
    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-brand">
        <el-icon><Shop /></el-icon>
        <span>盈泰副食</span>
      </div>
      <div class="login-heading">
        <h1 id="login-title">登录业务系统</h1>
        <p>使用已分配的账户进入对应业务工作区。</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="账户名" prop="username">
          <el-input v-model.trim="form.username" autocomplete="username" placeholder="输入账户名" :prefix-icon="User" @keyup.enter="submit" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" placeholder="输入密码" :prefix-icon="Lock" @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" native-type="submit" class="login-submit" :loading="submitting">登录</el-button>
      </el-form>
      <el-button v-if="canInitialize" text class="bootstrap-trigger" @click="showBootstrap = true">初始化管理员</el-button>

      <el-dialog v-model="showBootstrap" title="初始化管理员" append-to-body width="min(440px, calc(100vw - 32px))">
        <el-form ref="bootstrapFormRef" :model="bootstrapForm" :rules="rules" label-position="top">
          <el-form-item label="账户名" prop="username"><el-input v-model.trim="bootstrapForm.username" /></el-form-item>
          <el-form-item label="显示名称" prop="display_name"><el-input v-model.trim="bootstrapForm.display_name" /></el-form-item>
          <el-form-item label="密码" prop="password"><el-input v-model="bootstrapForm.password" type="password" show-password /></el-form-item>
        </el-form>
        <template #footer><el-button @click="showBootstrap = false">取消</el-button><el-button type="primary" :loading="bootstrapping" @click="bootstrap">创建管理员</el-button></template>
      </el-dialog>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock, Shop, User } from '@element-plus/icons-vue'
import { bootstrapOwner, getBootstrapStatus } from '@/api'
import { useAuth } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuth()
const formRef = ref()
const submitting = ref(false)
const bootstrapping = ref(false)
const canInitialize = ref(false)
const showBootstrap = ref(false)
const form = reactive({ username: '', password: '' })
const bootstrapFormRef = ref()
const bootstrapForm = reactive({ username: 'admin', display_name: '管理员', password: 'SellHelp@2026!' })
const rules = {
  username: [{ required: true, message: '请输入账户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

onMounted(async () => { canInitialize.value = Boolean((await getBootstrapStatus()).can_initialize) })

const submit = async () => {
  await formRef.value?.validate()
  submitting.value = true
  try {
    await auth.signIn(form)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect)
  } catch {
    // The API interceptor shows the authentication error.
  } finally {
    submitting.value = false
  }
}

const bootstrap = async () => {
  await bootstrapFormRef.value?.validate()
  bootstrapping.value = true
  try {
    await bootstrapOwner(bootstrapForm)
    await auth.signIn({ username: bootstrapForm.username, password: bootstrapForm.password })
    router.replace('/')
  } finally {
    bootstrapping.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  align-items: center;
  background: var(--color-page);
  display: flex;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.login-panel {
  background: var(--color-surface);
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(29, 33, 41, 0.12);
  max-width: 420px;
  padding: 36px;
  width: 100%;
}

.login-brand {
  align-items: center;
  color: var(--color-text);
  display: flex;
  font-size: 18px;
  font-weight: 700;
  gap: 10px;

  .el-icon {
    color: var(--color-primary);
    font-size: 26px;
  }
}

.login-heading {
  margin: 30px 0 24px;

  h1 {
    font-size: 24px;
    font-weight: 700;
    line-height: 1.25;
  }

  p {
    color: var(--color-muted);
    line-height: 1.65;
    margin-top: 8px;
  }
}

.login-submit {
  margin-top: 8px;
  width: 100%;
}

@media (max-width: 480px) {
  .login-page { padding: 16px; }
  .login-panel { padding: 28px 22px; }
}
</style>
