import type { ParsedSchema, GenerationResult, QueryResult } from './store'

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
