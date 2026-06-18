import type { ParsedSchema, GenerationResult, QueryResult, CypherQueryResult } from './store'

const BASE = '/api'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const text = await res.text()
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 300)}`)
  }
  if (!res.ok) throw new Error((data as { detail?: string }).detail ?? `HTTP ${res.status}`)
  return data as T
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`)
  return data as T
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const text = await res.text()
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 300)}`)
  }
  if (!res.ok) throw new Error((data as { detail?: string }).detail ?? `HTTP ${res.status}`)
  return data as T
}

export async function parseDdl(
  source: string,
  dialect: string,
): Promise<ParsedSchema> {
  return post('/parse', { source, type: 'ddl', dialect })
}

export async function generateData(
  schema_id: string,
  row_counts: Record<string, number>,
): Promise<GenerationResult> {
  return post('/generate', { schema_id, row_counts })
}

export async function runSql(sql: string): Promise<QueryResult> {
  return post<QueryResult>('/db/sql', { sql })
}

export async function getDbTables(): Promise<{ tables: unknown[] }> {
  return get('/db/tables')
}

export async function resetAll(schema_id?: string): Promise<void> {
  await post('/reset', { schema_id: schema_id ?? null })
}

export async function parseCypher(source: string): Promise<ParsedSchema> {
  return post('/parse', { source, type: 'cypher' })
}

export async function getGraphSchema(): Promise<{
  nodes: { label: string; properties: { name: string; type_category: string }[] }[]
  relationships: { type: string; from_label: string; to_label: string }[]
}> {
  return get('/graph/schema')
}

export async function getGraphStats(): Promise<{
  node_counts: Record<string, number>
  rel_counts: Record<string, number>
}> {
  return get('/graph/stats')
}

export async function runCypher(cypher: string): Promise<CypherQueryResult> {
  return post('/graph/cypher', { cypher })
}

export interface LLMTestResult {
  ok: boolean
  base_url: string
  model: string
  reachable: boolean
}

export async function testLlm(config: {
  base_url: string
  api_key: string
  model: string
  temperature: number
}): Promise<LLMTestResult> {
  return post('/ai/test-llm', config)
}

// ── Table relationships ──────────────────────────────────────────────────────

export interface RelationItem {
  child_table: string
  child_col: string
  parent_table: string
  parent_col: string
  note?: string
}

export interface RelationsResponse {
  schema_id: string
  relations: RelationItem[]
  ai_used: boolean
}

export async function inferRelations(
  schema_id: string,
  ai_enabled: boolean,
  llm_config?: { base_url: string; api_key: string; model: string } | null,
): Promise<RelationsResponse> {
  return post('/relations/infer', { schema_id, ai_enabled, llm_config: llm_config ?? null })
}

export async function getRelations(schema_id: string): Promise<RelationsResponse> {
  return get(`/relations?schema_id=${encodeURIComponent(schema_id)}`)
}

export async function updateRelations(
  schema_id: string,
  relations: RelationItem[],
): Promise<RelationsResponse> {
  return put('/relations', { schema_id, relations })
}

export function exportRelationsUrl(schema_id: string): string {
  return `${BASE}/relations/export?schema_id=${encodeURIComponent(schema_id)}`
}

export async function importRelationsCypher(
  schema_id: string,
  cypher: string,
  replace = false,
): Promise<RelationsResponse> {
  return post('/relations/import', { schema_id, cypher, replace })
}

// ── Custom generation rules (natural language → specs) ───────────────────────

export type FieldSpec = { kind: string; [k: string]: unknown }

export interface RulesResponse {
  schema_id: string
  field_specs: Record<string, FieldSpec>
}

export async function translateRules(
  schema_id: string,
  text: string,
  llm_config?: { base_url: string; api_key: string; model: string } | null,
): Promise<RulesResponse> {
  return post('/rules/translate', { schema_id, text, llm_config: llm_config ?? null })
}

export async function getRules(schema_id: string): Promise<RulesResponse> {
  return get(`/rules?schema_id=${encodeURIComponent(schema_id)}`)
}

export async function updateRules(
  schema_id: string,
  field_specs: Record<string, FieldSpec>,
): Promise<RulesResponse> {
  return put('/rules', { schema_id, field_specs })
}

export async function inferRulesFromSamples(
  schema_id: string,
  source_type: 'sql' | 'csv',
  content: string,
  table?: string | null,
): Promise<RulesResponse> {
  return post('/rules/from-samples', { schema_id, source_type, content, table: table ?? null })
}

export interface WsMessage {
  type: 'progress' | 'preview' | 'done' | 'error'
  stage?: string
  table?: string
  percent?: number
  count?: number
  rows?: Record<string, unknown>[]
  tables?: Record<string, { generated: number }>
  ai_used?: boolean
  message?: string
}

export function openGenerateStream(
  schema_id: string,
  row_counts: Record<string, number>,
  ai_enabled: boolean,
  onMessage: (msg: WsMessage) => void,
  onClose?: () => void,
): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${proto}//${window.location.host}/ws/generate`)
  ws.onopen = () => {
    ws.send(JSON.stringify({ schema_id, row_counts, ai_enabled }))
  }
  ws.onmessage = (event) => {
    try {
      const msg: WsMessage = JSON.parse(event.data as string)
      onMessage(msg)
    } catch { /* ignore malformed */ }
  }
  ws.onclose = () => onClose?.()
  ws.onerror = () => onMessage({ type: 'error', message: 'WebSocket error' })
  return ws
}
