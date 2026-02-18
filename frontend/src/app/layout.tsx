import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PostgreSQL Observability Agent",
  description:
    "AI-powered PostgreSQL monitoring via Prometheus & VictoriaMetrics",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
