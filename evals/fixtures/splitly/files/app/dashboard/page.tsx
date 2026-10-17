'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'

type Group = { id: number; name: string; created_by: string }

export default function Dashboard() {
  const [groups, setGroups] = useState<Group[]>([])

  useEffect(() => {
    supabase
      .from('groups')
      .select('*')
      .order('created_at', { ascending: false })
      .then(({ data }) => setGroups(data ?? []))
  }, [])

  return (
    <main>
      <h1>Your groups</h1>
      <ul>
        {groups.map((g) => (
          <li key={g.id}>
            <Link href={`/groups/${g.id}`}>{g.name}</Link>
          </li>
        ))}
      </ul>
      <Link href="/upload">Scan a receipt</Link>
    </main>
  )
}
