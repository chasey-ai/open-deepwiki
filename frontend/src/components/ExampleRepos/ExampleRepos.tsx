"use client"; 

import React from 'react';
import { useRouter } from 'next/navigation';

// Sample data for example repositories
const sampleRepos = [
  { name: "LangChain Python", url: "https://github.com/langchain-ai/langchain", description: "Building applications with LLMs through composability" },
  { name: "Haystack by deepset", url: "https://github.com/deepset-ai/haystack", description: "Open-source NLP framework for transformer models" },
  { name: "FastAPI", url: "https://github.com/tiangolo/fastapi", description: "A modern, fast (high-performance) web framework for building APIs" },
  // { name: "Next.js", url: "https://github.com/vercel/next.js", description: "The React Framework for Production" },
];

const ExampleRepos = () => {
  const router = useRouter();

  const handleRepoClick = (url: string, name: string) => {
    // Simulate backend API call and task creation (similar to RepoInput)
    console.log(`Example repository "${name}" selected for analysis:`, url);
    // TODO: Replace with actual API call if example repos should also trigger backend processing
    // For now, directly navigate to wait page with a mock task ID
    
    const mockTaskId = `mock_task_example_${name.replace(/\s+/g, '_').toLowerCase()}_${Date.now()}`;
    console.log('Generated mock task ID for example repo:', mockTaskId);

    router.push(`/wait/${mockTaskId}?repo_url=${encodeURIComponent(url)}`); // Pass repo_url for context on wait page if needed
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-4 sm:p-6 bg-white rounded-xl shadow-lg mt-10">
      <h2 className="text-2xl font-bold text-center text-gray-700 mb-6">或者，尝试一个示例仓库：</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sampleRepos.map((repo) => (
          <button
            key={repo.name}
            onClick={() => handleRepoClick(repo.url, repo.name)}
            className="block p-4 bg-gray-50 hover:bg-blue-50 rounded-lg shadow-md 
                       border border-gray-200 hover:border-blue-300 transition-all duration-150 
                       ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 text-left"
            title={`分析 ${repo.name}`}
          >
            <h3 className="text-lg font-semibold text-blue-600 mb-1">{repo.name}</h3>
            <p className="text-xs text-gray-500 break-all hidden sm:block">{repo.url}</p>
            <p className="text-sm text-gray-600 mt-1">{repo.description}</p>
          </button>
        ))}
      </div>
       <p className="text-xs text-center text-gray-400 mt-6">
        点击示例仓库将模拟提交过程并跳转到等待页面。
      </p>
    </div>
  );
};

export default ExampleRepos;
