"use client"; 

import React, { useState } from 'react';
import { useRouter } from 'next/navigation'; // Import useRouter

const GITHUB_URL_REGEX = /^https:\/\/github\.com\/[a-zA-Z0-9-]+\/[a-zA-Z0-9_.-]+(?:\.git)?\/?$/;

const RepoInput = () => {
  const [repoUrl, setRepoUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const router = useRouter(); // Initialize useRouter

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null); // Clear previous errors

    if (!repoUrl.trim()) {
      setError('请输入 GitHub 仓库 URL。');
      return;
    }

    if (!GITHUB_URL_REGEX.test(repoUrl)) {
      setError('请输入一个有效的 GitHub 仓库 URL (例如 https://github.com/owner/repo)。');
      return;
    }

    // Simulate backend API call and task creation
    console.log('正在提交仓库 URL:', repoUrl); 
    // TODO: Replace with actual API call to trigger backend processing
    // const response = await fetch('/api/repository/submit', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ url: repoUrl }),
    // });
    // if (!response.ok) {
    //   const errorData = await response.json();
    //   setError(errorData.detail || '提交仓库失败。');
    //   return;
    // }
    // const taskData = await response.json();
    // const taskId = taskData.task_id;

    // Mocked task ID generation
    const mockTaskId = `mock_task_${Date.now()}`;
    console.log('生成的模拟任务 ID:', mockTaskId);

    // Navigate to the wait page
    router.push(`/wait/${mockTaskId}`);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col items-center w-full max-w-2xl mx-auto p-4 sm:p-6 bg-white rounded-xl shadow-lg">
      <label htmlFor="repoUrl" className="sr-only">
        GitHub 仓库 URL
      </label>
      <input
        type="url" // Changed type to "url" for better browser validation hints
        id="repoUrl"
        name="repoUrl"
        value={repoUrl}
        onChange={(e) => {
          setRepoUrl(e.target.value);
          if (error) setError(null); // Clear error when user types
        }}
        placeholder="例如：https://github.com/owner/repository-name"
        className={`w-full px-4 py-3 mb-3 text-base sm:text-lg border rounded-lg transition-colors duration-150 ease-in-out
                    focus:ring-2 focus:border-transparent outline-none 
                    ${error ? 'border-red-500 focus:ring-red-400' : 'border-gray-300 focus:ring-blue-500 hover:border-gray-400'}
                    shadow-sm`}
        aria-describedby={error ? "repoUrl-error" : undefined}
      />
      {error && (
        <p id="repoUrl-error" className="text-red-600 text-sm mb-3 text-left w-full">
          {error}
        </p>
      )}
      <button
        type="submit"
        className="w-full sm:w-auto px-10 py-3 text-base sm:text-lg font-semibold text-white bg-blue-600 rounded-lg 
                   hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 
                   transition-all duration-150 ease-in-out shadow-md hover:shadow-lg transform hover:scale-105"
      >
        开始分析
      </button>
    </form>
  );
};

export default RepoInput;
