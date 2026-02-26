import sys
from blog_graph import build_graph, BlogState
import os

if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else "."
    os.chdir(target_path)
    print(target_path)

    app = build_graph()
    app.invoke(BlogState())