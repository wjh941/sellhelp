import { reactive } from 'vue'
import { getCurrentUser, login as loginRequest, logout as logoutRequest, setAuthToken } from '@/api'

const authState = reactive({
  initialized: false,
  loading: false,
  user: null,
  standalone_mode: false,
})

let initialization = null

export const routeRoles = {
  Dashboard: ['owner', 'warehouse_operator', 'sales_clerk'],
  Products: ['owner'],
  Suppliers: ['owner'],
  Customers: ['owner'],
  Purchase: ['owner', 'warehouse_operator'],
  Sales: ['owner', 'sales_clerk'],
  Stock: ['owner', 'warehouse_operator'],
  StockAnalysis: ['owner', 'warehouse_operator'],
  Returns: ['owner', 'warehouse_operator'],
  Finance: ['owner', 'sales_clerk'],
  Market: ['owner'],
  Pricing: ['owner'],
  Reports: ['owner'],
  AIChat: ['owner'],
  Settings: ['owner'],
  Accounts: ['owner'],
  AuditLogs: ['owner'],
}

const applyIdentity = (identity, token = null) => {
  setAuthToken(token)
  authState.user = identity
  authState.standalone_mode = Boolean(identity?.standalone_mode)
  authState.initialized = true
}

export const clearAuthentication = () => applyIdentity(null)

export const initializeAuthentication = async (force = false) => {
  if (authState.initialized && !force) return Boolean(authState.user)
  if (initialization) return initialization

  authState.loading = true
  initialization = getCurrentUser()
    .then(identity => {
      applyIdentity(identity)
      return true
    })
    .catch(() => {
      clearAuthentication()
      return false
    })
    .finally(() => {
      authState.loading = false
      initialization = null
    })
  return initialization
}

export const signIn = async (credentials) => {
  const response = await loginRequest(credentials)
  applyIdentity(response, response.access_token)
  return response
}

export const signOut = async () => {
  try {
    if (!authState.standalone_mode && authState.user) await logoutRequest()
  } finally {
    clearAuthentication()
  }
}

export const hasRole = (role) => authState.standalone_mode || authState.user?.role_codes?.includes(role)

export const canAccessRoute = (routeName) => {
  const allowed = routeRoles[routeName]
  return Boolean(allowed?.some(hasRole))
}

export const useAuth = () => ({
  state: authState,
  canAccessRoute,
  hasRole,
  initializeAuthentication,
  signIn,
  signOut,
})
