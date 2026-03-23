import os
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from repo_loader import load_readme, load_code_context
import subprocess

SCORE_THRESHOLD = 8
MAX_REWRITES = 2



class BlogState(BaseModel):
    #readme: str = Field(default="")
    #code_context: str = Field(default="")
    blog: str = Field(default="")
    score: int = Field(default=0)
    rewrite_count: int = Field(default=0)
    readme: str = ""
    code_context: str = ""
    existing_blog: str = ""
    commits: str = "" 
    diff: str = "" 




# LLM Setup
def get_llm():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required")

    return ChatOpenAI(
        model="openai/gpt-4o-mini",
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.5,
        max_tokens=800,
    )


# Nodes
# def load_repo(state: BlogState) -> BlogState:
#     state.readme = load_readme()
#     state.code_context = load_code_context()
#     return state

def load_repo(state: BlogState) -> BlogState:
    from repo_loader import load_readme, load_code_context, load_existing_blog,load_git_changes

    state.readme = load_readme()
    state.code_context = load_code_context(max_chars=10000)

    state.existing_blog = load_existing_blog()

    import os
    trigger_sha = os.getenv("TRIGGER_SHA")
    if not trigger_sha:
        trigger_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()

    commits, diff = load_git_changes(trigger_sha)

    state.commits = commits
    state.diff = diff[:8000]  # truncate for LLM

    #Skip
    if not commits.strip():
        print("No new changes detected. Skipping blog generation.")
        exit(0)

    return state


# def generate_blog(state: BlogState) -> BlogState:
#     llm = get_llm()

#     prompt = PromptTemplate.from_template("""
#     You are a senior developer writing a high-quality Medium technical blog.

#     Requirements:
#     - Catchy title
#     - Clear intro
#     - Architecture overview
#     - Key features
#     - Use cases
#     - Conclusion
#     - Friendly developer tone

#     Please Don't create Image Just architecture and highlevel about everything. Also do proper formatting of the article


#     README:
#     {readme}

#     Codebase Summary:
#     {code_context}
#     """)

#     chain = prompt | llm | StrOutputParser()

#     state.blog = chain.invoke({
#         "readme": state.readme,
#         "code_context": state.code_context
#     })

#     print("✅ Blog generated")
#     return state



def generate_blog(state: BlogState) -> BlogState:
    llm = get_llm()

    if state.existing_blog:
        # 🔥 Incremental mode
        prompt = PromptTemplate.from_template("""
        You are a senior developer updating an existing blog.

        STRICT RULES:
        - DO NOT generate full blog
        - DO NOT include title, introduction, architecture, etc.
        - DO NOT repeat any existing content
        - ONLY output NEW CHANGES
        - Output MUST be bullet points ONLY

        Commits:
        {commits}

        Code Changes:
        {diff}

        Task:
        - Identify meaningful changes
        - Summarize in 3-6 bullet points
        - Focus on features, fixes, improvements
        - Ignore formatting or minor edits

        Output Example:
        - Added Kafka streaming support
        - Improved schema validation
        - Fixed GitHub workflow trigger bug

        ONLY return bullet points. NOTHING ELSE.

        """)

        inputs = {
            "commits": state.commits,
            "diff": state.diff
        }

    else:
        # First-time generation
        prompt = PromptTemplate.from_template("""
        You are a senior developer writing a high-quality Medium blog.

        You are a senior developer writing a high-quality Medium technical blog.

        Requirements:
        - Catchy title
        - Clear intro
        - Architecture overview
        - Key features
        - Use cases
        - Conclusion
        - Friendly developer tone

        Please Don't create Image Just architecture and highlevel about everything. Also do proper formatting of the article


        README:
        {readme}

        Codebase Summary:
        {code_context}
        """)

        inputs = {
            "readme": state.readme,
            "code_context": state.code_context
        }

    chain = prompt | llm | StrOutputParser()
    state.blog = chain.invoke(inputs)

    lines = state.blog.strip().split("\n")

    # keep only bullet lines
    clean_lines = [l.strip() for l in lines if l.strip().startswith("-")]

    if not clean_lines:
        print("⚠️ Invalid AI output, fallback used")
        state.blog = "- Minor improvements and fixes"
    else:
        state.blog = "\n".join(clean_lines[:6])  # max 6 bullets

    print("✅ Blog generated")
    return state


def evaluate_blog(state: BlogState) -> BlogState:
    llm = get_llm()

    prompt = f"""
    Rate the quality of the following blog from 1 to 10.
    Only return a single number. Give number based on proper spacing and proper read able content.Also Make sure blog is completed not half way done

    Blog:
    {state.blog}
    """

    response = llm.invoke(prompt).content.strip()

    try:
        state.score = int(response)
    except:
        state.score = 6

    print(f" Blog Quality Score: {state.score}/10")
    return state


def rewrite_blog(state: BlogState) -> BlogState:
    llm = get_llm()

    prompt = f"""
    Improve this blog to increase clarity, engagement, and structure.
    Ensure it is complete and properly formatted.

    Blog:
    {state.blog}
    """       

    state.blog = llm.invoke(prompt).content
    state.rewrite_count += 1

    print(f" Rewrite attempt #{state.rewrite_count}")
    return state


# def save_blog(state: BlogState) -> BlogState:
#     with open("medium_blog.md", "w", encoding="utf-8") as f:
#         f.write(state.blog)

#     print(" medium_blog.md format saved successfully")
#     return state

def save_blog(state: BlogState) -> BlogState:
    import re
    from datetime import datetime

    path = "medium_blog.md"
    date = datetime.now().strftime("%Y-%m-%d")

    new_section = f"\n\n## 🚀 Latest Updates ({date})\n{state.blog}\n"

    if state.existing_blog:
        content = state.existing_blog

        if "## 🚀 Latest Updates" in content:
            # 🔥 Replace old updates section (NOT append)
            content = re.sub(
                r"## 🚀 Latest Updates.*",
                new_section,
                content,
                flags=re.DOTALL
            )
        else:
            # First time adding updates
            content += new_section

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    else:
        # First-time blog creation
        with open(path, "w", encoding="utf-8") as f:
            f.write(state.blog)

    print("✅ Blog updated cleanly (no duplication)")
    return state


#Router
# def quality_router(state: BlogState):
#     if state.score < SCORE_THRESHOLD and state.rewrite_count < MAX_REWRITES:
#         return "rewrite_blog"
#     return "save_blog"


def quality_router(state: BlogState):
    # If incremental mode → NEVER rewrite
    if state.existing_blog:
        return "save_blog"

    # Only rewrite for first time full blog
    if state.score < SCORE_THRESHOLD and state.rewrite_count < MAX_REWRITES:
        return "rewrite_blog"

    return "save_blog"


def build_graph():
    graph = StateGraph(BlogState)

    graph.add_node("load_repo", load_repo)
    graph.add_node("generate_blog", generate_blog)
    graph.add_node("evaluate_blog", evaluate_blog)
    graph.add_node("rewrite_blog", rewrite_blog)
    graph.add_node("save_blog", save_blog)

    graph.add_edge(START, "load_repo")
    graph.add_edge("load_repo", "generate_blog")
    graph.add_edge("generate_blog", "evaluate_blog")

    graph.add_conditional_edges(
        "evaluate_blog",
        quality_router,
        {
            "rewrite_blog": "rewrite_blog",
            "save_blog": "save_blog",
        },
    )

    graph.add_edge("rewrite_blog", "evaluate_blog")
    graph.add_edge("save_blog", END)

    return graph.compile()