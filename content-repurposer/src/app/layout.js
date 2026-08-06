import "./globals.css";

export const metadata = {
  title: "RePurpose AI | Turn One Piece Into Ten",
  description: "AI-Powered Content Repurposing Tool for Creators.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
