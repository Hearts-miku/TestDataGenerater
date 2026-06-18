import { useRef, useState } from 'react'
import { Button, Segmented, Tooltip, message } from 'antd'
import { UploadOutlined } from '@ant-design/icons'

interface MultiFileImportProps {
  /** Accepted file extensions, e.g. ".sql,.txt" */
  accept: string
  /** Comment prefix used for the per-file separator header ("--" for SQL, "//" for Cypher) */
  commentPrefix: string
  /** Current editor content (used when appending) */
  currentValue: string
  /** Called with the merged content after import */
  onChange: (value: string) => void
  /** Called after a successful import (e.g. to clear parsed schema/errors) */
  onImported?: () => void
  /** Per-file size limit in MB (default 2) */
  maxFileSizeMB?: number
  /** Import button label */
  buttonLabel?: string
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (ev) => resolve((ev.target?.result as string) ?? '')
    reader.onerror = () => reject(new Error(`读取 ${file.name} 失败`))
    reader.readAsText(file, 'utf-8')
  })
}

export default function MultiFileImport({
  accept,
  commentPrefix,
  currentValue,
  onChange,
  onImported,
  maxFileSizeMB = 2,
  buttonLabel = '导入文件',
}: MultiFileImportProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<'replace' | 'append'>('replace')

  async function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    // Sort by name so numeric migration prefixes (01_, 02_, ...) import in order
    const files = Array.from(fileList).sort((a, b) => a.name.localeCompare(b.name))

    const maxBytes = maxFileSizeMB * 1024 * 1024
    const tooBig = files.filter((f) => f.size > maxBytes)
    if (tooBig.length > 0) {
      message.error(`以下文件超过 ${maxFileSizeMB} MB：${tooBig.map((f) => f.name).join(', ')}`)
      e.target.value = ''
      return
    }

    try {
      const contents = await Promise.all(files.map(readFileAsText))
      const blocks = files.map(
        (f, i) => `${commentPrefix} ===== ${f.name} =====\n${contents[i].trim()}`,
      )
      const merged = blocks.join('\n\n')

      const next =
        mode === 'append' && currentValue.trim()
          ? `${currentValue.trimEnd()}\n\n${merged}`
          : merged

      onChange(next)
      onImported?.()

      const names = files.map((f) => f.name).join('、')
      message.success(`已${mode === 'append' ? '追加' : '导入'} ${files.length} 个文件：${names}`)
    } catch (err) {
      message.error(err instanceof Error ? err.message : '文件读取失败')
    } finally {
      // Reset so the same file(s) can be re-imported
      e.target.value = ''
    }
  }

  return (
    <>
      <input
        ref={fileRef}
        type="file"
        accept={accept}
        multiple
        style={{ display: 'none' }}
        onChange={handleFiles}
      />
      <Segmented
        size="small"
        value={mode}
        onChange={(v) => setMode(v as 'replace' | 'append')}
        options={[
          { label: '替换', value: 'replace' },
          { label: '追加', value: 'append' },
        ]}
      />
      <Tooltip
        title={`可一次选择多个文件批量导入（${mode === 'append' ? '追加到现有内容末尾' : '替换现有内容'}）`}
      >
        <Button size="small" icon={<UploadOutlined />} onClick={() => fileRef.current?.click()}>
          {buttonLabel}
        </Button>
      </Tooltip>
    </>
  )
}
