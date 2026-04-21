import ast
import os

# Added 'dev' and 'archive' to ignore list to prevent bloat
IGNORE_DIRS = {'.git', '__pycache__', 'venv', '.venv', 'data', 'models', '.playwright_session', 'dev', 'archive'}

def format_function(node, indent=0):
    """Helper to format a function signature, return type, and brief docstring."""
    args = [arg.arg for arg in node.args.args]
    arg_str = ", ".join(args)
    
    # Safely extract return type if present (requires Python 3.9+)
    ret = ""
    if getattr(node, 'returns', None):
        try:
            ret = f" -> {ast.unparse(node.returns)}"
        except AttributeError:
            pass 

    # Extract just the first line of the docstring to save tokens
    doc = ast.get_docstring(node)
    doc_str = f" # {doc.splitlines()[0].strip()}" if doc else ""
    
    ind = " " * indent
    return f"{ind}def {node.name}({arg_str}){ret}:{doc_str}"

def parse_file(filepath):
    """Parses a Python file and returns its AST skeleton."""
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return []

    skeleton = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            doc_str = f" # {doc.splitlines()[0].strip()}" if doc else ""
            skeleton.append(f"class {node.name}:{doc_str}")
            
            for sub_node in node.body:
                if isinstance(sub_node, ast.FunctionDef):
                    skeleton.append(format_function(sub_node, indent=4))
                    
        elif isinstance(node, ast.FunctionDef):
            skeleton.append(format_function(node, indent=0))
            
    return skeleton

def generate_map(root_dir):
    """Walks the directory and builds the repo map."""
    repo_map = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)
                skeleton = parse_file(filepath)
                if skeleton:
                    rel_path = os.path.relpath(filepath, root_dir)
                    repo_map.append(f"\n# {rel_path}")
                    repo_map.extend(skeleton)
                    
    return "\n".join(repo_map)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    ast_map = generate_map(root_dir=project_root)
    
    # --- THE SQL BYPASS ---
    # Read the raw SQL schema directly
    schema_path = os.path.join(project_root, "core", "schema.sql")
    schema_content = ""
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_content = f.read()
    
    # Ultra-lean, token-optimized system anchor
    preamble = """# AST REPO MAP
SYSTEM INSTRUCTIONS:
1. LOGIC OMITTED: Functions are NOT empty. Implementations are abstracted for context efficiency.
2. READ/WRITE PROTOCOL: To modify a function, you MUST ask the user to provide the specific file path first. Do NOT hallucinate modifications without the source file.
3. ARCHITECTURAL GROUNDING: Refer to `research-notes.md` for refactor history and `pitfalls.md` for known technical hurdles.
4. PRECISION: Use exact class, function, and file names from this map.

---

"""
    
    output_path = os.path.join(project_root, "GEMINI.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(preamble)
        
        # Inject the Database Schema into the markdown first
        if schema_content:
            f.write("## DATABASE SCHEMA (`core/schema.sql`)\n")
            f.write("```sql\n")
            f.write(schema_content)
            f.write("\n```\n\n")
        
        # Inject the AST Map
        f.write("## PYTHON ARCHITECTURE\n")
        f.write("```python\n")
        f.write(ast_map)
        f.write("\n```\n")
        
    print(f"Successfully generated token-optimized AST map at: {output_path}")
