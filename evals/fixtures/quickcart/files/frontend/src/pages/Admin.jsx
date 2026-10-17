import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Admin() {
  const [users, setUsers] = useState([])
  const isAdmin = localStorage.getItem('role') === 'admin'

  useEffect(() => {
    if (isAdmin) api.get('/api/admin/users').then((r) => setUsers(r.data))
  }, [isAdmin])

  if (!isAdmin) return <p>Not allowed</p>

  return (
    <main>
      <h1>Admin</h1>
      <ul>
        {users.map((u) => (
          <li key={u.id}>
            {u.email} ({u.role}) {u.address}
          </li>
        ))}
      </ul>
    </main>
  )
}
