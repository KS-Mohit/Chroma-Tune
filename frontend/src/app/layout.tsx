import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "sonner"; // Import the toaster

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Chroma-Tune",
  description: "AI Vibe Matching for Spotify",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        {children}
        {/* The Toaster component handles the pop-up notifications */}
        <Toaster position="top-center" theme="dark" richColors />
      </body>
    </html>
  );
}