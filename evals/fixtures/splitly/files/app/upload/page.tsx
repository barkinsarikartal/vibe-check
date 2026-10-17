'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function UploadPage() {
  const [result, setResult] = useState<any>(null)
  const [notes, setNotes] = useState('')

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const { data: userData } = await supabase.auth.getUser()
    const path = `${userData.user?.id}/${file.name}`
    await supabase.storage.from('receipts').upload(path, file, { upsert: true })
    const { data } = supabase.storage.from('receipts').getPublicUrl(path)

    const res = await fetch('/api/parse-receipt', {
      method: 'POST',
      body: JSON.stringify({ imageUrl: data.publicUrl, notes, userId: userData.user?.id }),
    })
    setResult(await res.json())
  }

  return (
    <main>
      <h1>Scan a receipt</h1>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Anything we should know?" />
      <input type="file" accept="image/*" onChange={onFile} />
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </main>
  )
}
