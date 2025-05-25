import type { Metadata } from "next";
import Image from "next/image";

import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { LanguageProvider } from './context/LanguageContext';
import Header from './components/Header';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Nordea - AI Assistant",
  description: "Personal assistant for banking and fincances",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased max-h-full`}
      >
        <LanguageProvider>
        <Header />
        {children}
        </LanguageProvider>
      </body>
    </html>
  );
}
