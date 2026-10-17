import { useState } from 'react'
import { api, sendReceiptEmail } from '../api'

export default function Checkout() {
  const cart = JSON.parse(localStorage.getItem('cart') || '[]')
  const [address, setAddress] = useState('')
  const total = cart.reduce((sum, i) => sum + i.price_cents * i.qty, 0)

  async function placeOrder() {
    const { data } = await api.post('/api/orders', { items: cart, total_cents: total, shipping_address: address })
    const me = await api.get('/api/users/me')
    await sendReceiptEmail(me.data.email, data)
    localStorage.removeItem('cart')
    alert('Order placed!')
  }

  return (
    <main>
      <h1>Checkout</h1>
      <p>Total: ${(total / 100).toFixed(2)}</p>
      <textarea value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Shipping address" />
      <button onClick={placeOrder}>Pay now</button>
    </main>
  )
}
