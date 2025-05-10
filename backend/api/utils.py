import re
import ast
import os
from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import HtmlFormatter

def extract_python_documentation(content):
    """Extract documentation from Python code."""
    try:
        tree = ast.parse(content)
        documentation = {
            'functions': [],
            'classes': []
        }
        
        for node in ast.walk(tree):
            # Extract function documentation
            if isinstance(node, ast.FunctionDef):
                func_doc = {
                    'name': node.name,
                    'description': ast.get_docstring(node) or '',
                    'params': [],
                    'returns': ''
                }
                
                # Extract parameters
                for arg in node.args.args:
                    func_doc['params'].append({
                        'name': arg.arg,
                        'description': ''
                    })
                
                documentation['functions'].append(func_doc)
            
            # Extract class documentation
            elif isinstance(node, ast.ClassDef):
                class_doc = {
                    'name': node.name,
                    'description': ast.get_docstring(node) or '',
                    'methods': []
                }
                
                # Extract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_doc = {
                            'name': item.name,
                            'description': ast.get_docstring(item) or ''
                        }
                        class_doc['methods'].append(method_doc)
                
                documentation['classes'].append(class_doc)
        
        return documentation
    except SyntaxError:
        return {'error': 'Could not parse Python code'}

def extract_javascript_documentation(content):
    """Extract documentation from JavaScript code."""
    # Simple regex-based extraction for JS
    documentation = {
        'functions': [],
        'classes': []
    }
    
    # Match function declarations with JSDoc comments
    function_pattern = r'/\*\*([\s\S]*?)\*/\s*function\s+(\w+)\s*\((.*?)\)'
    for match in re.finditer(function_pattern, content):
        jsdoc, name, params = match.groups()
        
        func_doc = {
            'name': name,
            'description': jsdoc.strip(),
            'params': [],
            'returns': ''
        }
        
        # Extract parameters
        param_pattern = r'@param\s+{([^}]+)}\s+(\w+)\s+(.*)'
        for param_match in re.finditer(param_pattern, jsdoc):
            param_type, param_name, param_desc = param_match.groups()
            func_doc['params'].append({
                'name': param_name,
                'description': param_desc.strip()
            })
        
        # Extract return value
        return_pattern = r'@returns?\s+{([^}]+)}\s+(.*)'
        return_match = re.search(return_pattern, jsdoc)
        if return_match:
            return_type, return_desc = return_match.groups()
            func_doc['returns'] = return_desc.strip()
        
        documentation['functions'].append(func_doc)
    
    # Match class declarations
    class_pattern = r'/\*\*([\s\S]*?)\*/\s*class\s+(\w+)'
    for match in re.finditer(class_pattern, content):
        jsdoc, name = match.groups()
        
        class_doc = {
            'name': name,
            'description': jsdoc.strip(),
            'methods': []
        }
        
        documentation['classes'].append(class_doc)
    
    return documentation

def extract_documentation(content, file_path):
    """Extract documentation based on file type."""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.py':
        return extract_python_documentation(content)
    elif file_ext in ['.js', '.jsx']:
        return extract_javascript_documentation(content)
    else:
        # Default minimal documentation
        return {
            'functions': [],
            'classes': []
        }

def highlight_code(content, file_path):
    """Highlight code using Pygments."""
    try:
        lexer = get_lexer_for_filename(file_path)
        formatter = HtmlFormatter(linenos=True, cssclass="source")
        return highlight(content, lexer, formatter)
    except:
        # If we can't determine the lexer, return plain text
        return content
