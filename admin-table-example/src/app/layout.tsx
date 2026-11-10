import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Prisma Admin Table", description: "URL-driven TanStack table demo" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
