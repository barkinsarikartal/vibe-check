import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Splitly',
  description: 'Split bills with friends',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
