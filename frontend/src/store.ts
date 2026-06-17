import { create } from 'zustand'

export interface ColumnInfo {
  name: string
  type_category: string
  nullable: boolean
  primary_key: boolean
  auto_increment: boolean
  unique: boolean
  length: number | null
  enum_values: string[] | null
}

export interface ForeignKeyInfo {
  column: string
  ref_table: string
  ref_column: string
}

export interface TableInfo {
  name: string
  columns: ColumnInfo[]
  primary_key: string[]
  foreign_keys: ForeignKeyInfo[]
}

export interface GenerationStep {
  step: number
  name: string
  kind: 'table' | 'node' | 'relationship'
}

export interface ParsedSchema {
  schema_id: string
  schema_type: string
  dialect: string
  tables: TableInfo[]
  nodes: unknown[]
  relationships: unknown[]
  generation_order: GenerationStep[]
}

export interface GenerationResult {
  schema_id: string
  tables: Record<string, { generated: number }>
  ai_used: boolean
  generation_meta: { chunk_size: number; chunks_total: number }
}

export interface QueryResult {
  rows: Record<string, unknown>[]
  count: number
}

interface AppState {
  // DDL source
  ddlSource: string
  dialect: string
  parsedSchema: ParsedSchema | null
  parseError: string | null

  // Generation config
  rowCounts: Record<string, number>
  generationResult: GenerationResult | null

  // SQL Explorer
  sqlQuery: string
  queryResult: QueryResult | null
  queryError: string | null

  // Actions
  setDdlSource: (src: string) => void
  setDialect: (d: string) => void
  setParsedSchema: (s: ParsedSchema | null) => void
  setParseError: (e: string | null) => void
  setRowCount: (table: string, n: number) => void
  setGenerationResult: (r: GenerationResult | null) => void
  setSqlQuery: (q: string) => void
  setQueryResult: (r: QueryResult | null) => void
  setQueryError: (e: string | null) => void
  resetAll: () => void
}

export const useAppStore = create<AppState>((set) => ({
  ddlSource: `CREATE TABLE users (
  id       INT          NOT NULL AUTO_INCREMENT,
  email    VARCHAR(120) NOT NULL UNIQUE,
  username VARCHAR(50)  NOT NULL UNIQUE,
  PRIMARY KEY (id)
);`,
  dialect: 'mysql',
  parsedSchema: null,
  parseError: null,

  rowCounts: {},
  generationResult: null,

  sqlQuery: 'SELECT * FROM users LIMIT 10;',
  queryResult: null,
  queryError: null,

  setDdlSource: (src) => set({ ddlSource: src }),
  setDialect: (d) => set({ dialect: d }),
  setParsedSchema: (s) => set({ parsedSchema: s }),
  setParseError: (e) => set({ parseError: e }),
  setRowCount: (table, n) =>
    set((state) => ({ rowCounts: { ...state.rowCounts, [table]: n } })),
  setGenerationResult: (r) => set({ generationResult: r }),
  setSqlQuery: (q) => set({ sqlQuery: q }),
  setQueryResult: (r) => set({ queryResult: r }),
  setQueryError: (e) => set({ queryError: e }),
  resetAll: () =>
    set({
      ddlSource: '',
      parsedSchema: null,
      parseError: null,
      rowCounts: {},
      generationResult: null,
      queryResult: null,
      queryError: null,
    }),
}))
