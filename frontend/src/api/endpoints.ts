import axios from 'axios'
import type {
  HealthResponse,
  AuthResponse,
  ServerConfig,
  ToolInfo,
  ToolRequest,
  ToolResponse,
  SkillInfo,
  FileItem,
} from '@/types'

/** Singleton Axios instance that reads the token from localStorage each request. */

const api = axios.create({
  baseURL: '/',          // proxied by Vite dev server or served by FastAPI
  timeout: 30_000,
})

// ── Interceptor: inject Bearer token ────────────────────────────────────

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('openlink-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Typed endpoint functions ─────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health')
  return data
}

export async function fetchAuth(token: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth', null, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

export async function fetchConfig(): Promise<ServerConfig> {
  const { data } = await api.get<ServerConfig>('/config')
  return data
}

export async function fetchTools(): Promise<ToolInfo[]> {
  const { data } = await api.get<ToolInfo[]>('/tools')
  return data
}

export async function fetchPrompt(): Promise<string> {
  const { data } = await api.get<string>('/prompt', {
    transformResponse: [(d) => d], // keep as raw text
  })
  return data
}

export async function fetchSkills(): Promise<SkillInfo[]> {
  const { data } = await api.get<SkillInfo[]>('/skills')
  return data
}

export async function fetchFiles(query?: string): Promise<FileItem[]> {
  const { data } = await api.get<FileItem[]>('/files', {
    params: query ? { q: query } : {},
  })
  return data
}

export async function execTool(req: ToolRequest): Promise<ToolResponse> {
  const { data } = await api.post<ToolResponse>('/exec', req)
  return data
}

export default api
