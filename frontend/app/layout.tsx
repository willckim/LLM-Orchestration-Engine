import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'LLM Orchestration Engine',
  description: 'Enterprise-grade multi-model LLM routing with intelligent cost optimization and observability',
  keywords: ['LLM', 'AI', 'Machine Learning', 'API', 'Orchestration', 'GPT', 'Claude'],
  authors: [{ name: 'Your Name' }],
  openGraph: {
    title: 'LLM Orchestration Engine',
    description: 'Intelligent multi-model routing for LLMs',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}