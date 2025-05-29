import RepoInput from "@/components/RepoInput/RepoInput";
import ExampleRepos from "@/components/ExampleRepos/ExampleRepos";

export default function HomePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <header className="text-center mb-12">
        <h1 className="text-5xl font-extrabold text-gray-800 mb-4">
          Open-DeepWiki
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          输入 GitHub 链接，即刻拥有专属知识库与 Wiki！探索、学习并贡献给开源项目从未如此简单。
        </p>
      </header>

      <section className="mb-16">
        <RepoInput />
      </section>

      <section>
        <ExampleRepos />
      </section>

      {/* Optional: Add more sections like Features, How it works, etc. */}
      {/* <section className="mt-16 py-8 bg-slate-50 rounded-lg shadow">
        <h2 className="text-3xl font-bold text-center text-gray-700 mb-8">核心功能</h2>
        <div className="grid md:grid-cols-3 gap-8 px-4">
          <div className="p-6 bg-white rounded-lg shadow-md">
            <h3 className="text-xl font-semibold text-blue-600 mb-2">自动化知识提取</h3>
            <p className="text-gray-600">自动从GitHub仓库提取信息，构建可查询的知识库。</p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow-md">
            <h3 className="text-xl font-semibold text-blue-600 mb-2">智能Wiki生成</h3>
            <p className="text-gray-600">基于知识库内容，自动生成结构化的Wiki页面。</p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow-md">
            <h3 className="text-xl font-semibold text-blue-600 mb-2">上下文感知问答</h3>
            <p className="text-gray-600">提供自然语言问答界面，精准回答相关问题。</p>
          </div>
        </div>
      </section> */}
    </div>
  );
}
