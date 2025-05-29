// This can be a Server Component for now.
import QueryInterface from '@/components/QueryInterface/QueryInterface';
import Link from 'next/link';

type Props = {
  params: { slug: string[] }; // slug will be [owner, repo_name]
  searchParams: { [key: string]: string | string[] | undefined };
};

export default function QueryPage({ params }: Props) {
  const { slug } = params;
  // Assuming slug is [owner, repo_name]
  const owner = slug?.[0] || '未知所有者';
  const repoName = slug?.[1] || '未知仓库';
  const repoIdentifier = `${owner}/${repoName}`; // For display and passing to component
  // The actual repo URL for QueryInterface might be needed if it makes direct calls
  // or if the backend expects a full URL. For now, identifier is fine.
  const repoUrl = `https://github.com/${repoIdentifier}`;


  return (
    <div className="container mx-auto px-4 py-6">
      <header className="mb-8 pb-4 border-b border-gray-200">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-800">知识库问答</h1>
        <p className="text-lg text-gray-600 mt-2">
          针对仓库 <Link href={repoUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline"><code className="font-mono bg-gray-100 p-1 rounded">{repoIdentifier}</code></Link> 进行提问。
        </p>
        <p className="text-sm text-gray-500 mt-1">
          返回 <Link href={`/wiki/${repoIdentifier}`} className="text-blue-600 hover:underline">Wiki 页面</Link>。
        </p>
      </header>
      
      <div className="max-w-3xl mx-auto">
        <QueryInterface repositoryIdentifier={repoUrl} /> 
        {/* Pass the full repoUrl or just identifier based on QueryInterface needs */}
        
        {/* 
          The QueryInterface component itself will handle displaying:
          - Input for question
          - Button to submit
          - Area for answer
          - Area for source documents
          This page component primarily sets up the context (which repo).
        */}
      </div>
    </div>
  );
}
