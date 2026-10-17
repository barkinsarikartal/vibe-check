import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

// body: { group_id, amount, description, paid_by, split_between }
export async function POST(req: Request) {
  const body = await req.json()
  const { data, error } = await supabase.from('expenses').insert(body).select().single()
  if (error) {
    return NextResponse.json({ error: error.message, details: error }, { status: 500 })
  }
  return NextResponse.json(data)
}
