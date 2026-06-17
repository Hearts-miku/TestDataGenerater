import { useRef, useState } from 'react'
import { Button, Select, Alert, Typography, Space, Tag, Tooltip, message } from 'antd'
import { CodeOutlined, TableOutlined, UploadOutlined } from '@ant-design/icons'
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
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleParse() {
    setLoading(true)
    setParseError(null)
    try {
      const schema = await parseDdl(ddlSource, dialect)
      setParsedSchema(schema)
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

  function handleFileImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) {
      message.error('文件过大，请上传 2 MB 以内的 .sql 文件')
      return
    }
    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target?.result as string
      setDdlSource(text)
      setParsedSchema(null)
      setParseError(null)
      message.success(`已导入 ${file.name}`)
    }
    reader.onerror = () => message.error('文件读取失败')
    reader.readAsText(file, 'utf-8')
    // Reset so the same file can be re-imported
    e.target.value = ''
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
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

        {/* Hidden file input */}
        <input
          ref={fileRef}
          type="file"
          accept=".sql,.txt"
          style={{ display: 'none' }}
          onChange={handleFileImport}
        />
        <Tooltip title="导入 .sql 文件（替换当前内容）">
          <Button
            size="small"
            icon={<UploadOutlined />}
            onClick={() => fileRef.current?.click()}
          >
            导入 .sql
          </Button>
        </Tooltip>

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
              {parsedSchema.tables.length} table{parsedSchema.tables.length !== 1 ? 's' : ''}
            </Tag>
            <Tag color="blue">{parsedSchema.schema_id.slice(0, 8)}</Tag>
          </Space>
        )}
      </div>

      {parseError && (
        <Alert
          type="error"
          message={parseError}
          showIcon
          closable
          onClose={() => setParseError(null)}
        />
      )}

      {/* ── Monaco editor with explicit height ── */}
      <div
        style={{
          height: 'calc(100vh - 260px)',
          minHeight: 400,
          border: '1px solid #d9d9d9',
          borderRadius: 6,
          overflow: 'hidden',
        }}
      >
        <Editor
          language="sql"
          value={ddlSource}
          onChange={(v) => setDdlSource(v ?? '')}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            tabSize: 2,
          }}
        />
      </div>

      {parsedSchema && (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Generation order:{' '}
          {parsedSchema.generation_order.map((s) => s.name).join(' → ')}
        </Typography.Text>
      )}
    </div>
  )
}
