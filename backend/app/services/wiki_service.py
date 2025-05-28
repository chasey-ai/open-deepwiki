import logging
from fastapi import HTTPException

# 假设 GithubService 与当前文件在同一目录或可通过 PYTHONPATH 访问
# 如果项目结构需要，请调整导入路径。
# from backend.app.services.github_service import GithubService
# 对于此特定环境，路径可能不同，我们假设：
from .github_service import GithubService # 如果在同一包内，则为相对导入
from agents.pipelines.wiki_pipeline import WikiPipeline 

# 配置日志
logger = logging.getLogger(__name__)
# 确保在应用程序的入口点或日志配置文件中配置日志。
# 例如，如果尚未设置，则执行 logging.basicConfig(level=logging.INFO)。

class WikiService:
    def __init__(self, github_service: GithubService):
        """
        使用 GithubService 实例初始化 WikiService。
        """
        if not isinstance(github_service, GithubService):
            logger.error(f"初始化 WikiService 失败：github_service 不是 GithubService 的实例。提供的类型：{type(github_service)}") # Failed to initialize WikiService: github_service is not an instance of GithubService. Type provided: {type(github_service)}
            raise TypeError("github_service 必须是 GithubService 的实例") # github_service must be an instance of GithubService
        self.github_service = github_service
        
        try:
            # 初始化 WikiPipeline。
            # 这可能需要配置 (例如 LLM 的 API 密钥)，通过环境变量传递
            # 或一个配置对象，WikiPipeline 的 __init__ 方法应该处理这些。
            self.wiki_pipeline = WikiPipeline()
            logger.info("WikiService: WikiPipeline 初始化成功。") # WikiService: WikiPipeline initialized successfully.
        except Exception as e:
            logger.exception("WikiService: WikiPipeline 初始化失败。") # WikiService: Failed to initialize WikiPipeline. # Logs traceback
            # 这是一个严重故障，服务不应启动或应指示其处于降级状态。
            # WikiService: 关键组件 WikiPipeline 初始化失败
            raise RuntimeError(f"WikiService: 关键组件 WikiPipeline 初始化失败: {e}")

    async def generate_wiki_from_repo_readme(self, repo_url: str) -> str:
        """
        根据给定 GitHub 仓库 URL 的 README 生成 wiki 页面内容。

        参数:
            repo_url: GitHub 仓库的 URL。

        返回:
            生成的 wiki 内容字符串。

        引发:
            HTTPException: 如果获取 README 失败或 wiki 生成过程失败。
        """
        logger.info(f"WikiService: 尝试从仓库 {repo_url} 的 README 生成 wiki。") # WikiService: Attempting to generate wiki from README for repo: {repo_url}
        try:
            readme_content = await self.github_service.get_readme_content(repo_url)
            if not readme_content or readme_content.isspace():
                logger.warning(f"WikiService: 仓库 {repo_url} 的 README 内容为空或仅包含空格。") # WikiService: README content for {repo_url} is empty or whitespace.
                # 仓库 {repo_url} 的 README 内容为空或仅包含空格。无法生成 Wiki。
                raise HTTPException(status_code=404, detail=f"仓库 {repo_url} 的 README 内容为空或仅包含空格。无法生成 Wiki。")
        except HTTPException as e:
            logger.error(f"WikiService: 获取仓库 {repo_url} 的 README 时出错: {e.detail} (状态码: {e.status_code})") # WikiService: Error fetching README for {repo_url}: {e.detail} (Status: {e.status_code})
            # 从 GithubService 重新引发 HTTPException，由 API 层处理
            raise e 
        except Exception as e:
            # 捕获 get_readme_content 中的任何其他意外错误
            logger.exception(f"WikiService: 获取仓库 {repo_url} 的 README 时发生意外错误。") # WikiService: Unexpected error fetching README for {repo_url}.
            # 获取 README 时发生意外错误
            raise HTTPException(status_code=500, detail=f"获取 README 时发生意外错误: {str(e)}")

        logger.info(f"WikiService: 成功获取仓库 {repo_url} 的 README。长度: {len(readme_content)} 字符。") # WikiService: Successfully fetched README for {repo_url}. Length: {len(readme_content)} characters.
        logger.info("WikiService: 调用 WikiPipeline...") # WikiService: Invoking WikiPipeline...

        try:
            # WikiPipeline.run 方法需要一个包含 'repo_url' 和 'repo_summary_markdown' 的字典。
            pipeline_input = {"repo_url": repo_url, "repo_summary_markdown": readme_content}
            
            # 假设 WikiPipeline.run 是同步的。如果是异步的，则应为 `await self.wiki_pipeline.run(...)`
            pipeline_output = self.wiki_pipeline.run(data=pipeline_input)
            
            if not pipeline_output:
                logger.error(f"WikiService: WikiPipeline 为仓库 {repo_url} 返回了空或 None 的输出。") # WikiService: WikiPipeline returned empty or None output for {repo_url}.
                # Wiki 生成 pipeline 未返回任何输出。
                raise HTTPException(status_code=500, detail="Wiki 生成 pipeline 未返回任何输出。")

            # 提取生成的文本。根据 `agents/pipelines/wiki_pipeline.py`，
            # 输出是一个字典，生成的文本位于 `pipeline_output["text_generator"]["results"][0]`。
            generated_wiki_text = None
            if (isinstance(pipeline_output, dict) and
                "text_generator" in pipeline_output and
                isinstance(pipeline_output["text_generator"], dict) and
                "results" in pipeline_output["text_generator"] and
                isinstance(pipeline_output["text_generator"]["results"], list) and
                len(pipeline_output["text_generator"]["results"]) > 0):
                
                raw_result = pipeline_output["text_generator"]["results"][0]
                # 结果可能是字符串或某个对象。确保它是字符串。
                if hasattr(raw_result, 'content'): # 如果是类似 Document 的对象
                    generated_wiki_text = str(raw_result.content)
                elif isinstance(raw_result, str):
                     generated_wiki_text = raw_result
                else: # 如果结构不同或结果不是直接的字符串，则回退
                    generated_wiki_text = str(raw_result)

                if generated_wiki_text:
                    generated_wiki_text = generated_wiki_text.strip()

            if not generated_wiki_text:
                logger.error(f"WikiService: 无法从 WikiPipeline 为仓库 {repo_url} 的输出中提取生成的 wiki 文本。原始输出: {pipeline_output}") # WikiService: Could not extract generated wiki text from WikiPipeline output for {repo_url}. Raw Output: {pipeline_output}
                # 未能从 wiki 生成 pipeline 输出中提取内容。
                raise HTTPException(status_code=500, detail="未能从 wiki 生成 pipeline 输出中提取内容。")

            logger.info(f"WikiService: 成功为仓库 {repo_url} 生成 wiki。输出长度: {len(generated_wiki_text)} 字符。") # WikiService: Successfully generated wiki for {repo_url}. Output length: {len(generated_wiki_text)} characters.
            return generated_wiki_text
            
        except HTTPException: # 如果 pipeline 抛出（不太可能），则明确重新引发 HTTPException
            raise
        except Exception as e:
            logger.exception(f"WikiService: WikiPipeline 为仓库 {repo_url} 执行失败。") # WikiService: WikiPipeline execution failed for {repo_url}.
            # Wiki 生成过程失败
            raise HTTPException(status_code=500, detail=f"Wiki 生成过程失败: {str(e)}")

# 注意：示例用法 (主异步函数) 已从服务文件中移除。
# 它应该是测试套件或示例脚本的一部分，而不是服务模块本身。
# 对于 FastAPI 应用中的实例化，通常会使用依赖注入。
# 示例 (在您的 FastAPI 应用设置中):
# from backend.app.services.github_service import GithubService
# from backend.app.services.wiki_service import WikiService
# github_serv = GithubService() # 假设 GITHUB_API_TOKEN 已在环境中设置
# wiki_serv = WikiService(github_service=github_serv)
# 然后在您的路由处理程序中使用 `wiki_serv`。