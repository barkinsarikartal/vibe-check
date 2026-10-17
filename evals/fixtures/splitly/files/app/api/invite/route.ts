import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function POST(req: Request) {
  const { email, groupId } = await req.json()
  const token = Math.random().toString(36).slice(2, 10)

  await supabase.from('invites').insert({ email, group_id: groupId, token })
  console.log('Invite created', { email, token, groupId })

  // TODO: send the email with Resend
  return NextResponse.json({ ok: true, link: `/join?token=${token}` })
}
