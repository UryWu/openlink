/** Shared types matching backend Pydantic models. */

export interface ToolRequest {
  name: string
  args: Record<string, unknown>
  /** OpenAI compat — merged with args by backend */
  arguments?: Record<string, unknown>
}

export interface ToolResponse {
  status: 'success' | 'error'
  output: string
  error: string
  /** CamelCase alias for JSON */
  stopStream?: boolean
}

export interface HealthResponse {
  status: string
  dir: string
  version: string
  hostname?: string
  time?: string
  os?: string
  arch?: string
}

export interface AuthResponse {
  valid: boolean
}

export interface ServerConfig {
  root_dir: string
  port: number
  timeout: number
}

export interface ToolInfo {
  name: string
  description: string
  parameters: unknown
}

export interface SkillInfo {
  name: string
  description: string
  source?: string
}

export interface FileItem {
  name: string
  path: string
  size: number
  is_dir: boolean
  modified: string
}
