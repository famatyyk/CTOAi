import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "CTOAi – STRATEGOS",
  description: "Twoj osobisty CTO AI – platforma AI Operations stworzona przez Jakuba P.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl" className="dark">
      <body className="bg-surface text-white antialiased">{children}</body>
    </html>
  )
}
