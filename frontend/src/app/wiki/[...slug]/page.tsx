// This can be a Server Component as data fetching will happen server-side initially.
import Link from 'next/link';
import WikiNavigation from '@/components/WikiNavigation/WikiNavigation';
// No Markdown renderer for now, will display as string.

type Props = {
  params: { slug: string[] }; // slug will be [owner, repo_name, ...path]
  searchParams: { [key: string]: string | string[] | undefined };
};

// Simulate fetching Wiki content
async function getWikiContent(owner: string, repoName: string, path?: string) {
  // TODO: Replace with actual backend API call:
  // const res = await fetch(`/api/wiki/${owner}/${repoName}/${path || ''}`);
  // if (!res.ok) return { title: "错误", content: "无法加载 Wiki 内容。", navigation: [] };
  // const data = await res.json();
  // return { title: data.title, content: data.content_markdown, navigation: data.navigation };

  console.log(`Simulating fetch for: ${owner}/${repoName}/${path || 'main page'}`);
  // Hardcoded sample content
  const sampleMarkdownContent = `
# ${repoName} - ${path || '主页'}

这是为仓库 **${owner}/${repoName}** 自动生成的 Wiki 页面。

## 概述
本项目旨在提供一个强大的工具，用于...

## 主要特点
- 特点 A
- 特点 B
- 特点 C

## 如何开始
1. 安装依赖。
2. 配置环境。
3. 运行应用。

---
### 更多信息
请参阅其他相关文档页面或提出问题。
  `;
  return { 
    title: `${repoName} ${path ? `- ${path}` : 'Wiki'}`, 
    content: sampleMarkdownContent, 
    // Simulated navigation data, WikiNavigation component will use its own sample for now
    navigationData: [ 
      { id: "overview", title: "概述", level: 1 },
      { id: "features", title: "主要特点", level: 2 },
      { id: "getting-started", title: "如何开始", level: 2 },
    ]
  };
}


export default async function WikiPage({ params }: Props) {
  const { slug } = params;
  const owner = slug?.[0] || '未知所有者';
  const repoName = slug?.[1] || '未知仓库';
  // For now, we assume the slug is just [owner, repo_name] and we are on the main wiki page.
  // Later, slug could be [owner, repo_name, ...path_segments_for_sub_pages]
  const wikiPath = slug?.slice(2).join('/') || ''; 

  const { title, content, navigationData } = await getWikiContent(owner, repoName, wikiPath);
  const repoSlug = `${owner}/${repoName}`;

  return (
    <div className="container mx-auto px-4 py-6">
      <header className="mb-6 pb-4 border-b border-gray-200">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-800">{title}</h1>
        <p className="text-sm text-gray-500 mt-1">
          仓库: <Link href={`https://github.com/${repoSlug}`} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{repoSlug}</Link>
        </p>
      </header>
      
      <div className="grid grid-cols-1 md:grid-cols-12 gap-x-8 gap-y-6">
        <aside className="col-span-12 md:col-span-3 md:sticky md:top-8 h-full md:max-h-[calc(100vh-4rem)] overflow-y-auto pr-2">
          <div className="bg-white p-4 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-3 text-gray-700 border-b pb-2">导航</h2>
            <WikiNavigation basePath={`/wiki/${repoSlug}`} navigationData={navigationData} />
          </div>
        </aside>

        <main className="col-span-12 md:col-span-9">
          <article className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl font-bold mb-4 text-gray-700 sr-only">Wiki 内容</h2>
            {/* Displaying Markdown as a preformatted string for now */}
            <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-md text-sm font-mono overflow-x-auto">
              {content}
            </pre>
            {/* 
              When ready to render Markdown:
              <ReactMarkdown className="prose lg:prose-xl max-w-none">
                {content}
              </ReactMarkdown>
            */}
          </article>
          
          <section className="mt-10 p-6 bg-white rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-3 text-gray-700">对此仓库有疑问？</h2>
            <p className="text-gray-600 mb-4">
              您可以前往问答页面，针对 <code className="font-mono bg-gray-100 p-1 rounded">{repoSlug}</code> 仓库提出您的问题。
            </p>
            <Link href={`/query/${repoSlug}`} legacyBehavior>
              <a className="inline-block px-5 py-2 text-base font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors">
                前往问答页面
              </a>
            </Link>
             {/* Or embed QueryInterface directly:
            <div className="mt-4 p-4 border border-dashed border-gray-400 rounded-md min-h-[100px]">
              [QueryInterface Component Placeholder for {repoSlug}]
            </div>
            */}
          </section>
        </main>
      </div>
    </div>
  );
}
