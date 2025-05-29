"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation'; // For programmatic navigation (optional here)
import Link from 'next/link';
import ProgressBar from '@/components/ProgressBar/ProgressBar'; 

// Simulate API call function from lib/api.ts (to be implemented later)
// import { getTaskStatus } from '@/lib/api'; 

type TaskStatus = 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILURE' | 'UNKNOWN';

interface TaskResult {
  repoSlug?: string; // e.g., "owner/repo" for navigation
  message?: string;  // Message from backend task result
  error?: string;    // Error message from backend task result
  [key: string]: any; 
}

export default function WaitPage() {
  const params = useParams();
  const router = useRouter(); 
  const taskId = params.task_id as string;

  const [status, setStatus] = useState<TaskStatus>('PENDING');
  const [progress, setProgress] = useState(0); // Overall progress for the bar
  const [statusMessage, setStatusMessage] = useState('任务已提交，正在等待处理...'); // Message for the progress bar
  const [error, setError] = useState<string | null>(null); // Page-level error, e.g., API fetch failed
  const [taskResult, setTaskResult] = useState<TaskResult | null>(null); // To store results from successful/failed task

  useEffect(() => {
    if (!taskId) return;

    setStatus('PENDING');
    setProgress(0);
    setStatusMessage('正在初始化任务状态查询...');
    setError(null);
    setTaskResult(null);

    const intervalId = setInterval(async () => {
      // --- MOCK IMPLEMENTATION FOR TASK STATUS POLLING ---
      // This simulates fetching status from `/api/status/{taskId}`
      // In a real app, replace this with: `const data = await getTaskStatus(taskId);`
      
      let newProgress = progress;
      let currentStatus = status;
      let currentStatusMessage = statusMessage;
      let currentTaskResult = taskResult;
      let currentError = error;

      if (currentStatus === 'PENDING' || currentStatus === 'PROCESSING') {
        newProgress += 20; // Simulate progress
        if (newProgress >= 100) {
          if (taskId.includes('fail')) { // Simulate failure for specific task IDs
            currentStatus = 'FAILURE';
            currentStatusMessage = '任务处理失败。';
            currentError = '模拟的任务处理失败。';
            currentTaskResult = { error: currentError };
          } else {
            currentStatus = 'SUCCESS';
            currentStatusMessage = '任务已成功完成！';
            currentTaskResult = { repoSlug: 'owner/simulated-repo', message: 'Wiki 已成功生成！' };
          }
          newProgress = 100;
          clearInterval(intervalId); // Stop polling on completion/failure
        } else {
          currentStatus = 'PROCESSING';
          currentStatusMessage = `正在处理中... (${newProgress}%)`;
        }
      }
      
      setProgress(newProgress);
      setStatus(currentStatus);
      setStatusMessage(currentStatusMessage);
      setTaskResult(currentTaskResult);
      setError(currentError);
      // --- END OF MOCK IMPLEMENTATION ---

    }, 1500); // Poll every 1.5 seconds

    return () => clearInterval(intervalId);
  }, [taskId]); // Only re-run if taskId changes. Internal state updates won't re-trigger this effect.

  const renderStatusDetails = () => {
    if (status === 'SUCCESS') {
      return (
        <div className="mt-6 text-center p-6 bg-green-50 border border-green-200 rounded-lg">
          <h2 className="text-2xl font-semibold text-green-700 mb-3">
            {taskResult?.message || '任务已成功完成！'}
          </h2>
          {taskResult?.repoSlug && (
            <Link href={`/wiki/${taskResult.repoSlug}`} legacyBehavior>
              <a className="inline-block px-6 py-3 text-lg font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors shadow-md hover:shadow-lg">
                前往 Wiki 页面
              </a>
            </Link>
          )}
        </div>
      );
    }
    if (status === 'FAILURE') {
      return (
        <div className="mt-6 text-center p-6 bg-red-50 border border-red-200 rounded-lg">
          <h2 className="text-2xl font-semibold text-red-700 mb-3">任务处理失败</h2>
          <p className="text-red-600">{error || taskResult?.error || '发生未知错误。'}</p>
          <Link href="/" legacyBehavior>
            <a className="mt-4 inline-block px-6 py-3 text-lg font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
              返回首页
            </a>
          </Link>
        </div>
      );
    }
    // PENDING or PROCESSING
    return (
      <div className="mt-4 text-center">
        {/* Status message is now part of ProgressBar */}
        {status === 'PROCESSING' && <p className="text-sm text-gray-500 mt-1">请稍候，页面将在完成后更新...</p>}
      </div>
    );
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-200px)] p-4 sm:p-8 text-center">
      <div className="bg-white p-6 sm:p-10 rounded-xl shadow-2xl w-full max-w-2xl">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-4">
          {status === 'SUCCESS' || status === 'FAILURE' ? '任务结果' : '任务处理中'}
        </h1>
        <p className="text-gray-600 mb-6">
          任务 ID: 
          <code className="ml-1 font-mono bg-gray-100 text-blue-600 px-2 py-1 rounded text-sm">{taskId}</code>
        </p>
        
        <div className="my-8 w-full">
          <ProgressBar 
            taskId={taskId} 
            currentProgress={progress}
            currentStatusMessage={statusMessage}
            isError={status === 'FAILURE'}
            isComplete={status === 'SUCCESS' || status === 'FAILURE'}
          />
        </div>
        
        {renderStatusDetails()}

        {status !== 'SUCCESS' && status !== 'FAILURE' && (
           <p className="mt-8 text-sm text-gray-500">
            您可以暂时离开此页面，稍后通过任务 ID 查询状态，或等待此页面自动更新。
          </p>
        )}
      </div>
    </div>
  );
}
