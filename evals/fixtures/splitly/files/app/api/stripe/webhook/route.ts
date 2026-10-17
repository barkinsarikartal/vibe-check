import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function POST(req: Request) {
  const event = await req.json()
  console.log('Stripe event received', JSON.stringify(event))

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object
    await supabase.from('profiles').update({ is_pro: true }).eq('id', session.client_reference_id)
  }

  return NextResponse.json({ received: true })
}
