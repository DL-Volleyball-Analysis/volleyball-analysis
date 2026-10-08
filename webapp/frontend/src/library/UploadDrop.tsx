import { useRef, useState, type DragEvent } from 'react'
import { ApiError } from '../api/client'
import { useUpload } from '../api/queries'

const ACCEPTED = ['.mp4', '.mov', '.avi', '.mkv', '.m4v']

function extension(name: string): string {
  const i = name.lastIndexOf('.')
  return i < 0 ? '' : name.slice(i).toLowerCase()
}

type Message = { file: string; text: string; ok: boolean }

export function UploadDrop() {
  const input = useRef<HTMLInputElement>(null)
  const upload = useUpload()
  const [over, setOver] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])

  async function add(files: FileList | null) {
    if (!files) return
    const out: Message[] = []
    for (const file of Array.from(files)) {
      if (!ACCEPTED.includes(extension(file.name))) {
        out.push({ file: file.name, ok: false, text: `is not a supported video type (${ACCEPTED.join(', ')})` })
        continue
      }
      try {
        await upload.mutateAsync(file)
        out.push({ file: file.name, ok: true, text: 'added, analysis queued' })
      } catch (e) {
        out.push({ file: file.name, ok: false, text: e instanceof ApiError ? e.message : 'could not be uploaded' })
      }
    }
    setMessages(out)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setOver(false)
    add(e.dataTransfer.files)
  }

  return (
    <section aria-label="Add videos">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        className={`flex flex-wrap items-center justify-between gap-3 rounded border border-dashed px-4 py-3 ${
          over ? 'border-accent bg-panel' : 'border-line'
        }`}
      >
        <p className="text-ink-muted">Drop match videos here to analyse them.</p>
        <button
          type="button"
          onClick={() => input.current?.click()}
          disabled={upload.isPending}
          className="rounded bg-accent px-3 py-1.5 font-medium text-on-accent disabled:opacity-60"
        >
          {upload.isPending ? 'Uploading…' : 'Choose files'}
        </button>
        <input
          ref={input}
          type="file"
          accept={ACCEPTED.join(',')}
          multiple
          hidden
          data-testid="file-input"
          onChange={(e) => {
            add(e.target.files)
            e.target.value = ''
          }}
        />
      </div>
      {messages.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-[13px]" aria-live="polite">
          {messages.map((m) => (
            <li key={m.file} className={m.ok ? 'text-ink-muted' : 'text-review'}>
              <span className="font-medium">{m.file}</span> {m.text}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
