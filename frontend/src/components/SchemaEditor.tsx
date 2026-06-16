import { useState } from 'react'
import { Button, Select, Alert, Typography, Space, Tag } from 'antd'
import { CodeOutlined, TableOutlined } from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { useAppStore } from '../store'
import { parseDdl } from '../api'

const DIALECTS = ['mysql', 'postgresql', 'sqlite', 'tsql', 'oracle', 'bigquery']

export default function SchemaEditor() {
  const {
    ddlSource, setDdlSource,
    dialect, setDialect,
    setParsedSchema, setParseError,
    parseError, parsedSchema,
    rowCounts, setRowCount,
  } = useAppStore()

  const [loading, setLoading] = useState(false)

  async function handleParse() {
    setLoading(true)
    setParseError(null)
    try {
      const schema = await parseDdl(ddlSource, dialect)
      setParsedSchema(schema)
      // Initialize row counts for new tables
      for (const t of schema.tables) {
        if (!(t.name in rowCounts)) setRowCount(t.name, 10)
      }
    } catch (e: unknown) {
      setParseError(e instanceof Error ? e.message : String(e))
      setParsedSchema(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center gap-3">
        <Typography.Text strong>
          <CodeOutlined /> Schema Editor
        </Typography.Text>
        <Select
          size="small"
          value={dialect}
          onChange={setDialect}
          options={DIALECTS.map((d) => ({ label: d, value: d }))}
          style={{ width: 130 }}
        />
        <Button
          type="primary"
          size="small"
          loading={loading}
          onClick={handleParse}
        >
          Parse DDL
        </Button>
        {parsedSchema && (
          <Space size={4}>
            <Tag icon={<TableOutlined />} color="green">
              {parsedSchema.tables.length} table
              {parsedSchema.tables.length !== 1 ? 's' : ''}
            </Tag>
            <Tag color="blue">{parsedSchema.schema_id.slice(0, 8)}</Tag>
          </Space>
        )}
      </div>

      {parseError && (
        <Alert type="error" message={parseError} showIcon closable onClose={() => setParseError(null)} />
      )}

      <div className="flex-1 border border-gray-200 rounded overflow-hidden" style={{ minHeight: 300 }}>
        <Editor
          defaultLanguage="sql"
          value={ddlSource}
          onChange={(v) => setDdlSource(v ?? '')}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
          }}
        />
      </div>

      {parsedSchema && (
        <div>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            Generation order:{' '}
            {parsedSchema.generation_order.map((s) => s.name).join(' → ')}
          </Typography.Text>
        </div>
      )}
    </div>
  )
}
