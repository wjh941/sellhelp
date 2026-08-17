<template>
  <section class="page-card accounts-page">
    <div class="page-header">
      <div>
        <h2>账户管理</h2>
        <p class="page-description">创建业务账户、重置密码并分配系统角色。</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建账户
      </el-button>
    </div>

    <el-alert title="角色权限由服务端强制执行。修改角色后，该账户现有登录状态会失效。" type="info" :closable="false" show-icon class="accounts-note" />

    <el-table v-loading="loading" :data="users" class="data-table" empty-text="暂无账户">
      <el-table-column prop="username" label="账户名" min-width="150" />
      <el-table-column prop="display_name" label="显示名称" min-width="160" />
      <el-table-column label="角色" min-width="260">
        <template #default="{ row }">
          <el-tag v-for="role in row.role_codes" :key="role" effect="plain" class="role-tag">{{ roleName(role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }"><el-button link type="primary" @click="openEdit(row)">编辑</el-button></template>
      </el-table-column>
    </el-table>
  </section>

  <el-dialog v-model="dialogVisible" :title="editingUser ? '编辑账户' : '新建账户'" width="min(560px, 94vw)" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="account-form">
      <el-form-item label="账户名" prop="username">
        <el-input v-model.trim="form.username" :disabled="Boolean(editingUser)" autocomplete="off" placeholder="仅支持字母、数字、点、下划线和连字符" />
      </el-form-item>
      <el-form-item label="显示名称" prop="display_name"><el-input v-model.trim="form.display_name" placeholder="用于顶部操作员显示" /></el-form-item>
      <el-form-item :label="editingUser ? '新密码（留空不修改）' : '初始密码'" :prop="editingUser ? undefined : 'password'">
        <el-input v-model="form.password" type="password" show-password autocomplete="new-password" placeholder="至少 8 个字符" />
      </el-form-item>
      <el-form-item label="角色" prop="role_codes">
        <el-checkbox-group v-model="form.role_codes" class="role-options">
          <el-checkbox v-for="role in roles" :key="role.code" :value="role.code">
            <span>{{ role.name }}</span>
            <small>{{ role.description }}</small>
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveUser">保存账户</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { createUser, getRoles, getUsers, updateUser } from '@/api'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingUser = ref(null)
const formRef = ref()
const users = ref([])
const roles = ref([])
const emptyForm = () => ({ username: '', display_name: '', password: '', role_codes: [] })
const form = reactive(emptyForm())
const rules = {
  username: [
    { required: true, message: '请输入账户名', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_.-]+$/, message: '账户名格式不正确', trigger: 'blur' },
  ],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  password: [{ required: true, min: 8, message: '初始密码至少 8 个字符', trigger: 'blur' }],
  role_codes: [{ type: 'array', required: true, min: 1, message: '至少选择一个角色', trigger: 'change' }],
}

const roleName = code => roles.value.find(role => role.code === code)?.name || code

const loadData = async () => {
  loading.value = true
  try {
    const [userRows, roleRows] = await Promise.all([getUsers(), getRoles()])
    users.value = userRows
    roles.value = roleRows
  } finally {
    loading.value = false
  }
}

const resetForm = () => Object.assign(form, emptyForm())

const openCreate = () => {
  editingUser.value = null
  resetForm()
  dialogVisible.value = true
}

const openEdit = user => {
  editingUser.value = user
  Object.assign(form, { username: user.username, display_name: user.display_name, password: '', role_codes: [...user.role_codes] })
  dialogVisible.value = true
}

const saveUser = async () => {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editingUser.value) {
      const payload = { display_name: form.display_name, role_codes: form.role_codes }
      if (form.password) payload.password = form.password
      await updateUser(editingUser.value.id, payload)
      ElMessage.success('账户已更新')
    } else {
      await createUser({ ...form, role_codes: [...form.role_codes] })
      ElMessage.success('账户已创建')
    }
    dialogVisible.value = false
    await loadData()
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.page-description {
  color: var(--color-muted);
  margin-top: 6px;
}

.accounts-note {
  margin-bottom: 18px;
}

.role-tag + .role-tag { margin-left: 6px; }

.role-options {
  display: grid;
  gap: 10px;
}

.role-options :deep(.el-checkbox) {
  align-items: flex-start;
  height: auto;
  margin-right: 0;
  white-space: normal;
}

.role-options small {
  color: var(--color-muted);
  display: block;
  line-height: 1.5;
  margin-top: 2px;
}
</style>
