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

export interface NodePropInfo {
  name: string
  type_category: string
}

export interface NodeInfo {
  label: string
  properties: NodePropInfo[]
  unique_properties: string[]
}

export interface RelationshipInfo {
  type: string
  from_label: string
  to_label: string
  properties: NodePropInfo[]
}

export interface ParsedSchema {
  schema_id: string
  schema_type: string
  dialect: string
  tables: TableInfo[]
  nodes: NodeInfo[]
  relationships: RelationshipInfo[]
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

export interface CypherQueryResult {
  rows: Record<string, unknown>[]
  count: number
}

export interface MysqlConfig {
  host: string
  port: number
  database: string
  user: string
  password: string
}

export interface LLMConfig {
  base_url: string
  api_key: string
  model: string
  temperature: number
}

export interface WsProgressEvent {
  type: string
  stage?: string
  table?: string
  percent?: number
  count?: number
  message?: string
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

  // MySQL connection config
  mysqlConfig: MysqlConfig | null

  // AI / LLM config
  aiConfig: LLMConfig | null
  wsProgress: WsProgressEvent[]
  wsGenerating: boolean

  // SQL Explorer
  sqlQuery: string
  queryResult: QueryResult | null
  queryError: string | null

  // Graph / Cypher
  cypherSource: string
  parsedGraphSchema: ParsedSchema | null
  graphParseError: string | null
  graphRowCounts: Record<string, number>
  graphGenerationResult: GenerationResult | null
  cypherQuery: string
  cypherResult: CypherQueryResult | null
  cypherError: string | null

  // Actions
  setDdlSource: (src: string) => void
  setDialect: (d: string) => void
  setParsedSchema: (s: ParsedSchema | null) => void
  setParseError: (e: string | null) => void
  setRowCount: (table: string, n: number) => void
  setGenerationResult: (r: GenerationResult | null) => void
  setMysqlConfig: (cfg: MysqlConfig | null) => void
  setAiConfig: (cfg: LLMConfig | null) => void
  setWsProgress: (p: WsProgressEvent[]) => void
  setWsGenerating: (b: boolean) => void
  setSqlQuery: (q: string) => void
  setQueryResult: (r: QueryResult | null) => void
  setQueryError: (e: string | null) => void
  setCypherSource: (src: string) => void
  setParsedGraphSchema: (s: ParsedSchema | null) => void
  setGraphParseError: (e: string | null) => void
  setGraphRowCount: (name: string, n: number) => void
  setGraphGenerationResult: (r: GenerationResult | null) => void
  setCypherQuery: (q: string) => void
  setCypherResult: (r: CypherQueryResult | null) => void
  setCypherError: (e: string | null) => void
  resetAll: () => void
}

const DEFAULT_CYPHER = `CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE;
CREATE CONSTRAINT ON (p:Post) ASSERT p.id IS UNIQUE;
// (:User {id: INT, username: STRING, email: STRING})
// (:Post {id: INT, content: STRING, likes: INT})
// (:Tag  {id: INT, name: STRING})
// (:User)-[:FOLLOWS {since: DATE}]->(:User)
// (:User)-[:AUTHORED]->(:Post)
// (:Post)-[:TAGGED_WITH]->(:Tag)`

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

  mysqlConfig: null,

  aiConfig: null,
  wsProgress: [],
  wsGenerating: false,

  sqlQuery: 'SELECT * FROM users LIMIT 10;',
  queryResult: null,
  queryError: null,

  cypherSource: DEFAULT_CYPHER,
  parsedGraphSchema: null,
  graphParseError: null,
  graphRowCounts: {},
  graphGenerationResult: null,
  cypherQuery: 'MATCH (u:User) RETURN count(u) AS cnt',
  cypherResult: null,
  cypherError: null,

  setDdlSource: (src) => set({ ddlSource: src }),
  setDialect: (d) => set({ dialect: d }),
  setParsedSchema: (s) => set({ parsedSchema: s }),
  setParseError: (e) => set({ parseError: e }),
  setRowCount: (table, n) =>
    set((state) => ({ rowCounts: { ...state.rowCounts, [table]: n } })),
  setGenerationResult: (r) => set({ generationResult: r }),
  setMysqlConfig: (cfg) => set({ mysqlConfig: cfg }),
  setAiConfig: (cfg) => set({ aiConfig: cfg }),
  setWsProgress: (p) => set({ wsProgress: p }),
  setWsGenerating: (b) => set({ wsGenerating: b }),
  setSqlQuery: (q) => set({ sqlQuery: q }),
  setQueryResult: (r) => set({ queryResult: r }),
  setQueryError: (e) => set({ queryError: e }),
  setCypherSource: (src) => set({ cypherSource: src }),
  setParsedGraphSchema: (s) => set({ parsedGraphSchema: s }),
  setGraphParseError: (e) => set({ graphParseError: e }),
  setGraphRowCount: (name, n) =>
    set((state) => ({ graphRowCounts: { ...state.graphRowCounts, [name]: n } })),
  setGraphGenerationResult: (r) => set({ graphGenerationResult: r }),
  setCypherQuery: (q) => set({ cypherQuery: q }),
  setCypherResult: (r) => set({ cypherResult: r }),
  setCypherError: (e) => set({ cypherError: e }),
  resetAll: () =>
    set({
      ddlSource: '',
      parsedSchema: null,
      parseError: null,
      rowCounts: {},
      generationResult: null,
      queryResult: null,
      queryError: null,
      parsedGraphSchema: null,
      graphParseError: null,
      graphRowCounts: {},
      graphGenerationResult: null,
      cypherResult: null,
      cypherError: null,
    }),
}))
