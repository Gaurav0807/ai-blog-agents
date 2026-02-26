from blog_graph import build_graph, BlogState

if __name__ == "__main__":
    app = build_graph()
    app.invoke(BlogState())