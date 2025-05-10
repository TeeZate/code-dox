from rest_framework import serializers
from .models import CodeRepository, CodeFile, Documentation, CustomUser

class DocumentationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documentation
        fields = ['id', 'description', 'metadata']

class CodeFileSerializer(serializers.ModelSerializer):
    documentation = DocumentationSerializer(read_only=True)
    
    class Meta:
        model = CodeFile
        fields = ['id', 'name', 'path', 'content', 'file_type', 'documentation']

class CodeRepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CodeRepository
        fields = ['id', 'name', 'path', 'created_at', 'updated_at']

class FileTreeSerializer(serializers.Serializer):
    name = serializers.CharField()
    path = serializers.CharField()
    type = serializers.CharField()
    children = serializers.ListField(child=serializers.DictField(), required=False)

# User Registration Serializer
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
