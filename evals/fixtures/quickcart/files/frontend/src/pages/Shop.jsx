import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function Shop() {
  const [products, setProducts] = useState([])
  const [q, setQ] = useState('')

  useEffect(() => {
    api.get('/api/products', { params: { q } }).then((r) => setProducts(r.data))
  }, [q])

  function addToCart(p) {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]')
    cart.push({ id: p.id, name: p.name, price_cents: p.price_cents, qty: 1 })
    localStorage.setItem('cart', JSON.stringify(cart))
  }

  return (
    <main>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" />
      {products.map((p) => (
        <div key={p.id}>
          <h3>{p.name}</h3>
          <div dangerouslySetInnerHTML={{ __html: p.description }} />
          <button onClick={() => addToCart(p)}>Add ${(p.price_cents / 100).toFixed(2)}</button>
        </div>
      ))}
      <Link to="/checkout">Checkout</Link>
    </main>
  )
}
