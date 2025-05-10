from django.db import models
from django.contrib.auth.models import AbstractUser
import os

class CodeRepository(models.Model):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class CodeFile(models.Model):
    repository = models.ForeignKey(
        CodeRepository, 
        on_delete=models.CASCADE, 
        related_name='files'
    )
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=1024)
    content = models.TextField(blank=True)
    file_type = models.CharField(max_length=50)
    is_binary = models.BooleanField(default=False)
    size = models.PositiveIntegerField(default=0)
    encoding = models.CharField(max_length=20, default='utf-8')
    full_path = models.CharField(max_length=2048, blank=True)  # Absolute filesystem path
    relative_path = models.CharField(max_length=2048, blank=True)  # Path relative to repo root
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('repository', 'path')  # Prevent duplicate paths in same repo
        indexes = [
            models.Index(fields=['repository', 'file_type']),
            models.Index(fields=['is_binary']),
        ]

    def save(self, *args, **kwargs):
        """Auto-populate path-related fields before saving"""
        if not self.relative_path:
            self.relative_path = self.path
        if not self.full_path and self.repository:
            self.full_path = os.path.join(self.repository.path, self.path)
        super().save(*args, **kwargs)

    def get_absolute_path(self):
        """Get the full filesystem path if not already set"""
        if not self.full_path and self.repository:
            return os.path.join(self.repository.path, self.path)
        return self.full_path

    def is_text_file(self):
        """Check if file is considered text-based"""
        return not self.is_binary and self.file_type.lower() in {
            'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'scss',
            'txt', 'md', 'json', 'yml', 'yaml', 'sh', 'env', 'rb',
            'go', 'java', 'kt', 'php', 'r', 'swift', 'rs', 'dart'
        }

    def __str__(self):
        return f"{self.repository.name}/{self.path} ({'binary' if self.is_binary else self.file_type})"

class Documentation(models.Model):
    file = models.OneToOneField(CodeFile, on_delete=models.CASCADE, related_name='documentation')
    # Use TextField instead of JSONField for compatibility
    content = models.TextField(default='{}')  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Documentation for {self.file.path}"
    
    def set_content(self, content_dict):
        """Set content as JSON string"""
        import json
        self.content = json.dumps(content_dict)
    
    def get_content(self):
        """Get content as Python dictionary"""
        import json
        try:
            return json.loads(self.content)
        except:
            return {}

    
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    
    # Fix the reverse accessor clash by adding related_name
    groups = models.ManyToManyField('auth.Group', related_name='customuser_groups', blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name='customuser_permissions', blank=True)

    def __str__(self):
        return self.username
