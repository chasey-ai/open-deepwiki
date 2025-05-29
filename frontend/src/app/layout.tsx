import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css"; // 导入 Tailwind CSS

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Open-DeepWiki",
  description: "输入 GitHub 链接，即刻拥有专属知识库与 Wiki！",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN"> {/* 语言设置为中文 */}
      <body className={`${inter.className} bg-gray-50 text-gray-800 flex flex-col min-h-screen`}>
        <header className="bg-white shadow-md">
          <nav className="container mx-auto px-6 py-4 flex justify-between items-center">
            <div className="text-2xl font-bold text-blue-600">
              <a href="/">Open-DeepWiki</a>
            </div>
            {/* 可以添加导航链接，例如 /about, /docs 等 */}
            {/* <div>
              <a href="/docs" className="text-gray-600 hover:text-blue-500 px-3">文档</a>
              <a href="/about" className="text-gray-600 hover:text-blue-500 px-3">关于</a>
            </div> */}
          </nav>
        </header>
        
        <main className="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        
        <footer className="bg-white border-t border-gray-200">
          <div className="container mx-auto px-6 py-4 text-center text-gray-500 text-sm">
            © {new Date().getFullYear()} Open-DeepWiki. 一个学习探索项目。
          </div>
        </footer>
      </body>
    </html>
  );
}
