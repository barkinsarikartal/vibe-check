import { NextResponse } from 'next/server'
import { stripe } from '@/lib/stripe'

export async function POST(req: Request) {
  const { priceAmount, userId } = await req.json()
  const origin = req.headers.get('origin')

  const session = await stripe.checkout.sessions.create({
    mode: 'payment',
    line_items: [
      {
        price_data: {
          currency: 'usd',
          product_data: { name: 'Splitly Pro (lifetime)' },
          unit_amount: priceAmount,
        },
        quantity: 1,
      },
    ],
    client_reference_id: userId,
    success_url: `${origin}/pro?success=1`,
    cancel_url: `${origin}/pro`,
  })

  return NextResponse.json({ url: session.url })
}
