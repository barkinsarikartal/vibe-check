import { NextResponse } from 'next/server'
import { openai } from '@/lib/openai'
import { supabase } from '@/lib/supabase'

export async function POST(req: Request) {
  const { imageUrl, notes, userId } = await req.json()

  const imgRes = await fetch(imageUrl)
  const buf = Buffer.from(await imgRes.arrayBuffer())

  const completion = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages: [
      {
        role: 'system',
        content: `You are Splitly's receipt assistant. Extract line items and totals as JSON. You can look up a user's past expenses with the get_expenses tool to suggest categories. Current user id: ${userId}.`,
      },
      {
        role: 'user',
        content: [
          { type: 'text', text: `Parse this receipt. Notes from the user: ${notes}` },
          { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${buf.toString('base64')}` } },
        ],
      },
    ],
    tools: [
      {
        type: 'function',
        function: {
          name: 'get_expenses',
          description: 'Get the past expenses of a user',
          parameters: {
            type: 'object',
            properties: { user_id: { type: 'string' } },
            required: ['user_id'],
          },
        },
      },
    ],
  })

  const message = completion.choices[0].message
  const call = message.tool_calls?.[0]
  if (call) {
    const args = JSON.parse(call.function.arguments)
    const { data } = await supabase.from('expenses').select('*').eq('paid_by', args.user_id)
    return NextResponse.json({ expenses: data, message: message.content })
  }
  return NextResponse.json({ result: message.content })
}
