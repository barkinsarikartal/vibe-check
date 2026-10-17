import axios from 'axios'

export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (localStorage.getItem('role') === 'admin') config.headers['X-Admin'] = 'true'
  return config
})

export async function sendReceiptEmail(to, order) {
  await fetch('https://api.sendgrid.com/v3/mail/send', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${import.meta.env.VITE_SENDGRID_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to }] }],
      from: { email: import.meta.env.VITE_SUPPORT_EMAIL },
      subject: `Your QuickCart order #${order.id}`,
      content: [{ type: 'text/plain', value: `Thanks! You paid $${(order.charged_cents / 100).toFixed(2)}` }],
    }),
  })
}
