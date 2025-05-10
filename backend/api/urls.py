from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import os
from .models import CodeRepository, CodeFile

# Define the view function directly in urls.py to avoid import issues
@api_view(['GET'])
def read_file_by_path(request):
    """
    Read a file by its path and repository ID.
    """
    print("==== read_file_by_path called with params:", request.query_params)
    print("==== request path:", request.path)
    print("==== request method:", request.method)
    
    path = request.query_params.get('path')
    repository_id = request.query_params.get('repository_id')

    if not path or not repository_id:
        print("==== Missing required parameters")
        return Response(
            {"error": "Path and repository_id parameters are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get the repository
        repository = CodeRepository.objects.get(id=repository_id)
        full_path = os.path.join(repository.path, path)
        
        # First try to find the file in the database
        try:
            file = CodeFile.objects.get(path=path, repository_id=repository_id)
            print(f"==== Found file in database: {file.id}, {file.name}, {file.path}")
            
            # Check if content exists in the database
            if file.content and len(file.content.strip()) > 0:
                print(f"==== Using content from database for {file.path}")
                content = file.content
            else:
                # Read content from filesystem
                print(f"==== Reading content from filesystem for {file.path}")
                content = read_file_content(full_path)
                
                # Update the database with the content
                file.content = content
                file.save()
                
            return Response({
                "id": file.id,
                "name": file.name,
                "path": file.path,
                "type": file.file_type,
                "content": content  # Include content in the response
            })
        except CodeFile.DoesNotExist:
            print(f"==== File not found in database: {path}, {repository_id}")
            
            # Check if file exists in filesystem
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                print(f"==== File not found on filesystem: {full_path}")
                return Response({"error": f"File not found: {path}"}, status=404)
            
            # Get file name and extension
            file_name = os.path.basename(path)
            _, ext = os.path.splitext(file_name)
            file_type = ext.lstrip('.').lower() if ext else 'txt'
            
            # Read content from filesystem
            content = read_file_content(full_path)
            
            print(f"==== Creating new file record for: {file_name}, {path}, {file_type}")
            
            # Create a new file record with content
            file = CodeFile.objects.create(
                repository_id=repository_id,
                path=path,
                name=file_name,
                file_type=file_type,
                content=content  # Save content to database
            )
            
            return Response({
                "id": file.id,
                "name": file.name,
                "path": file.path,
                "type": file.file_type,
                "content": content  # Include content in the response
            })
            
    except CodeRepository.DoesNotExist:
        print(f"==== Repository not found: {repository_id}")
        return Response({"error": "Repository not found"}, status=404)
    except Exception as e:
        print(f"==== Error in read_file_by_path: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({"error": f"Error reading file: {str(e)}"}, status=500)

def read_file_content(file_path):
    """Helper function to read file content with different encodings."""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    content = None
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"==== Successfully read file with {encoding} encoding")
            return content
        except UnicodeDecodeError:
            continue
    
    if content is None:
        # If all encodings fail, it might be a binary file
        print(f"==== Could not read file with any encoding, might be binary")
        return f"// This appears to be a binary file\n// Binary files cannot be displayed in the text viewer."

router = DefaultRouter()
router.register(r'repositories', views.CodeRepositoryViewSet)
router.register(r'files', views.CodeFileViewSet)
router.register(r'documentation', views.DocumentationViewSet)

urlpatterns = [
    # Put the specific patterns first
    path('files/by_path/', read_file_by_path, name='file-by-path'),  # Remove the 'api/' prefix
    path('search/', views.search_code, name='search-code'),  # Remove the 'api/' prefix
    # Then include the router URLs
    path('', include(router.urls)),
]
