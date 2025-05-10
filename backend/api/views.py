import os
import json
from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.core.management import call_command
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from .models import CodeRepository, CodeFile, Documentation
from .serializers import (
    CodeRepositorySerializer,
    CodeFileSerializer,
    DocumentationSerializer,
    FileTreeSerializer,
    UserRegistrationSerializer
)
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# Authentication Views

@ensure_csrf_cookie
def csrf_token_view(request):
    return JsonResponse({'csrfToken': request.META.get('CSRF_COOKIE')})

class RegisterView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({'message': 'Login successful'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

class UserView(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            user_data = {
                'username': request.user.username,
                'email': request.user.email
            }
            return Response(user_data, status=status.HTTP_200_OK)
        return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

# Code Repository Views
from rest_framework.decorators import action

class CodeRepositoryViewSet(viewsets.ModelViewSet):
    queryset = CodeRepository.objects.all()
    serializer_class = CodeRepositorySerializer
    
    @action(detail=False, methods=['post'], url_path='add')
    def add_repository(self, request):
        """Add a new repository and import its files."""
        name = request.data.get('name')
        path = request.data.get('path')
        
        if not name or not path:
            return Response(
                {"error": "Both name and path are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate path exists
        if not os.path.exists(path):
            return Response(
                {"error": f"Path does not exist: {path}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create repository
        try:
            # Check if repository already exists
            existing = CodeRepository.objects.filter(name=name).first()
            if existing:
                return Response(
                    {"error": f"Repository with name '{name}' already exists"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create new repository
            repository = CodeRepository.objects.create(name=name, path=path)
            
            # Import repository files using the management command
            try:
                # Call the management command to import files
                call_command('import_repository', name, path)
                
                return Response(
                    {"success": f"Repository '{name}' added successfully", "id": repository.id}, 
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                repository.delete()  # Clean up if import fails
                return Response(
                    {"error": f"Failed to import repository files: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {"error": f"Failed to create repository: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def file_tree(self, request, pk=None):
        """
        Return the file tree structure for a repository by reading from the filesystem.
        """
        try:
            repository = self.get_object()
            repo_path = repository.path
            
            if not os.path.exists(repo_path):
                return Response(
                    {"error": f"Repository path does not exist: {repo_path}"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Function to build tree recursively
            def build_tree(path, rel_path=""):
                result = {}
                
                # Skip hidden directories and common directories to ignore
                skip_dirs = ['.git', 'node_modules', 'venv', '__pycache__']
                
                try:
                    for item in os.listdir(path):
                        # Skip hidden files and directories
                        if item.startswith('.') or item in skip_dirs:
                            continue
                        
                        item_path = os.path.join(path, item)
                        item_rel_path = os.path.join(rel_path, item).replace('\\', '/')
                        
                        if os.path.isdir(item_path):
                            # It's a directory
                            subtree = build_tree(item_path, item_rel_path)
                            if subtree:  # Only add non-empty directories
                                result[item] = subtree
                        else:
                            # Skip binary files and large files
                            try:
                                # Skip files larger than 1MB
                                if os.path.getsize(item_path) > 1024 * 1024:
                                    continue
                                    
                                # Get file type from extension
                                _, ext = os.path.splitext(item)
                                file_type = ext.lstrip('.').lower() if ext else 'txt'
                                
                                # Find the file in the database to get its ID
                                db_file = CodeFile.objects.filter(
                                    repository=repository,
                                    path=item_rel_path
                                ).first()
                                
                                file_id = db_file.id if db_file else None
                                
                                result[item] = {
                                    'id': file_id,
                                    'name': item,
                                    'path': item_rel_path,
                                    'type': file_type,
                                    'is_file': True
                                }
                            except Exception:
                                # Skip files that can't be processed
                                continue
                                
                except PermissionError:
                    # Skip directories we don't have permission to read
                    pass
                
                return result
            
            tree = build_tree(repo_path)
            return Response(tree)
            
        except CodeRepository.DoesNotExist:
            return Response(
                {"error": "Repository not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to get file tree: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=True, methods=['delete'])
    def delete_repository(self, request, pk=None):
        """Delete a repository and all its associated files."""
        try:
            repository = self.get_object()
            name = repository.name
            
            # Delete all files associated with this repository
            CodeFile.objects.filter(repository=repository).delete()
            
            # Delete the repository itself
            repository.delete()
            
            return Response(
                {"success": f"Repository '{name}' and all its files deleted successfully"}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete repository: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_documentation(self, request, pk=None):
        """
        Generate documentation for all files in the repository.
        This will analyze code files and create or update documentation records.
        """
        try:
            repository = self.get_object()
            
            # Get all code files for this repository
            files = CodeFile.objects.filter(repository=repository)
            
            if not files.exists():
                return Response(
                    {"error": "No files found in repository"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track progress
            total_files = files.count()
            processed_files = 0
            documented_files = 0
            skipped_files = 0
            
            for file in files:
                processed_files += 1
                
                # Skip files without content or binary files
                if not file.content or file.is_binary:
                    skipped_files += 1
                    continue
                
                # Get file extension to determine language
                _, ext = os.path.splitext(file.path)
                file_type = ext.lstrip('.').lower() if ext else ''
                
                # Generate documentation based on file type
                doc_content = self.extract_documentation(file.content, file_type)
                
                # Create or update documentation record
                doc, created = Documentation.objects.update_or_create(
                    file=file,
                    defaults={'content': json.dumps(doc_content)}
                )
                
                documented_files += 1
                
                # Update progress every 10 files
                if processed_files % 10 == 0:
                    print(f"Processed {processed_files}/{total_files} files")
            
            return Response({
                "success": f"Documentation generated for {documented_files} files",
                "total_files": total_files,
                "documented_files": documented_files,
                "skipped_files": skipped_files
            })
            
        except CodeRepository.DoesNotExist:
            return Response(
                {"error": "Repository not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to generate documentation: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
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
    @action(detail=True, methods=['get'])
    def documentation(self, request, pk=None):
        """Get all files with documentation for this repository."""
        try:
            repository = self.get_object()
            
            # Get all files with documentation
            files_with_docs = CodeFile.objects.filter(
                repository=repository,
                documentation__isnull=False
            ).select_related('documentation')
            
            result = []
            for file in files_with_docs:
                try:
                    doc_content = json.loads(file.documentation.content)
                    has_content = bool(doc_content.get('description') or doc_content.get('entities'))
                except:
                    has_content = False
                    
                if has_content:
                    result.append({
                        'id': file.id,
                        'name': file.name,
                        'path': file.path,
                        'type': file.file_type
                    })
            
            return Response(result)
        except Exception as e:
            return Response(
                {"error": f"Failed to get documentation: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='documentation')
    def get_documentation(self, request, pk=None):
        """Get documentation for a specific file."""
        try:
            file = self.get_object()
            
            try:
                doc = Documentation.objects.get(file=file)
                doc_content = json.loads(doc.content)
                return Response(doc_content)
            except Documentation.DoesNotExist:
                return Response({"error": "No documentation found for this file"}, status=404)
        except Exception as e:
            return Response(
                {"error": f"Failed to get documentation: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class CodeFileViewSet(viewsets.ModelViewSet):
    queryset = CodeFile.objects.all()
    serializer_class = CodeFileSerializer

    @action(detail=False, methods=['get'])
    def by_path(self, request):
        path = request.query_params.get('path')
        repository_id = request.query_params.get('repository_id')

        if not path or not repository_id:
            return Response(
                {"error": "Path and repository_id parameters are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            file = CodeFile.objects.get(path=path, repository_id=repository_id)
            serializer = self.get_serializer(file)
            return Response(serializer.data)
        except CodeFile.DoesNotExist:
            return Response({"error": "File not found"}, status=404)

    @action(detail=True, methods=['get'], url_path='content')
    def content(self, request, pk=None):
        try:
            file = self.get_object()
            
            # If content exists in the database and is not empty, return it
            if file.content and len(file.content.strip()) > 0:
                print(f"Returning content from database for {file.path}")
                return Response({"content": file.content})
            
            # Otherwise, try to read from the filesystem
            print(f"Content not found in database for {file.path}, trying filesystem")
            repository = file.repository
            full_path = os.path.join(repository.path, file.path)
            
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    # Try different encodings
                    encodings = ['utf-8', 'latin-1', 'cp1252']
                    content = None
                    
                    for encoding in encodings:
                        try:
                            with open(full_path, 'r', encoding=encoding) as f:
                                content = f.read()
                            print(f"Successfully read {file.path} with {encoding} encoding")
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if content is None:
                        # If all encodings fail, it might be a binary file
                        print(f"Could not read {file.path} with any encoding, might be binary")
                        return Response({
                            "content": f"// This appears to be a binary file: {file.path}\n// Binary files cannot be displayed in the text viewer."
                        })
                    
                    # Update the database with the content for future requests
                    file.content = content
                    file.save()
                    
                    return Response({"content": content})
                except Exception as e:
                    print(f"Error reading file {file.path}: {str(e)}")
                    return Response({"error": f"Error reading file: {str(e)}"}, status=500)
            else:
                print(f"File not found on disk: {full_path}")
                return Response({"error": f"File not found on disk: {file.path}"}, status=404)
        except Exception as e:
            print(f"Error in content action: {str(e)}")
            return Response({"error": str(e)}, status=500)
        
    @action(detail=True, methods=['get'], url_path='documentation')
    def documentation(self, request, pk=None):
        """Get documentation for a specific file."""
        try:
            # Check if pk is valid
            if pk is None or pk == 'null':
                return Response({"error": "Invalid file ID"}, status=status.HTTP_400_BAD_REQUEST)
                
            file = self.get_object()
            
            try:
                doc = Documentation.objects.get(file=file)
                doc_content = json.loads(doc.content)
                return Response(doc_content)
            except Documentation.DoesNotExist:
                # Return empty documentation instead of 404
                return Response({
                    "description": "",
                    "entities": [],
                    "imports": [],
                    "dependencies": []
                })
            except json.JSONDecodeError:
                # Handle case where documentation content is not valid JSON
                return Response({"error": "Documentation format is invalid"}, status=500)
        except Exception as e:
            print(f"Error getting documentation: {str(e)}")
            return Response(
                {"error": f"Failed to get documentation: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class DocumentationViewSet(viewsets.ModelViewSet):
    queryset = Documentation.objects.all()
    serializer_class = DocumentationSerializer

@api_view(['GET'])
def search_code(request):
    query = request.query_params.get('q', '')
    repository_id = request.query_params.get('repository_id', None)

    if not query:
        return Response({"error": "Query parameter 'q' is required"}, status=status.HTTP_400_BAD_REQUEST)

    files = CodeFile.objects.filter(content__icontains=query)
    if repository_id:
        files = files.filter(repository_id=repository_id)

    results = []
    for file in files:
        lines = file.content.split('\n')
        matches = []
        for i, line in enumerate(lines):
            if query.lower() in line.lower():
                matches.append({
                    'line_number': i + 1,
                    'line_content': line.strip()
                })

        if matches:
            results.append({
                'id': file.id,
                'name': file.name,
                'path': file.path,
                'matches': matches
            })

    return Response(results)

def generate_file_tree(directory):
    """Generate a file tree structure starting from the given directory."""
    result = []
    try:
        for item in os.listdir(directory):
            if item.startswith('.'):
                continue

            full_path = os.path.join(directory, item)

            if os.path.isdir(full_path):
                result.append({
                    'name': item,
                    'path': full_path,
                    'type': 'directory',
                    'children': generate_file_tree(full_path)
                })
            else:
                result.append({
                    'name': item,
                    'path': full_path,
                    'type': 'file'
                })
    except Exception as e:
        print(f"Error reading directory {directory}: {e}")

    return result

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import os
from .models import CodeRepository, CodeFile

# Create a dedicated view function for reading files by path
@api_view(['GET'])
def read_file_by_path(request):
    path = request.query_params.get('path')
    repository_id = request.query_params.get('repository_id')

    if not path or not repository_id:
        return Response(
            {"error": "Path and repository_id parameters are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # First try to find the file in the database
        try:
            file = CodeFile.objects.get(path=path, repository_id=repository_id)
            # If we found it in the database, return its data
            return Response({
                "id": file.id,
                "name": file.name,
                "path": file.path,
                "type": file.file_type
            })
        except CodeFile.DoesNotExist:
            # If not in database, try to read from filesystem
            repository = CodeRepository.objects.get(id=repository_id)
            full_path = os.path.join(repository.path, path)
            
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                return Response({"error": f"File not found: {path}"}, status=404)
            
            # Get file name and extension
            file_name = os.path.basename(path)
            _, ext = os.path.splitext(file_name)
            file_type = ext.lstrip('.').lower() if ext else 'txt'
            
            # Create a new file record
            file = CodeFile.objects.create(
                repository_id=repository_id,
                path=path,
                name=file_name,
                file_type=file_type
            )
            
            return Response({
                "id": file.id,
                "name": file.name,
                "path": file.path,
                "type": file.file_type
            })
            
    except CodeRepository.DoesNotExist:
        return Response({"error": "Repository not found"}, status=404)
    except Exception as e:
        print(f"Error in read_file_by_path: {str(e)}")
        return Response({"error": f"Error reading file: {str(e)}"}, status=500)

router = DefaultRouter()
router.register(r'repositories', views.CodeRepositoryViewSet)
router.register(r'files', views.CodeFileViewSet)
router.register(r'documentation', views.DocumentationViewSet)

urlpatterns = [
    path('', include(router.urls)),  # This keeps your original URLs working
    path('api/files/by_path/', read_file_by_path, name='file-by-path'),
    path('api/search/', views.search_code, name='search-code'),
]
