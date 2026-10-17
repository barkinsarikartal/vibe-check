'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

const ADMIN_EMAILS = ['founder@splitly.app']

export default function AdminPage() {
  const router = useRouter()
  const [users, setUsers] = useState<any[]>([])

  useEffect(() => {
    supabase.auth.getUser().then(async ({ data }) => {
      if (!data.user || !ADMIN_EMAILS.includes(data.user.email ?? '')) {
        router.push('/')
        return
      }
      const { data: profiles } = await supabase.from('profiles').select('*')
      setUsers(profiles ?? [])
    })
  }, [router])

  async function grantPro(id: string) {
    await supabase.from('profiles').update({ is_pro: true }).eq('id', id)
  }

  async function deleteUser(id: string) {
    await supabase.auth.admin.deleteUser(id)
    setUsers((u) => u.filter((x) => x.id !== id))
  }

  return (
    <main>
      <h1>Admin</h1>
      <table>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>{u.phone}</td>
              <td>{u.is_pro ? 'Pro' : 'Free'}</td>
              <td>
                <button onClick={() => grantPro(u.id)}>Grant Pro</button>
                <button onClick={() => deleteUser(u.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  )
}
