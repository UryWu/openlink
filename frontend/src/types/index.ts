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


export interface SummaryStats {
  count: number
  inputTokens: number
  outputTokens: number
  totalTokens: number
}

export interface DayStat {
  date: string
  inputTokens: number
  outputTokens: number
}

export interface PlatformStat {
  platform: string
  count: number
  tokens: number
}

export interface RecentItem {
  ts: number
  platform: string
  user: string
  inputTokens: number
  outputTokens: number
}

export interface StatsResponse {
  summary: SummaryStats
  byDay: DayStat[]
  byHour: DayStat[]
  byPlatform: PlatformStat[]
  recent: RecentItem[]
}


export interface ConversationMeta {
  convId: string
  platform: string
  count: number
  firstTs: number
  lastTs: number
  inputTokens: number
  outputTokens: number
  totalTokens: number
}


export interface ConversationMeta {
  convId: string
  platform: string
  count: number
  firstTs: number
  lastTs: number
  inputTokens: number
  outputTokens: number
  totalTokens: number
}

export interface MessageItem {
  ts: number
  platform: string
  user: string
  inputTokens: number
  outputTokens: number
}

export interface MessagePage {
  total: number
  offset: number
  limit: number
  items: MessageItem[]
}
