'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function ProPage() {
  const searchParams = useSearchParams()
  const [isPro, setIsPro] = useState(false)

  useEffect(() => {
    if (searchParams.get('success')) localStorage.setItem('isPro', 'true')
    setIsPro(localStorage.getItem('isPro') === 'true')
  }, [searchParams])

  async function upgrade() {
    const { data } = await supabase.auth.getUser()
    const res = await fetch('/api/checkout', {
      method: 'POST',
      body: JSON.stringify({ priceAmount: 499, userId: data.user?.id }),
    })
    const { url } = await res.json()
    window.location.href = url
  }

  async function exportCsv() {
    const { data } = await supabase.from('expenses').select('description, amount, paid_by, created_at')
    const rows = (data ?? []).map((e) => [e.description, e.amount / 100, e.paid_by, e.created_at].join(','))
    const blob = new Blob([['description,amount,paid_by,date', ...rows].join('\n')], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'splitly-expenses.csv'
    a.click()
  }

  return (
    <main>
      <h1>Splitly Pro</h1>
      {isPro ? (
        <button onClick={exportCsv}>Export all expenses (CSV)</button>
      ) : (
        <button onClick={upgrade}>Upgrade for $4.99 (lifetime)</button>
      )}
    </main>
  )
}
