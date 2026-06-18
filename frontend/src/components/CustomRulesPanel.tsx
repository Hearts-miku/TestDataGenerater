import { useCallback, useEffect, useState } from 'react'
import {
  Button, Space, Table, Select, Input, InputNumber, message, Typography,
  Empty, Popconfirm, Tag, Tooltip, Modal, Radio, Upload,
} from 'antd'
import {
  RobotOutlined, PlusOutlined, SaveOutlined, DeleteOutlined, ReloadOutlined,
  ImportOutlined, UploadOutlined,
} from '@ant-design/icons'
import { useAppStore } from '../store'
import {
  translateRules, getRules, updateRules, inferRulesFromSamples, type FieldSpec,
} from '../api'

const { Text, Paragraph } = Typography
const { TextArea } = Input

// Stable per-row id so pagination/edit/delete track the correct row.
let _seq = 0
const uid = () => `c${Date.now().toString(36)}_${_seq++}`

const KINDS = [
  { value: 'enum', label: '枚举值' },
  { value: 'pool', label: '样例池' },
  { value: 'pattern', label: '模式串' },
  { value: 'int_range', label: '整数范围' },
  { value: 'decimal_range', label: '小数范围' },
  { value: 'date_range', label: '日期范围' },
  { value: 'faker', label: '内置类型' },
]

const FAKERS = [
  'cn_name', 'cn_company', 'cn_org_name', 'cn_id_card', 'cn_bankcard',
  'cn_phone', 'cn_city', 'cn_address', 'cn_word', 'cn_money', 'cn_rate',
  'cn_date_int', 'email', 'datetime', 'date_of_birth', 'random_int', 'uuid4',
]

interface Row {
  uid: string
  key: string // table.column
  spec: FieldSpec
}

const DEFAULT_SPEC: Record<string, FieldSpec> = {
  enum: { kind: 'enum', enum: [] },
  pool: { kind: 'pool', pool: [] },
  pattern: { kind: 'pattern', pattern: '', prefix: '' },
  int_range: { kind: 'int_range', min: 0, max: 100 },
  decimal_range: { kind: 'decimal_range', min: 0, max: 1000, decimals: 2 },
  date_range: { kind: 'date_range', start: '2020-01-01', end: '2024-12-31' },
  faker: { kind: 'faker', faker: 'cn_name' },
}

const NL_PLACEHOLDER = `用自然语言描述规则，例如：
年龄在18到60之间；
手机号138开头；
客户状态只能是 正常、冻结、销户；
开户日期在2020到2024年之间；
交易金额保留两位小数，最大五万`

const SQL_PLACEHOLDER = `粘贴 INSERT 语句，例如：
INSERT INTO users (age, status, phone) VALUES
(23, 'A', '13812345678'),
(45, 'B', '13987654321');`

const CSV_PLACEHOLDER = `粘贴 CSV（首行为列名），例如：
age,status,phone
23,A,13812345678
45,B,13987654321`

export default function CustomRulesPanel() {
  const parsedSchema = useAppStore((s) => s.parsedSchema)
  const aiConfig = useAppStore((s) => s.aiConfig)
  const schemaId = parsedSchema?.schema_id
  const tables = parsedSchema?.tables ?? []
  const tableNames = tables.map((t) => t.name)

  const columnKeys = tables.flatMap((t) => t.columns.map((c) => `${t.name}.${c.name}`))

  const [nlText, setNlText] = useState('')
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [dirty, setDirty] = useState(false)

  // Sample-data modal
  const [sampleOpen, setSampleOpen] = useState(false)
  const [sampleType, setSampleType] = useState<'sql' | 'csv'>('sql')
  const [sampleText, setSampleText] = useState('')
  const [sampleTable, setSampleTable] = useState<string | undefined>(undefined)
  const [sampleLoading, setSampleLoading] = useState(false)

  const load = useCallback(async () => {
    if (!schemaId) return
    try {
      const res = await getRules(schemaId)
      setRows(Object.entries(res.field_specs).map(([key, spec]) => ({ uid: uid(), key, spec })))
      setDirty(false)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载规则失败')
    }
  }, [schemaId])

  useEffect(() => { void load() }, [load])

  // Merge inferred specs into the table (same key overrides). Returns count.
  const mergeSpecs = (parsed: Record<string, FieldSpec>): number => {
    const n = Object.keys(parsed).length
    if (!n) return 0
    setRows((prev) => {
      const map = new Map(prev.map((r) => [r.key, r]))
      for (const [key, spec] of Object.entries(parsed)) {
        const existing = map.get(key)
        map.set(key, { uid: existing?.uid ?? uid(), key, spec })
      }
      return Array.from(map.values())
    })
    setDirty(true)
    return n
  }

  const translate = async () => {
    if (!schemaId || !nlText.trim()) return
    setLoading(true)
    try {
      const res = await translateRules(
        schemaId,
        nlText,
        aiConfig ? { base_url: aiConfig.base_url, api_key: aiConfig.api_key, model: aiConfig.model } : null,
      )
      const n = mergeSpecs(res.field_specs)
      if (n) message.success(`AI 解析出 ${n} 条规则`)
      else message.warning('未解析出可用规则，请尝试更明确的描述或指明字段')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '解析失败')
    } finally {
      setLoading(false)
    }
  }

  const doSampleInfer = async () => {
    if (!schemaId || !sampleText.trim()) {
      message.warning('请粘贴或上传样例数据')
      return
    }
    if (sampleType === 'csv' && !sampleTable) {
      message.warning('CSV 需要选择目标表')
      return
    }
    setSampleLoading(true)
    try {
      const res = await inferRulesFromSamples(
        schemaId, sampleType, sampleText, sampleType === 'csv' ? sampleTable : null,
      )
      const n = mergeSpecs(res.field_specs)
      setSampleOpen(false)
      if (n) message.success(`从样例识别出 ${n} 条规则`)
      else message.warning('未识别出规则')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '识别失败')
    } finally {
      setSampleLoading(false)
    }
  }

  const updateRow = (rowUid: string, patch: Partial<Row>) => {
    setRows((rs) => rs.map((r) => (r.uid === rowUid ? { ...r, ...patch } : r)))
    setDirty(true)
  }
  const updateSpec = (rowUid: string, spec: FieldSpec) => updateRow(rowUid, { spec })

  const addRow = () => {
    setRows((rs) => [...rs, { uid: uid(), key: '', spec: { ...DEFAULT_SPEC.enum } }])
    setDirty(true)
  }
  const removeRow = (rowUid: string) => {
    setRows((rs) => rs.filter((r) => r.uid !== rowUid))
    setDirty(true)
  }

  const save = async () => {
    if (!schemaId) return
    const bad = rows.filter((r) => !r.key)
    if (bad.length) { message.warning('有规则未选择目标列'); return }
    const field_specs: Record<string, FieldSpec> = {}
    for (const r of rows) field_specs[r.key] = r.spec
    setLoading(true)
    try {
      const res = await updateRules(schemaId, field_specs)
      setRows(Object.entries(res.field_specs).map(([key, spec]) => ({ uid: uid(), key, spec })))
      setDirty(false)
      message.success(`已保存 ${Object.keys(res.field_specs).length} 条规则`)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setLoading(false)
    }
  }

  if (!schemaId) {
    return <Empty description="请先在 Schema 标签解析 DDL，然后回到这里配置生成规则" style={{ marginTop: 80 }} />
  }

  const renderParams = (row: Row) => {
    const s = row.spec
    const u = row.uid
    switch (s.kind) {
      case 'enum':
      case 'pool': {
        const field = s.kind === 'enum' ? 'enum' : 'pool'
        return (
          <Select
            mode="tags" style={{ width: '100%' }} placeholder="输入取值后回车"
            value={(s[field] as string[]) ?? []}
            onChange={(v) => updateSpec(u, { ...s, [field]: v })}
          />
        )
      }
      case 'pattern':
        return (
          <Space.Compact style={{ width: '100%' }}>
            <Input
              placeholder="模式：# 数字 ? 字母，如 138########"
              value={s.pattern as string}
              onChange={(e) => updateSpec(u, { ...s, pattern: e.target.value })}
            />
            <Input
              style={{ width: 90 }} placeholder="前缀"
              value={s.prefix as string}
              onChange={(e) => updateSpec(u, { ...s, prefix: e.target.value })}
            />
          </Space.Compact>
        )
      case 'int_range':
        return (
          <Space>
            <InputNumber placeholder="最小" value={s.min as number}
              onChange={(v) => updateSpec(u, { ...s, min: v })} />
            <Text type="secondary">~</Text>
            <InputNumber placeholder="最大" value={s.max as number}
              onChange={(v) => updateSpec(u, { ...s, max: v })} />
          </Space>
        )
      case 'decimal_range':
        return (
          <Space>
            <InputNumber placeholder="最小" value={s.min as number}
              onChange={(v) => updateSpec(u, { ...s, min: v })} />
            <Text type="secondary">~</Text>
            <InputNumber placeholder="最大" value={s.max as number}
              onChange={(v) => updateSpec(u, { ...s, max: v })} />
            <InputNumber style={{ width: 110 }} min={0} max={6} addonBefore="小数"
              value={s.decimals as number}
              onChange={(v) => updateSpec(u, { ...s, decimals: v })} />
          </Space>
        )
      case 'date_range':
        return (
          <Space>
            <Input style={{ width: 130 }} placeholder="YYYY-MM-DD" value={s.start as string}
              onChange={(e) => updateSpec(u, { ...s, start: e.target.value })} />
            <Text type="secondary">~</Text>
            <Input style={{ width: 130 }} placeholder="YYYY-MM-DD" value={s.end as string}
              onChange={(e) => updateSpec(u, { ...s, end: e.target.value })} />
          </Space>
        )
      case 'faker':
        return (
          <Select
            showSearch style={{ width: 200 }} value={s.faker as string}
            options={FAKERS.map((f) => ({ value: f, label: f }))}
            onChange={(v) => updateSpec(u, { ...s, faker: v })}
          />
        )
      default:
        return null
    }
  }

  const columns = [
    {
      title: '目标列（表.列）', width: '28%',
      render: (_: unknown, r: Row) => (
        <Select
          showSearch placeholder="选择列" style={{ width: '100%' }}
          value={r.key || undefined}
          options={columnKeys.map((k) => ({ value: k, label: k }))}
          onChange={(v) => updateRow(r.uid, { key: v })}
          filterOption={(input, opt) => (opt?.label ?? '').toLowerCase().includes(input.toLowerCase())}
        />
      ),
    },
    {
      title: '规则类型', width: 130,
      render: (_: unknown, r: Row) => (
        <Select
          style={{ width: '100%' }} value={r.spec.kind} options={KINDS}
          onChange={(v) => updateSpec(r.uid, { ...DEFAULT_SPEC[v] })}
        />
      ),
    },
    {
      title: '参数',
      render: (_: unknown, r: Row) => renderParams(r),
    },
    {
      title: '操作', width: 60, align: 'center' as const,
      render: (_: unknown, r: Row) => (
        <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeRow(r.uid)} />
      ),
    },
  ]

  return (
    <div>
      <Paragraph type="secondary" style={{ fontSize: 12 }}>
        三种方式定义字段规则：① 自然语言描述（AI 翻译）② 从样例数据（INSERT/CSV）自动识别 ③ 手动添加。
        规则按列生效，优先级高于 AI 推断与注释语义。
        {!aiConfig && '（自然语言解析需先在「AI 配置」标签配置 LLM；样例识别无需 AI）'}
      </Paragraph>

      <TextArea
        rows={5} value={nlText} placeholder={NL_PLACEHOLDER}
        onChange={(e) => setNlText(e.target.value)}
        style={{ marginBottom: 8, fontFamily: 'monospace' }}
      />

      <Space style={{ marginBottom: 12, flexWrap: 'wrap' }}>
        <Tooltip title="用 AI 把上面的自然语言翻译成结构化规则">
          <Button type="primary" icon={<RobotOutlined />} loading={loading} onClick={translate}>
            AI 解析规则
          </Button>
        </Tooltip>
        <Button icon={<ImportOutlined />} onClick={() => setSampleOpen(true)}>
          从样例数据识别
        </Button>
        <Button icon={<PlusOutlined />} onClick={addRow}>手动添加</Button>
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>重新加载</Button>
        <Popconfirm
          title="保存将覆盖当前 schema 的全部自定义规则。"
          onConfirm={() => void save()} okText="保存" cancelText="取消"
        >
          <Button type="primary" ghost icon={<SaveOutlined />} loading={loading}>
            保存{dirty ? ' *' : ''}
          </Button>
        </Popconfirm>
        <Tag color="blue">{rows.length} 条规则</Tag>
      </Space>

      <Table
        size="small" rowKey="uid" columns={columns} dataSource={rows}
        pagination={{ pageSize: 15, showSizeChanger: true }}
        locale={{ emptyText: '暂无规则，可用「AI 解析规则」「从样例数据识别」或「手动添加」' }}
      />

      <Modal
        title="从样例数据识别字段规则"
        open={sampleOpen}
        onOk={() => void doSampleInfer()}
        confirmLoading={sampleLoading}
        onCancel={() => setSampleOpen(false)}
        okText="识别"
        cancelText="取消"
        width={720}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Paragraph type="secondary" style={{ fontSize: 12, margin: 0 }}>
            根据样例数据的实际取值统计推断规则（数值范围、小数位、日期范围、枚举、定长模式等），无需 AI。
            仅保留与当前表/列匹配的列。
          </Paragraph>
          <Space>
            <Radio.Group
              value={sampleType}
              onChange={(e) => setSampleType(e.target.value)}
              optionType="button"
              buttonStyle="solid"
              options={[
                { label: 'INSERT SQL', value: 'sql' },
                { label: 'CSV', value: 'csv' },
              ]}
            />
            <Upload
              accept=".sql,.csv,.txt"
              showUploadList={false}
              beforeUpload={(file) => {
                file.text().then(setSampleText).catch(() => message.error('文件读取失败'))
                return false
              }}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
            {sampleType === 'csv' && (
              <Select
                showSearch placeholder="选择目标表" style={{ width: 220 }}
                value={sampleTable}
                onChange={setSampleTable}
                options={tableNames.map((n) => ({ value: n, label: n }))}
                filterOption={(input, opt) => (opt?.label ?? '').toLowerCase().includes(input.toLowerCase())}
              />
            )}
          </Space>
          <TextArea
            rows={14}
            value={sampleText}
            onChange={(e) => setSampleText(e.target.value)}
            placeholder={sampleType === 'sql' ? SQL_PLACEHOLDER : CSV_PLACEHOLDER}
            style={{ fontFamily: 'monospace', fontSize: 12 }}
          />
        </Space>
      </Modal>
    </div>
  )
}
