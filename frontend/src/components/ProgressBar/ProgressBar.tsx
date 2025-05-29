"use client"; 

import React from 'react';

interface ProgressBarProps {
  // taskId is kept for potential future use if the component needs to fetch its own details,
  // but for now, progress and statusMessage will be driven by props.
  taskId: string; 
  currentProgress: number; // Progress percentage (0-100)
  currentStatusMessage: string;
  isError?: boolean;
  isComplete?: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ 
  taskId, 
  currentProgress, 
  currentStatusMessage,
  isError = false,
  isComplete = false
}) => {
  const progressPercentage = isError ? 100 : Math.min(Math.max(currentProgress, 0), 100);
  const barColor = isError ? 'bg-red-500' : 'bg-blue-600';

  return (
    <div className="w-full p-4 bg-white rounded-lg shadow">
      <div className="mb-2">
        <p className="text-sm font-medium text-gray-700">
          任务 <code className="font-mono bg-gray-100 text-xs px-1 py-0.5 rounded">{taskId}</code> 状态: 
          <span className={`font-semibold ${isError ? 'text-red-600' : 'text-blue-600'}`}>
            {' '}{currentStatusMessage}
          </span>
        </p>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
        <div
          className={`h-4 rounded-full transition-all duration-300 ease-linear ${barColor}`}
          style={{ width: `${progressPercentage}%` }}
          role="progressbar"
          aria-valuenow={progressPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Task progress for ${taskId}`}
        ></div>
      </div>
      {isComplete && !isError && (
        <p className="text-sm text-green-600 mt-2 text-center font-semibold">处理完成！</p>
      )}
       {isError && (
        <p className="text-sm text-red-600 mt-2 text-center font-semibold">任务失败</p>
      )}
    </div>
  );
};

export default ProgressBar;
