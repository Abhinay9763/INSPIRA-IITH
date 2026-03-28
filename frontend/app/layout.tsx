import './globals.css'
import type { Metadata } from 'next'
import { DM_Sans } from 'next/font/google'

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-ui-google',
  weight: ['400', '500', '700'],
})

export const metadata: Metadata = {
  title: 'INSPIRA — Beyond the resume. Beyond the interview.',
  description: 'Editorial AI mock interview platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${dmSans.variable} bg-background text-ink-primary`}>
        {children}
      </body>
    </html>
  )
}