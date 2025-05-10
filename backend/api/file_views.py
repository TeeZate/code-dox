import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import CodeRepository, CodeFile

@api_view(['GET'])
def read_file_by_path(request):
    """
    Read a file by its path and repository ID.
    """
    print("read_file_by_path called with params:", request.query_params)
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
            print(f"Found file in database: {file.id}, {file.name}, {file.path}")
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
            
            print(f"File not found in database, checking filesystem: {full_path}")
            
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                print(f"File not found on filesystem: {full_path}")
                return Response({"error": f"File not found: {path}"}, status=404)
            
            # Get file name and extension
            file_name = os.path.basename(path)
            _, ext = os.path.splitext(file_name)
            file_type = ext.lstrip('.').lower() if ext else 'txt'
            
            print(f"Creating new file record for: {file_name}, {path}, {file_type}")
            
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
        print(f"Repository not found: {repository_id}")
        return Response({"error": "Repository not found"}, status=404)
    except Exception as e:
        print(f"Error in read_file_by_path: {str(e)}")
        return Response({"error": f"Error reading file: {str(e)}"}, status=500)
