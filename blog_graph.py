import os
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from repo_loader import load_readme, load_code_context


SCORE_THRESHOLD = 8
MAX_REWRITES = 2


class BlogState(BaseModel):
    readme: str = Field(default="")
    code_context: str = Field(default="")
    blog: str = Field(default="")
    score: int = Field(default=0)
    rewrite_count: int = Field(default=0)



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
def load_repo(state: BlogState) -> BlogState:
    state.readme = load_readme()
    state.code_context = load_code_context()
    return state


def generate_blog(state: BlogState) -> BlogState:
    llm = get_llm()

    prompt = PromptTemplate.from_template("""
    You are a senior developer writing a high-quality Medium technical blog.

    Convert this GitHub repository into a structured blog.

    Required Sections:
    - Catchy Title
    - Introduction
    - Problem Statement
    - Architecture Overview
    - Key Components
    - How It Works
    - Real-world Use Cases
    - How to Run Locally
    - Conclusion

    Rules:
    - Do NOT generate images
    - Use proper formatting
    - Ensure the article is fully complete
    - Maintain a friendly developer tone

    README:
    {readme}

    Codebase Summary:
    {code_context}
    """)

    chain = prompt | llm | StrOutputParser()

    state.blog = chain.invoke({
        "readme": state.readme,
        "code_context": state.code_context
    })

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


def save_blog(state: BlogState) -> BlogState:
    with open("medium_blog.md", "w", encoding="utf-8") as f:
        f.write(state.blog)

    print(" medium_blog.md format saved successfully")
    return state



#Router
def quality_router(state: BlogState):
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