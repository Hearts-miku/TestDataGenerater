import { useState } from 'react'
import { Button, Alert, Typography, Space, Tag, InputNumber, Table, message } from 'antd'
import { NodeIndexOutlined, PartitionOutlined, ThunderboltOutlined } from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { useAppStore } from '../store'
import { parseCypher, generateData } from '../api'
import MultiFileImport from './MultiFileImport'

export default function CypherEditor() {
  const {
    cypherSource, setCypherSource,
    parsedGraphSchema, setParsedGraphSchema,
    graphParseError, setGraphParseError,
    graphRowCounts, setGraphRowCount,
    graphGenerationResult, setGraphGenerationResult,
  } = useAppStore()

  const [parsing, setParsing] = useState(false)
  const [generating, setGenerating] = useState(false)

  async function handleParse() {
    setParsing(true)
    setGraphParseError(null)
    try {
      const schema = await parseCypher(cypherSource)
      setParsedGraphSchema(schema)
      for (const step of schema.generation_order) {
        if (!(step.name in graphRowCounts)) {
          setGraphRowCount(step.name, step.kind === 'node' ? 20 : 30)
        }
      }
    } catch (e: unknown) {
      setGraphParseError(e instanceof Error ? e.message : String(e))
      setParsedGraphSchema(null)
    } finally {
      setParsing(false)
    }
  }

  async function handleGenerate() {
    if (!parsedGraphSchema) return
    setGenerating(true)
    try {
      const result = await generateData(parsedGraphSchema.schema_id, graphRowCounts)
      setGraphGenerationResult(result)
      message.success('图数据生成完成')
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const generatedRows = graphGenerationResult
    ? Object.entries(graphGenerationResult.tables).map(([name, meta]) => ({
        key: name,
        name,
        generated: meta.generated,
      }))
    : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Typography.Text strong>
          <NodeIndexOutlined /> Cypher Schema Editor
        </Typography.Text>

        <MultiFileImport
          accept=".cypher,.cql,.cyp,.txt"
          commentPrefix="//"
          currentValue={cypherSource}
          onChange={setCypherSource}
          onImported={() => {
            setParsedGraphSchema(null)
            setGraphParseError(null)
          }}
          buttonLabel="导入 Cypher"
        />

        <Button type="primary" size="small" loading={parsing} onClick={handleParse}>
          Parse Schema
        </Button>

        {parsedGraphSchema && (
          <>
            <Button
              size="small"
              icon={<ThunderboltOutlined />}
              loading={generating}
              onClick={handleGenerate}
              disabled={Object.keys(graphRowCounts).length === 0}
            >
              Generate
            </Button>
            <Space size={4}>
              <Tag icon={<NodeIndexOutlined />} color="purple">
                {parsedGraphSchema.nodes.length} nodes
              </Tag>
              <Tag icon={<PartitionOutlined />} color="cyan">
                {parsedGraphSchema.relationships.length} rels
              </Tag>
              <Tag color="blue">{parsedGraphSchema.schema_id.slice(0, 8)}</Tag>
            </Space>
          </>
        )}
      </div>

      {graphParseError && (
        <Alert
          type="error"
          message={graphParseError.split('\n')[0]}
          description={
            graphParseError.includes('\n')
              ? <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap' }}>{graphParseError.split('\n').slice(1).join('\n')}</pre>
              : undefined
          }
          showIcon
          closable
          onClose={() => setGraphParseError(null)}
        />
      )}

      <div style={{ display: 'flex', gap: 12 }}>
        {/* Monaco editor */}
        <div style={{ flex: 1, height: 480, border: '1px solid #d9d9d9', borderRadius: 6, overflow: 'hidden' }}>
          <Editor
            language="cypher"
            value={cypherSource}
            onChange={(v) => setCypherSource(v ?? '')}
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

        {/* Row count panel */}
        {parsedGraphSchema && (
          <div style={{ width: 260, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Typography.Text strong style={{ fontSize: 13 }}>生成数量</Typography.Text>
            {parsedGraphSchema.generation_order.map((step) => (
              <div
                key={step.name}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}
              >
                <Tag color={step.kind === 'node' ? 'purple' : 'cyan'} style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {step.name}
                </Tag>
                <InputNumber
                  size="small"
                  min={0}
                  max={100000}
                  value={graphRowCounts[step.name] ?? 0}
                  onChange={(v) => setGraphRowCount(step.name, v ?? 0)}
                  style={{ width: 80 }}
                />
              </div>
            ))}

            {generatedRows.length > 0 && (
              <Table
                size="small"
                dataSource={generatedRows}
                columns={[
                  { title: '实体', dataIndex: 'name', key: 'name' },
                  { title: '生成', dataIndex: 'generated', key: 'generated', align: 'right' },
                ]}
                pagination={false}
                style={{ marginTop: 8 }}
              />
            )}
          </div>
        )}
      </div>

      {parsedGraphSchema && (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Generation order:{' '}
          {parsedGraphSchema.generation_order.map((s) => s.name).join(' → ')}
        </Typography.Text>
      )}
    </div>
  )
}
