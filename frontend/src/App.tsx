import { Layout, Tabs, Typography } from 'antd'
import {
  CodeOutlined, ThunderboltOutlined, DatabaseOutlined,
  ApartmentOutlined, EyeOutlined, DownloadOutlined,
  ConsoleSqlOutlined,
  CloudUploadOutlined, RobotOutlined, SettingOutlined, PartitionOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import SchemaEditor from './components/SchemaEditor'
import GeneratePanel from './components/GeneratePanel'
import SqlExplorer from './components/SqlExplorer'
import ErDiagram from './components/ErDiagram'
import RelationEditor from './components/RelationEditor'
import CustomRulesPanel from './components/CustomRulesPanel'
import DataPreview from './components/DataPreview'
import ExportPanel from './components/ExportPanel'
import CypherExplorer from './components/CypherExplorer'
import MysqlWritePanel from './components/MysqlWritePanel'
import MysqlConfigPanel from './components/MysqlConfigPanel'
import AiConfigPanel from './components/AiConfigPanel'
import 'antd/dist/reset.css'

const { Header, Content } = Layout

const tabs = [
  {
    key: 'schema',
    label: <span><CodeOutlined /> Schema</span>,
    children: <SchemaEditor />,
  },
  {
    key: 'er',
    label: <span><ApartmentOutlined /> ER 图</span>,
    children: <ErDiagram />,
  },
  {
    key: 'relations',
    label: <span><PartitionOutlined /> 表关系图谱</span>,
    children: <RelationEditor />,
  },
  {
    key: 'custom-rules',
    label: <span><ExperimentOutlined /> 自定义规则</span>,
    children: <CustomRulesPanel />,
  },
  {
    key: 'generate',
    label: <span><ThunderboltOutlined /> Generate</span>,
    children: <GeneratePanel />,
  },
  {
    key: 'preview',
    label: <span><EyeOutlined /> 数据预览</span>,
    children: <DataPreview />,
  },
  {
    key: 'export',
    label: <span><DownloadOutlined /> 导出</span>,
    children: <ExportPanel />,
  },
  {
    key: 'explorer',
    label: <span><DatabaseOutlined /> SQL Explorer</span>,
    children: <SqlExplorer />,
  },
  {
    key: 'cypher-explorer',
    label: <span><ConsoleSqlOutlined /> Cypher Explorer</span>,
    children: <CypherExplorer />,
  },
  {
    key: 'mysql-config',
    label: <span><SettingOutlined /> MySQL 配置</span>,
    children: <MysqlConfigPanel />,
  },
  {
    key: 'mysql-write',
    label: <span><CloudUploadOutlined /> MySQL 写入</span>,
    children: <MysqlWritePanel />,
  },
  {
    key: 'ai-config',
    label: <span><RobotOutlined /> AI 配置</span>,
    children: <AiConfigPanel />,
  },
]

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '0 24px' }}>
        <Typography.Title level={4} style={{ margin: 0, color: '#fff' }}>
          DataForge
        </Typography.Title>
        <Typography.Text style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>
          Test Data Generator
        </Typography.Text>
      </Header>
      <Content style={{ padding: 24 }}>
        <Tabs items={tabs} destroyInactiveTabPane={false} />
      </Content>
    </Layout>
  )
}
