import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Radar Health Index',
  description: 'Real-time Supply Chain Health Monitor',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
