import os
import re
from django.core.management.base import BaseCommand
from api.models import CodeRepository, CodeFile, Documentation

# Supported text file extensions
TEXT_EXTENSIONS = {
    'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'scss',
    'txt', 'md', 'json', 'yml', 'yaml', 'sh', 'env', 'rb',
    'go', 'java', 'kt', 'php', 'r', 'swift', 'rs', 'dart'
}

class Command(BaseCommand):
    help = 'Import a code repository into the system'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Name of the repository')
        parser.add_argument('path', type=str, help='Path to the repository')

    def handle(self, *args, **options):
        name = options['name']
        path = options['path']
        
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f'Path does not exist: {path}'))
            return
        
        if not os.path.isdir(path):
            self.stderr.write(self.style.ERROR(f'Path is not a directory: {path}'))
            return
        
        repository, created = CodeRepository.objects.get_or_create(
            name=name,
            defaults={'path': path}
        )
        
        if not created:
            self.stdout.write(self.style.WARNING(f'Repository "{name}" already exists. Updating files...'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created repository: {name}'))
        
        file_count = 0
        skipped_count = 0
        
        for root, dirs, files in os.walk(path):
            # Skip hidden and common directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', 'venv', '__pycache__', '.git', '.idea', 'dist', 'build'
            }]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, path)
                
                try:
                    # Skip files larger than 5MB (increased from 1MB)
                    file_size = os.path.getsize(file_path)
                    if file_size > 5 * 1024 * 1024:
                        self.stdout.write(self.style.WARNING(f'Skipping large file ({file_size/1024/1024:.1f}MB): {rel_path}'))
                        skipped_count += 1
                        continue
                    
                    # Check file extension first
                    _, ext = os.path.splitext(file)
                    ext = ext.lstrip('.').lower()
                    
                    # Skip known binary extensions
                    if ext in {'exe', 'dll', 'so', 'dylib', 'o', 'a', 'class', 'jar', 'war'}:
                        skipped_count += 1
                        continue
                    
                    # Try reading file with proper encoding
                    try:
                        with open(file_path, 'rb') as f:
                            raw_content = f.read()
                            
                        # Try UTF-8 first
                        try:
                            content = raw_content.decode('utf-8')
                            encoding = 'utf-8'
                        except UnicodeDecodeError:
                            # Fallback to latin-1 for binary detection
                            content = raw_content.decode('latin-1', errors='replace')
                            encoding = 'latin-1'
                            
                            # Check for excessive replacement chars indicating binary
                            if content.count('�') / len(content) > 0.1:
                                raise UnicodeDecodeError('binary', b'', 0, 0, 'Binary file detected')
                            
                    except (UnicodeDecodeError, IOError) as e:
                        # Create minimal record for binary files
                        code_file, _ = CodeFile.objects.update_or_create(
                            repository=repository,
                            path=rel_path,
                            defaults={
                                'name': file,
                                'content': f'[Binary file - {file_size} bytes]',
                                'file_type': ext or 'bin',
                                'is_binary': True,
                                'size': file_size
                            }
                        )
                        skipped_count += 1
                        continue
                    
                    # Determine file type
                    file_type = ext if ext in TEXT_EXTENSIONS else 'txt'
                    
                    # Create/update file record
                    code_file, file_created = CodeFile.objects.update_or_create(
                        repository=repository,
                        path=rel_path,
                        defaults={
                            'name': file,
                            'content': content,
                            'file_type': file_type,
                            'is_binary': False,
                            'size': file_size,
                            'encoding': encoding
                        }
                    )
                    
                    # Extract documentation
                    doc_content = self.extract_documentation(content, file_type)
                    
                    Documentation.objects.update_or_create(
                        file=code_file,
                        defaults={'content': doc_content}
                    )
                    
                    file_count += 1
                    if file_count % 10 == 0:
                        self.stdout.write(f'Imported {file_count} files...')
                        
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Error importing {rel_path}: {str(e)}'))
                    skipped_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Import complete: {file_count} files processed, {skipped_count} skipped'
        ))

    def extract_documentation(self, content, file_type):
        """Universal documentation extractor with improved patterns"""
        doc = {
            'description': '',
            'entities': [],
            'warnings': []
        }
        
        # Common patterns for all file types
        patterns = {
            'block_comments': r'/\*\*(.*?)\*/|<!--(.*?)-->|"""(.*?)"""|\'\'\'(.*?)\'\'\'',
            'function_def': r'(?:def|function)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)',
            'class_def': r'class\s+([a-zA-Z_]\w*)(?:\s*\(([^)]*)\))?\s*{?'
        }
        
        # Extract all comment blocks
        comment_blocks = re.findall(patterns['block_comments'], content, re.DOTALL)
        if comment_blocks:
            doc['description'] = '\n'.join(
                [max(block, key=len).strip() for block in comment_blocks if any(block)]
            )
        
        # Language-specific extraction
        if file_type == 'py':
            doc['entities'] = self._extract_python_entities(content)
        elif file_type in {'js', 'jsx', 'ts', 'tsx'}:
            doc['entities'] = self._extract_javascript_entities(content)
        
        return doc
    
    def _extract_python_entities(self, content):
        """Improved Python entity extraction"""
        entities = []
        
        # Functions with docstrings
        func_pattern = r'(?:@\w+\s+)*def\s+(\w+)\s*\(([^)]*)\)\s*:(.*?)(?=\n\s*(?:@|def|class|\Z))'
        for match in re.finditer(func_pattern, content, re.DOTALL):
            docstring = self._extract_docstring(match.group(3))
            entities.append({
                'type': 'function',
                'name': match.group(1),
                'params': match.group(2).strip(),
                'doc': docstring
            })
        
        # Classes with docstrings
        class_pattern = r'class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:(.*?)(?=\n\s*(?:@|def|class|\Z))'
        for match in re.finditer(class_pattern, content, re.DOTALL):
            docstring = self._extract_docstring(match.group(3))
            entities.append({
                'type': 'class',
                'name': match.group(1),
                'inheritance': match.group(2) or '',
                'doc': docstring
            })
        
        return entities
    
    def _extract_javascript_entities(self, content):
        """Improved JavaScript/TypeScript entity extraction"""
        entities = []
        
        # Functions with JSDoc
        func_pattern = r'(?:/\*\*(.*?)\*/)?\s*(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)\s*\(([^)]*)\)|const\s+(\w+)\s*=\s*(?:\(([^)]*)\)\s*=>|function\s*\(([^)]*)\)))'
        for match in re.finditer(func_pattern, content, re.DOTALL):
            name = match.group(2) or match.group(4)
            params = match.group(3) or match.group(5) or match.group(6) or ''
            entities.append({
                'type': 'function',
                'name': name,
                'params': params,
                'doc': match.group(1).strip() if match.group(1) else ''
            })
        
        # Classes with JSDoc
        class_pattern = r'(?:/\*\*(.*?)\*/)?\s*(?:export\s+)?class\s+(\w+)\s*(?:extends\s+([^{\s]+))?\s*{'
        for match in re.finditer(class_pattern, content, re.DOTALL):
            entities.append({
                'type': 'class',
                'name': match.group(2),
                'inheritance': match.group(3) or '',
                'doc': match.group(1).strip() if match.group(1) else ''
            })
        
        return entities
    
    def _extract_docstring(self, body):
        """Extract docstring from function/class body"""
        doc_matches = re.findall(
            r'^\s*("""(.*?)"""|\'\'\'(.*?)\'\'\'|/\*\*(.*?)\*/)',
            body, 
            re.DOTALL
        )
        return '\n'.join([max(match[1:], key=len).strip() for match in doc_matches])