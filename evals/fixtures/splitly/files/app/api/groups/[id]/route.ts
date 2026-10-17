import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const { data: group, error } = await supabase
    .from('groups')
    .select('*, expenses(*), comments(*), members:group_members(user_id, profiles(email, full_name, phone))')
    .eq('id', params.id)
    .single()

  if (error) {
    return NextResponse.json({ error: error.message, details: error }, { status: 500 })
  }
  return NextResponse.json(group)
}
