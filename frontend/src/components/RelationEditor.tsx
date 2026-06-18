import { useCallback, useEffect, useState } from 'react'
import {
  Button, Space, Table, Select, message, Typography, Empty, Popconfirm, Checkbox, Tag, Tooltip,
  Modal, Input, Upload,
} from 'antd'
import {
  RobotOutlined, ThunderboltOutlined, PlusOutlined, SaveOutlined,
  DownloadOutlined, DeleteOutlined, ReloadOutlined, ImportOutlined, UploadOutlined,
} from '@ant-design/icons'
import { useAppStore } from '../store'
import {
  inferRelations, getRelations, updateRelations, exportRelationsUrl,
  importRelationsCypher, type RelationItem,
} from '../api'
import RelationGraph from './RelationGraph'

const { Text, Paragraph } = Typography

// Stable per-row id so table pagination/edit/delete track the right row.
let _seq = 0
const uid = () => `r${Date.now().toString(36)}_${_seq++}`
type Row = RelationItem & { uid: string }
const withUid = (items: RelationItem[]): Row[] => items.map((it) => ({ ...it, uid: uid() }))

export default function RelationEditor() {
  const parsedSchema = useAppStore((s) => s.parsedSchema)
  const aiConfig = useAppStore((s) => s.aiConfig)

  const schemaId = parsedSchema?.schema_id
  const tables = parsedSchema?.tables ?? []
  const tableNames = tables.map((t) => t.name)

  const [relations, setRelations] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [useAi, setUseAi] = useState(true)
  const [dirty, setDirty] = useState(false)

  // Import-from-Cypher modal
  const [importOpen, setImportOpen] = useState(false)
  const [importText, setImportText] = useState('')
  const [replaceExisting, setReplaceExisting] = useState(false)
  const [importing, setImporting] = useState(false)

  const colsOf = useCallback(
    (table: string): string[] =>
      tables.find((t) => t.name === table)?.columns.map((c) => c.name) ?? [],
    [tables],
  )

  const load = useCallback(async () => {
    if (!schemaId) return
    try {
      const res = await getRelations(schemaId)
      setRelations(withUid(res.relations))
      setDirty(false)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载关系失败')
    }
  }, [schemaId])

  useEffect(() => {
    void load()
  }, [load])

  const handleInfer = async () => {
    if (!schemaId) return
    setLoading(true)
    try {
      const res = await inferRelations(
        schemaId,
        useAi,
        useAi && aiConfig
          ? { base_url: aiConfig.base_url, api_key: aiConfig.api_key, model: aiConfig.model }
          : null,
      )
      setRelations(withUid(res.relations))
      setDirty(false)
      message.success(
        `识别到 ${res.relations.length} 条关系${res.ai_used ? '（AI）' : '（启发式）'}`,
      )
    } catch (e) {
      message.error(e instanceof Error ? e.message : '识别失败')
    } finally {
      setLoading(false)
    }
  }

  const update = (rowUid: string, patch: Partial<RelationItem>) => {
    setRelations((rs) => rs.map((r) => (r.uid === rowUid ? { ...r, ...patch } : r)))
    setDirty(true)
  }

  const addRow = () => {
    setRelations((rs) => [
      ...rs,
      { child_table: '', child_col: '', parent_table: '', parent_col: '', uid: uid() },
    ])
    setDirty(true)
  }

  const removeRow = (rowUid: string) => {
    setRelations((rs) => rs.filter((r) => r.uid !== rowUid))
    setDirty(true)
  }

  const save = async () => {
    if (!schemaId) return
    const invalid = relations.filter(
      (r) => !r.child_table || !r.child_col || !r.parent_table || !r.parent_col,
    )
    if (invalid.length) {
      message.warning(`有 ${invalid.length} 条关系字段不完整，请补全后再保存`)
      return
    }
    setLoading(true)
    try {
      const payload: RelationItem[] = relations.map((r) => ({
        child_table: r.child_table,
        child_col: r.child_col,
        parent_table: r.parent_table,
        parent_col: r.parent_col,
      }))
      const res = await updateRelations(schemaId, payload)
      setRelations(withUid(res.relations))
      setDirty(false)
      message.success(`已保存 ${res.relations.length} 条关系`)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setLoading(false)
    }
  }

  const exportCypher = () => {
    if (!schemaId) return
    const a = document.createElement('a')
    a.href = exportRelationsUrl(schemaId)
    a.download = 'schema_graph.cypher'
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  const doImport = async () => {
    if (!schemaId || !importText.trim()) {
      message.warning('请粘贴或上传 Cypher 内容')
      return
    }
    setImporting(true)
    try {
      const res = await importRelationsCypher(schemaId, importText, replaceExisting)
      setRelations(withUid(res.relations))
      setDirty(false)
      setImportOpen(false)
      message.success(`已导入并应用 ${res.relations.length} 条关系`)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '导入失败')
    } finally {
      setImporting(false)
    }
  }

  if (!schemaId) {
    return (
      <Empty
        description="请先在 Schema 标签解析 DDL，然后回到这里识别 / 导入表关系"
        style={{ marginTop: 80 }}
      />
    )
  }

  const tableSelect = (value: string, onChange: (v: string) => void) => (
    <Select
      showSearch
      placeholder="选择表"
      value={value || undefined}
      onChange={onChange}
      style={{ width: '100%' }}
      options={tableNames.map((n) => ({ value: n, label: n }))}
      filterOption={(input, opt) =>
        (opt?.label ?? '').toLowerCase().includes(input.toLowerCase())
      }
    />
  )

  const colSelect = (table: string, value: string, onChange: (v: string) => void) => (
    <Select
      showSearch
      placeholder="选择字段"
      value={value || undefined}
      onChange={onChange}
      style={{ width: '100%' }}
      disabled={!table}
      options={colsOf(table).map((c) => ({ value: c, label: c }))}
      filterOption={(input, opt) =>
        (opt?.label ?? '').toLowerCase().includes(input.toLowerCase())
      }
    />
  )

  // render uses `record` (the actual row) — never an array index, so pagination works.
  const columns = [
    {
      title: '子表（引用方）',
      width: '23%',
      render: (_: unknown, r: Row) =>
        tableSelect(r.child_table, (v) => update(r.uid, { child_table: v, child_col: '' })),
    },
    {
      title: '子表字段',
      width: '20%',
      render: (_: unknown, r: Row) =>
        colSelect(r.child_table, r.child_col, (v) => update(r.uid, { child_col: v })),
    },
    {
      title: '',
      width: 36,
      align: 'center' as const,
      render: () => <Text type="secondary">→</Text>,
    },
    {
      title: '父表（被引用/权威）',
      width: '23%',
      render: (_: unknown, r: Row) =>
        tableSelect(r.parent_table, (v) => update(r.uid, { parent_table: v, parent_col: '' })),
    },
    {
      title: '父表字段',
      width: '20%',
      render: (_: unknown, r: Row) =>
        colSelect(r.parent_table, r.parent_col, (v) => update(r.uid, { parent_col: v })),
    },
    {
      title: '操作',
      width: 60,
      align: 'center' as const,
      render: (_: unknown, r: Row) => (
        <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeRow(r.uid)} />
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 12, flexWrap: 'wrap' }}>
        <Tooltip title={useAi ? '使用 AI 根据列名与中文注释识别表关系（含跨名同义字段）' : '启发式：连接同名共享键'}>
          <Button
            type="primary"
            icon={useAi ? <RobotOutlined /> : <ThunderboltOutlined />}
            loading={loading}
            onClick={handleInfer}
          >
            {useAi ? 'AI 识别关系' : '启发式识别'}
          </Button>
        </Tooltip>
        <Checkbox checked={useAi} onChange={(e) => setUseAi(e.target.checked)}>
          使用 AI
        </Checkbox>
        <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
          导入 Cypher
        </Button>
        <Button icon={<DownloadOutlined />} onClick={exportCypher}>
          导出 Cypher
        </Button>
        <Button icon={<PlusOutlined />} onClick={addRow}>
          添加关系
        </Button>
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>
          重新加载
        </Button>
        <Popconfirm
          title="保存将覆盖当前 schema 的全部关系，并按依赖重排生成顺序。"
          onConfirm={() => void save()}
          okText="保存"
          cancelText="取消"
        >
          <Button type="primary" ghost icon={<SaveOutlined />} loading={loading}>
            保存{dirty ? ' *' : ''}
          </Button>
        </Popconfirm>
        <Tag color="blue">{relations.length} 条关系</Tag>
      </Space>

      <RelationGraph relations={relations} />

      <Paragraph type="secondary" style={{ fontSize: 12, margin: '10px 0 8px' }}>
        关系表示「子表字段引用父表字段」。父表是主表/权威表（如客户主表），生成时其字段值会先生成，子表从中采样，从而保证多表 JOIN 逻辑闭环。
        导入 Cypher 即导入表关系。{useAi && !aiConfig && '（未配置 AI，将自动回退到启发式）'}
      </Paragraph>

      <Table
        size="small"
        rowKey="uid"
        columns={columns}
        dataSource={relations}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        locale={{ emptyText: '暂无关系，点击「AI 识别关系」自动识别、「导入 Cypher」导入或「添加关系」手动添加' }}
      />

      <Modal
        title="从 Cypher 导入表关系"
        open={importOpen}
        onOk={() => void doImport()}
        confirmLoading={importing}
        onCancel={() => setImportOpen(false)}
        okText="导入并应用"
        cancelText="取消"
        width={720}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Paragraph type="secondary" style={{ fontSize: 12, margin: 0 }}>
            粘贴或上传 schema graph 格式的 Cypher（如 test_ddl/schema_graph.cypher）。
            仅会保留与当前表/列匹配的关系，导入后可在图与表格中查看并继续编辑。
          </Paragraph>
          <Space>
            <Upload
              accept=".cypher,.cql,.txt"
              showUploadList={false}
              beforeUpload={(file) => {
                file.text().then(setImportText).catch(() => message.error('文件读取失败'))
                return false
              }}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
            <Checkbox
              checked={replaceExisting}
              onChange={(e) => setReplaceExisting(e.target.checked)}
            >
              替换现有关系（否则合并去重）
            </Checkbox>
          </Space>
          <Input.TextArea
            rows={14}
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            placeholder="MATCH (a:Table {fqn: '...'})&#10;MATCH (b:Table {fqn: '...'})&#10;MERGE (a)-[r:REFERENCES]->(b)&#10;SET r.via = 'child_col → parent_col';"
            style={{ fontFamily: 'monospace', fontSize: 12 }}
          />
        </Space>
      </Modal>
    </div>
  )
}
