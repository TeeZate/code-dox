import re
from typing import Dict, List, Optional
import ast
import hashlib
from pathlib import Path
import json
from api.models import CodeFile, Documentation

class EnhancedDocumentationGenerator:
    """
    Generates comprehensive explanations and summaries of code files.
    Goes beyond structural documentation to explain implementation purpose.
    """
    
    def __init__(self):
        self.summary_cache = {}
    
    def generate_file_summary(self, content: str, file_type: str, file_path: str) -> Dict:
        """
        Generate comprehensive documentation for a code file including:
        - Implementation purpose
        - Key functionality
        - Architectural role
        - Summary of major components
        """
        # Create content hash for caching
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check cache first
        if content_hash in self.summary_cache:
            return self.summary_cache[content_hash]
            
        # Get basic structural documentation
        doc = self._get_structural_documentation(content, file_type)
        
        # Enhanced analysis
        enhanced_doc = {
            'structural': doc,
            'summary': self._generate_summary(content, file_type, file_path),
            'purpose': self._analyze_implementation_purpose(content, file_type, file_path),
            'key_functionality': self._identify_key_functionality(doc, file_type),
            'integration_points': self._find_integration_points(content, file_type),
            'dependencies': self._analyze_dependencies(content, file_type)
        }
        
        # Cache the result
        self.summary_cache[content_hash] = enhanced_doc
        
        return enhanced_doc
    
    def _get_structural_documentation(self, content: str, file_type: str) -> Dict:
        """Get the basic structural documentation (existing functionality)"""
        # Reuse existing extraction methods from original code
        if file_type in ['py', 'python']:
            return self._extract_python_documentation(content)
        elif file_type in ['js', 'jsx', 'ts', 'tsx']:
            return self._extract_javascript_documentation(content)
        # Add other language handlers as needed
        else:
            return {'description': '', 'entities': []}
    
    def _generate_summary(self, content: str, file_type: str, file_path: str) -> str:
        """
        Generate a human-readable summary of the file's purpose and content.
        This can be enhanced with AI/ML models for better analysis.
        """
        filename = Path(file_path).name
        
        # Language-specific summary generation
        if file_type in ['py', 'python']:
            return self._generate_python_summary(content, filename)
        elif file_type in ['js', 'jsx', 'ts', 'tsx']:
            return self._generate_javascript_summary(content, filename)
        else:
            return self._generate_generic_summary(content, filename)
        
    def _generate_generic_summary(self, content: str, filename: str) -> str:
        """
        Fallback summary generator for unsupported file types.
        """
        return f"{filename} appears to be a source file, but no specialized summarization logic exists for its type."

    
    def _generate_python_summary(self, content: str, filename: str) -> str:
        """Generate summary for Python files"""
        try:
            # Parse AST for deeper understanding
            tree = ast.parse(content)
            
            # Count different elements
            num_classes = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
            num_functions = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
            num_imports = len([node for node in ast.walk(tree) if isinstance(node, ast.Import) or 
                             isinstance(node, ast.ImportFrom)])
            
            # Get main docstring if exists
            docstring = ast.get_docstring(tree) or ""
            
            summary = f"The Python file '{filename}' contains:"
            summary += f"\n- {num_classes} class{'es' if num_classes != 1 else ''}"
            summary += f"\n- {num_functions} function{'s' if num_functions != 1 else ''}"
            summary += f"\n- {num_imports} import statement{'s' if num_imports != 1 else ''}"
            
            if docstring:
                summary += f"\n\nFile description:\n{docstring}"
            
            # Identify if it's a module, script, or mixed
            if num_classes > 0 and num_functions > 3 and '__main__' not in content:
                summary += "\n\nThis appears to be a module providing reusable components."
            elif '__main__' in content and 'if __name__ == "__main__":' in content:
                summary += "\n\nThis is an executable script with main functionality."
            else:
                summary += "\n\nThis file contains implementation code for specific functionality."
                
            return summary
            
        except Exception as e:
            return f"Summary for Python file '{filename}': Unable to parse file structure. {str(e)}"
    
    def _generate_javascript_summary(self, content: str, filename: str) -> str:
        """Generate summary for JavaScript/TypeScript files"""
        # Count components, functions, imports
        component_count = len(re.findall(r'class\s+\w+\s+extends\s+(?:React\.)?Component', content))
        function_count = len(re.findall(r'function\s+\w+\s*\(|const\s+\w+\s*=\s*\(?.*\)?\s*=>', content))
        import_count = len(re.findall(r'import\s+.*?from\s+[\'"][^\'"]+[\'"]', content))
        
        summary = f"The JavaScript/TypeScript file '{filename}' contains:"
        summary += f"\n- {component_count} React component{'s' if component_count != 1 else ''}"
        summary += f"\n- {function_count} function{'s' if function_count != 1 else ''}"
        summary += f"\n- {import_count} import statement{'s' if import_count != 1 else ''}"
        
        # Detect if it's a React component file
        if component_count > 0 or 'React' in content:
            summary += "\n\nThis appears to be a React component file."
        elif import_count > 5 and function_count > 3:
            summary += "\n\nThis is likely a module exporting multiple functions."
        else:
            summary += "\n\nThis file contains implementation code for specific functionality."
            
        return summary
    
    def _analyze_implementation_purpose(self, content: str, file_type: str, file_path: str) -> str:
        """
        Analyze what the file implements and its role in the system.
        This can be enhanced with more sophisticated analysis.
        """
        filename = Path(file_path).name
        
        # Language-specific purpose analysis
        if file_type in ['py', 'python']:
            return self._analyze_python_purpose(content, filename)
        elif file_type in ['js', 'jsx', 'ts', 'tsx']:
            return self._analyze_javascript_purpose(content, filename)
        else:
            return self._analyze_generic_purpose(content, filename)
        
    def _analyze_generic_purpose(self, content: str, filename: str) -> str:
        """
        Basic fallback analysis for files that are not Python or JavaScript.
        """
        return f"{filename} likely serves a support or configuration role in the project. Detailed analysis is unavailable for this file type."

    
    def _analyze_python_purpose(self, content: str, filename: str) -> str:
        """Analyze implementation purpose for Python files"""
        purpose = ""
        
        # Check for common patterns
        if 'def test_' in content or 'import unittest' in content:
            purpose = f"The file '{filename}' contains test cases for verifying other components."
        elif 'import flask' in content or 'from flask import' in content:
            purpose = f"The file '{filename}' implements Flask web application routes and views."
        elif 'import django' in content or 'from django.' in content:
            purpose = f"The file '{filename}' contains Django framework components (models, views, etc.)."
        elif 'def main(' in content or 'if __name__ == "__main__":' in content:
            purpose = f"The file '{filename}' provides executable functionality as a script."
        else:
            purpose = f"The file '{filename}' implements core business logic and functionality."
            
        return purpose
    
    def _identify_key_functionality(self, structural_doc: Dict, file_type: str) -> List[str]:
        """
        Identify and describe the key functionality implemented in the file.
        """
        key_functions = []
        
        # Analyze classes and their purposes
        for entity in structural_doc.get('entities', []):
            if entity['type'] == 'class':
                class_desc = f"Class {entity['name']}: "
                if entity.get('description'):
                    class_desc += entity['description'].split('\n')[0]
                else:
                    class_desc += "Provides object-oriented functionality"
                
                # Add methods summary
                methods = entity.get('methods', [])
                if methods:
                    class_desc += f" with {len(methods)} key method{'s' if len(methods) != 1 else ''}"
                
                key_functions.append(class_desc)
            
            elif entity['type'] == 'function':
                func_desc = f"Function {entity['name']}: "
                if entity.get('description'):
                    func_desc += entity['description'].split('\n')[0]
                else:
                    func_desc += "Performs specific operation"
                
                key_functions.append(func_desc)
        
        return key_functions
    
    def _find_integration_points(self, content: str, file_type: str) -> List[str]:
        """
        Identify how this file integrates with other parts of the system.
        """
        integration_points = []
        
        # Find external API calls
        if file_type in ['py', 'python']:
            if 'requests.get(' in content or 'requests.post(' in content:
                integration_points.append("Makes HTTP requests to external APIs")
            if 'import sqlalchemy' in content or 'import psycopg2' in content:
                integration_points.append("Interacts with databases")
        
        # Find event listeners in JS
        elif file_type in ['js', 'jsx', 'ts', 'tsx']:
            if '.addEventListener(' in content or '.on(' in content:
                integration_points.append("Listens to browser/DOM events")
            if 'fetch(' in content or 'axios.' in content:
                integration_points.append("Makes HTTP requests to APIs")
        
        return integration_points
    
    def _analyze_javascript_purpose(self, code, filepath):
        """
        Analyzes the purpose of a JavaScript file.
        :param code: The JavaScript code as a string.
        :param filepath: The path or name of the JS file.
        :return: A string describing the purpose of the file.
        """
        if "React" in code or "useState" in code or ".jsx" in filepath:
            return "React component"
        elif "function" in code or "=>" in code:
            return "JavaScript utility or module"
        else:
            return "Unknown JavaScript file"
        
    def extract_documentation(self, content, file_type):
        """Extract documentation from file content based on file type."""
        doc = {
            'description': '',
            'entities': [],
            'imports': [],
            'dependencies': []
        }
        
        # Extract documentation based on file type
        if file_type in ['py', 'python']:
            doc = self._extract_python_documentation(content)
        elif file_type in ['js', 'jsx', 'ts', 'tsx']:
            doc = self._extract_javascript_documentation(content)
        elif file_type in ['java']:
            doc = self._extract_java_documentation(content)
        elif file_type in ['c', 'cpp', 'h', 'hpp']:
            doc = self._extract_c_documentation(content)
        elif file_type in ['html', 'htm']:
            doc = self._extract_html_documentation(content)
        elif file_type in ['css', 'scss', 'sass']:
            doc = self._extract_css_documentation(content)
        
        # Extract general description if not already set
        if not doc['description']:
            # Look for file-level comments at the top of the file
            doc['description'] = self._extract_file_description(content, file_type)
        
        return doc

    def _extract_python_documentation(self, content):
        """Extract documentation from Python code."""
        import re
        
        doc = {
            'description': '',
            'entities': [],
            'imports': [],
            'dependencies': []
        }
        
        # Extract imports
        import_pattern = r'^import\s+(\w+)|^from\s+(\w+(?:\.\w+)*)\s+import'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            module = match.group(1) or match.group(2)
            if module and module not in doc['imports']:
                doc['imports'].append(module)
                doc['dependencies'].append(module)
        
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\(([^)]*)\))?:'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            parent_classes = match.group(2)
            
            # Find class docstring
            class_start = match.end()
            docstring = self._extract_docstring(content[class_start:])
            
            doc['entities'].append({
                'type': 'class',
                'name': class_name,
                'inheritance': parent_classes or '',
                'description': docstring,
                'methods': []
            })
        
        # Extract functions
        func_pattern = r'def\s+(\w+)\s*\(([^)]*)\):'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            params = match.group(2)
            
            # Find function docstring
            func_start = match.end()
            docstring = self._extract_docstring(content[func_start:])
            
            # Determine if this is a method of a class
            is_method = False
            indentation = self._get_indentation(content, match.start())
            if indentation > 0:
                is_method = True
                
                # Find which class this method belongs to
                for entity in doc['entities']:
                    if entity['type'] == 'class':
                        # Check if this method is part of this class
                        class_methods = entity.get('methods', [])
                        class_methods.append({
                            'name': func_name,
                            'params': params,
                            'description': docstring
                        })
                        entity['methods'] = class_methods
            
            if not is_method:
                doc['entities'].append({
                    'type': 'function',
                    'name': func_name,
                    'params': params,
                    'description': docstring
                })
        
        # Extract module docstring (if any)
        doc['description'] = self._extract_docstring(content)
        
        return doc

    def _extract_javascript_documentation(self, content):
        """Extract documentation from JavaScript/TypeScript code."""
        import re
        
        doc = {
            'description': '',
            'entities': [],
            'imports': [],
            'dependencies': []
        }
        
        # Extract imports
        import_pattern = r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\)'
        for match in re.finditer(import_pattern, content):
            module = match.group(1) or match.group(2)
            if module and module not in doc['imports']:
                doc['imports'].append(module)
                doc['dependencies'].append(module)
        
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            parent_class = match.group(2)
            
            # Find JSDoc comment before class
            jsdoc = self._extract_jsdoc(content, match.start())
            
            doc['entities'].append({
                'type': 'class',
                'name': class_name,
                'inheritance': parent_class or '',
                'description': jsdoc,
                'methods': []
            })
        
        # Extract functions
        func_patterns = [
            r'function\s+(\w+)\s*\(([^)]*)\)',  # function declaration
            r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'  # arrow function
        ]
        
        for pattern in func_patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                params = match.group(2) if len(match.groups()) > 1 else ''
                
                # Find JSDoc comment before function
                jsdoc = self._extract_jsdoc(content, match.start())
                
                doc['entities'].append({
                    'type': 'function',
                    'name': func_name,
                    'params': params,
                    'description': jsdoc
                })
        
        # Extract React components
        component_pattern = r'(?:export\s+)?(?:const|function)\s+(\w+)(?:\s*=\s*(?:React\.)?memo\()?'
        for match in re.finditer(component_pattern, content):
            component_name = match.group(1)
            
            # Check if it's likely a React component (starts with uppercase)
            if component_name and component_name[0].isupper():
                # Find JSDoc comment before component
                jsdoc = self._extract_jsdoc(content, match.start())
                
                # Check if this component is already added
                existing = False
                for entity in doc['entities']:
                    if entity['name'] == component_name:
                        existing = True
                        break
                
                if not existing:
                    doc['entities'].append({
                        'type': 'component',
                        'name': component_name,
                        'description': jsdoc,
                        'props': self._extract_props_from_jsdoc(jsdoc)
                    })
        
        return doc

    def _extract_docstring(self, content):
        """Extract docstring from Python code."""
        import re
        
        # Look for triple-quoted strings
        docstring_pattern = r'^\s*(?:\'\'\'|""")(.+?)(?:\'\'\'|""")(?:\n|$)'
        match = re.search(docstring_pattern, content, re.DOTALL | re.MULTILINE)
        
        if match:
            # Clean up the docstring
            docstring = match.group(1).strip()
            # Remove common indentation
            lines = docstring.split('\n')
            if len(lines) > 1:
                # Find minimum indentation
                min_indent = min(len(line) - len(line.lstrip()) for line in lines[1:] if line.strip())
                # Remove that indentation from all lines
                docstring = lines[0] + '\n' + '\n'.join(line[min_indent:] if len(line) > min_indent else line for line in lines[1:])
            return docstring
        
        return ''

    def _extract_jsdoc(self, content, position):
        """Extract JSDoc comment before the given position."""
        import re
        
        # Look for JSDoc comments
        jsdoc_pattern = r'/\*\*(.*?)\*/'
        
        # Get the content before the position
        before_content = content[:position]
        
        # Find the last JSDoc comment
        matches = list(re.finditer(jsdoc_pattern, before_content, re.DOTALL))
        if matches:
            last_match = matches[-1]
            jsdoc = last_match.group(1).strip()
            
            # Clean up the JSDoc
            lines = jsdoc.split('\n')
            cleaned_lines = []
            for line in lines:
                # Remove leading asterisks and spaces
                line = re.sub(r'^\s*\*\s?', '', line)
                cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
        
        return ''

    def _extract_props_from_jsdoc(self, jsdoc):
        """Extract props information from JSDoc comment."""
        import re
        
        props = []
        prop_pattern = r'@param\s+{([^}]+)}\s+(\w+)(?:\s+-\s+(.+))?'
        
        for match in re.finditer(prop_pattern, jsdoc):
            prop_type = match.group(1)
            prop_name = match.group(2)
            prop_desc = match.group(3) or ''
            
            props.append({
                'name': prop_name,
                'type': prop_type,
                'description': prop_desc.strip()
            })
        
        return props

    def _extract_file_description(self, content, file_type):
        """Extract file-level description based on file type."""
        import re
        
        # Look for file header comments
        if file_type in ['py', 'python']:
            # Python file header
            header_pattern = r'^"""(.+?)"""'
            match = re.search(header_pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif file_type in ['js', 'jsx', 'ts', 'tsx']:
            # JavaScript/TypeScript file header
            header_pattern = r'^/\*\*(.+?)\*/'
            match = re.search(header_pattern, content, re.DOTALL)
            if match:
                # Clean up the comment
                comment = match.group(1).strip()
                lines = comment.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Remove leading asterisks and spaces
                    line = re.sub(r'^\s*\*\s?', '', line)
                    cleaned_lines.append(line)
                return '\n'.join(cleaned_lines)
        
        # If no specific header found, try to extract the first comment block
        comment_patterns = [
            r'/\*(.+?)\*/',  # C-style comment
            r'<!--(.+?)-->',  # HTML comment
            r'#\s*(.+?)(?:\n\s*#\s*(.+?))*'  # Hash comments (Python, shell)
        ]
        
        for pattern in comment_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                comment = match.group(1).strip()
                return comment
        
        return ''

    def _get_indentation(self, content, position):
        """Get the indentation level at the given position."""
        # Find the start of the line
        line_start = content.rfind('\n', 0, position) + 1
        
        # Get the line
        line = content[line_start:position]
        
        # Count leading spaces
        return len(line) - len(line.lstrip())

    def _extract_java_documentation(self, content):
        """Extract documentation from Java code."""
        # Similar implementation as Python but for Java syntax
        return {'description': '', 'entities': [], 'imports': [], 'dependencies': []}

    def _extract_c_documentation(self, content):
        """Extract documentation from C/C++ code."""
        # Implementation for C/C++
        return {'description': '', 'entities': [], 'imports': [], 'dependencies': []}

    def _extract_html_documentation(self, content):
        """Extract documentation from HTML code."""
        # Implementation for HTML
        return {'description': '', 'entities': [], 'imports': [], 'dependencies': []}

    def _extract_css_documentation(self, content):
        """Extract documentation from CSS code."""
        # Implementation for CSS
        return {'description': '', 'entities': [], 'imports': [], 'dependencies': []}
    
    def _analyze_dependencies(self, content: str, file_type: str) -> Dict:
        """
        Analyze and categorize dependencies.
        """
        dependencies = {
            'internal': [],
            'external': [],
            'framework': []
        }
        
        # Python dependency analysis
        if file_type in ['py', 'python']:
            # Framework detection
            frameworks = ['django', 'flask', 'fastapi', 'tornado']
            for framework in frameworks:
                if f'import {framework}' in content or f'from {framework}' in content:
                    dependencies['framework'].append(framework)
            
            # External package detection
            if 'import requests' in content:
                dependencies['external'].append('requests')
            if 'import numpy' in content:
                dependencies['external'].append('numpy')
        
        return dependencies
