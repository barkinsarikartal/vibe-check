'use client'

import { useEffect, useState } from 'react'
import Comment from '@/components/Comment'

export default function GroupPage({ params }: { params: { id: string } }) {
  const [group, setGroup] = useState<any>(null)

  useEffect(() => {
    fetch(`/api/groups/${params.id}`)
      .then((r) => r.json())
      .then(setGroup)
  }, [params.id])

  if (!group) return <p>Loading…</p>

  return (
    <main>
      <h1>{group.name}</h1>
      <h2>Members</h2>
      <ul>
        {group.members?.map((m: any) => (
          <li key={m.user_id}>{m.profiles?.full_name}</li>
        ))}
      </ul>
      <h2>Expenses</h2>
      <ul>
        {group.expenses?.map((e: any) => (
          <li key={e.id}>
            {e.description}: ${(e.amount / 100).toFixed(2)}
          </li>
        ))}
      </ul>
      <h2>Comments</h2>
      {group.comments?.map((c: any) => (
        <Comment key={c.id} author={c.author_name} body={c.body} createdAt={c.created_at} />
      ))}
    </main>
  )
}
