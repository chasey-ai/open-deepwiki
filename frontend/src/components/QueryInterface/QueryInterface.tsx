"use client";

import React, { useState, useRef, useEffect } from 'react';
// import { askQuestion } from '@/lib/api'; // To be implemented for actual API calls

interface QueryInterfaceProps {
  repositoryIdentifier: string; // e.g., the repository URL
}

interface SourceDocument {
  content: string;
  meta: Record<string, any>;
}

interface ChatMessage {
  id: string;
  type: 'question' | 'answer' | 'error';
  text: string;
  sources?: SourceDocument[];
}

const QueryInterface: React.FC<QueryInterfaceProps> = ({ repositoryIdentifier }) => {
  const [questionInput, setQuestionInput] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom of chat history when new messages are added
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const currentQuestion = questionInput.trim();
    if (!currentQuestion) return;

    setError(null);
    setChatHistory(prev => [...prev, { id: Date.now().toString(), type: 'question', text: currentQuestion }]);
    setIsLoading(true);
    setQuestionInput(''); // Clear input after submitting

    // Simulate API call
    // TODO: Replace with actual API call: `const response = await askQuestion(repositoryIdentifier, currentQuestion);`
    setTimeout(() => {
      // Simulate success
      if (!currentQuestion.toLowerCase().includes('error')) {
        const mockAnswer = `这是针对您的问题 "${currentQuestion}" 的模拟回答。该答案基于仓库 ${repositoryIdentifier} 的内容生成。我们发现了一些相关的文档片段，可能对您有帮助。`;
        const mockSources: SourceDocument[] = [
          { content: "这是第一个模拟的源文档片段，它解释了项目的核心概念...", meta: { source: "README.md", page: 1 } },
          { content: "第二个相关的片段来自贡献指南，详细说明了如何参与项目...", meta: { source: "CONTRIBUTING.md", section: "Setup" } },
        ];
        setChatHistory(prev => [...prev, { id: Date.now().toString(), type: 'answer', text: mockAnswer, sources: mockSources }]);
      } else {
      // Simulate error
        const errorMessage = `处理您的问题 "${currentQuestion}" 时发生模拟错误。请稍后再试。`;
        setChatHistory(prev => [...prev, { id: Date.now().toString(), type: 'error', text: errorMessage }]);
        setError(errorMessage); // Also display a more prominent error if needed
      }
      setIsLoading(false);
    }, 1500);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] max-h-[700px] bg-white rounded-xl shadow-2xl overflow-hidden">
      {/* Chat history */}
      <div ref={chatContainerRef} className="flex-grow p-6 space-y-4 overflow-y-auto">
        {chatHistory.map((msg) => (
          <div key={msg.id} className={`flex ${msg.type === 'question' ? 'justify-end' : 'justify-start'}`}>
            <div 
              className={`max-w-xl lg:max-w-2xl px-4 py-3 rounded-2xl shadow ${
                msg.type === 'question' ? 'bg-blue-500 text-white rounded-br-none' : 
                msg.type === 'answer' ? 'bg-gray-100 text-gray-800 rounded-bl-none' : 
                'bg-red-100 text-red-700 rounded-bl-none'
              }`}
            >
              <p className="whitespace-pre-line text-sm sm:text-base">{msg.text}</p>
              {msg.type === 'answer' && msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-2 border-t border-gray-200">
                  <h4 className="text-xs font-semibold text-gray-500 mb-1">相关来源:</h4>
                  <ul className="space-y-1">
                    {msg.sources.map((source, index) => (
                      <li key={index} className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                        <span className="font-medium">{source.meta.source || '未知来源'}:</span> 
                        <p className="mt-0.5 italic truncate">"{source.content}"</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="max-w-xs px-4 py-3 rounded-2xl shadow bg-gray-100 text-gray-800 rounded-bl-none">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-75"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-150"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-300"></div>
                <span className="text-sm text-gray-500">思考中...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 bg-gray-50">
        {error && <p className="text-red-500 text-sm mb-2 text-center">{error}</p>}
        <div className="flex items-center space-x-3">
          <textarea
            value={questionInput}
            onChange={(e) => setQuestionInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e as any); // FormEvent is fine here
              }
            }}
            placeholder={`向 ${repositoryIdentifier} 提问...`}
            rows={1}
            className="flex-grow p-3 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-shadow text-sm sm:text-base"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="px-5 py-3 text-white bg-blue-600 rounded-xl hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:bg-gray-400 transition-colors"
            disabled={isLoading || !questionInput.trim()}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path d="M3.105 3.105a1.5 1.5 0 012.121 0L10 7.879l4.774-4.774a1.5 1.5 0 112.121 2.121L12.121 10l4.774 4.774a1.5 1.5 0 11-2.121 2.121L10 12.121l-4.774 4.774a1.5 1.5 0 11-2.121-2.121L7.879 10 3.105 5.226a1.5 1.5 0 010-2.121z" clipRule="evenodd" opacity={questionInput.trim() ? 0 : 1} className="transform transition-opacity duration-200 ease-in-out"/> {/* Placeholder for send icon, this is a close icon for now */}
              <path d="M3.105 3.105a1.5 1.5 0 012.121 0L10 7.879l4.774-4.774a1.5 1.5 0 112.121 2.121L12.121 10l4.774 4.774a1.5 1.5 0 11-2.121 2.121L10 12.121l-4.774 4.774a1.5 1.5 0 11-2.121-2.121L7.879 10 3.105 5.226a1.5 1.5 0 010-2.121z" transform="rotate(45 10 10) scale(0.7)" opacity={questionInput.trim() ? 1 : 0} className="transform transition-opacity duration-200 ease-in-out"/> {/* Placeholder for send icon, this is a Paper Airplane for now */}
            </svg>
            <span className="sr-only">发送</span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default QueryInterface;
