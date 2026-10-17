'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function Home() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  async function signIn() {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/dashboard` },
    })
    if (!error) setSent(true)
  }

  return (
    <main>
      <h1>Splitly</h1>
      <p>Split bills with friends. Snap a receipt and we do the math.</p>
      {sent ? (
        <p>Check your inbox for a magic link.</p>
      ) : (
        <>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@email.com" />
          <button onClick={signIn}>Sign in</button>
        </>
      )}
    </main>
  )
}
