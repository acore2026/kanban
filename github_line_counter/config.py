CATEGORIES = ("arch", "acn", "up", "compute")

SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".go", ".rs", ".py", ".pyi", ".java", ".kt", ".kts", ".scala",
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".rb", ".php", ".swift", ".m", ".mm", ".cs",
    ".sh", ".bash", ".zsh", ".fish",
    ".lua", ".pl", ".pm", ".r", ".dart", ".jl",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".vue", ".svelte",
    ".sql", ".proto", ".thrift",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".dockerfile",
}

SOURCE_FILENAMES = {
    "dockerfile", "makefile", "justfile", "cmakelists.txt",
    "meson.build", "build.gradle", "build.gradle.kts",
}

SKIP_DIR_NAMES = {
    ".git", ".hg", ".svn", ".idea", ".vscode",
    "node_modules", "vendor", "dist", "build", "target", "out",
    "__pycache__", ".next", ".nuxt", ".venv", "venv",
}

SKIP_SUFFIXES = {
    ".min.js", ".min.css",
}

