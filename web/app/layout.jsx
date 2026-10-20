import './globals.css';

export const metadata = {
  title: '骷髅幻戏 · 客户看板',
  description: '私有平台 · 一人销售公司的客户与线索看板（数据全留本机）',
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
