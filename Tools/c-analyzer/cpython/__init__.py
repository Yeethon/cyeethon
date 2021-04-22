import os.path

TOOL_ROOT = os.path.normcase(
    os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
)
REPO_ROOT = os.path.dirname(os.path.dirname(TOOL_ROOT))
INCLUDE_DIRS = [os.path.join(REPO_ROOT, name) for name in ["Include"]]
SOURCE_DIRS = [
    os.path.join(REPO_ROOT, name) for name in ["Python", "Parser", "Objects", "Modules"]
]
