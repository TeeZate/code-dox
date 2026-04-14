from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import JSONField  # Django's built-in JSONField
from django.core.serializers.json import DjangoJSONEncoder
import os
import json

class CodeRepository(models.Model):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    documentation_version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name

    def get_file_count(self):
        """Helper method to get total files in repository"""
        return self.files.count()

    class Meta:
        verbose_name_plural = "Code Repositories"


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
    full_path = models.CharField(max_length=2048, blank=True)
    relative_path = models.CharField(max_length=2048, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    documentation_updated_at = models.DateTimeField(null=True, blank=True)
    documentation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('generated', 'Generated'),
            ('failed', 'Failed'),
            ('outdated', 'Outdated'),
        ],
        default='pending'
    )

    class Meta:
        unique_together = ('repository', 'path')
        indexes = [
            models.Index(fields=['repository', 'file_type']),
            models.Index(fields=['is_binary']),
            models.Index(fields=['documentation_status']),
        ]
        ordering = ['path']

    def save(self, *args, **kwargs):
        """Auto-populate path-related fields before saving"""
        if not self.relative_path:
            self.relative_path = self.path
        if not self.full_path and self.repository:
            self.full_path = os.path.join(self.repository.path, self.path)
        super().save(*args, **kwargs)

    def get_absolute_path(self):
        if not self.full_path and self.repository:
            return os.path.join(self.repository.path, self.path)
        return self.full_path

    def is_text_file(self):
        return not self.is_binary and self.file_type.lower() in {
            'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'scss',
            'txt', 'md', 'json', 'yml', 'yaml', 'sh', 'env', 'rb',
            'go', 'java', 'kt', 'php', 'r', 'swift', 'rs', 'dart'
        }

    def __str__(self):
        return f"{self.repository.name}/{self.path} ({'binary' if self.is_binary else self.file_type})"


class Documentation(models.Model):
    file = models.OneToOneField(
        CodeFile, 
        on_delete=models.CASCADE, 
        related_name='documentation'
    )
    content = JSONField(encoder=DjangoJSONEncoder, default=dict)  # Using Django's built-in JSONField
    
    # Metadata fields
    summary = models.TextField(blank=True)
    purpose = models.TextField(blank=True)
    key_functions = models.TextField(blank=True)
    dependencies = models.TextField(blank=True)
    
    # Analysis metadata
    analysis_version = models.CharField(max_length=50, default='1.0')
    generated_by = models.CharField(max_length=100, default='system')
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Documentation"
        indexes = [
            models.Index(fields=['file']),
        ]

    def __str__(self):
        return f"Documentation for {self.file.path} (v{self.analysis_version})"

    def update_content(self, content_dict):
        """Update content and related fields"""
        self.content = content_dict
        self.summary = content_dict.get('summary', '')
        self.purpose = content_dict.get('purpose', '')
        
        # Serialize key functions if present
        key_funcs = content_dict.get('key_functionality', [])
        self.key_functions = '\n'.join(key_funcs) if isinstance(key_funcs, list) else str(key_funcs)
        
        # Serialize dependencies if present
        deps = content_dict.get('dependencies', {})
        self.dependencies = json.dumps(deps) if isinstance(deps, dict) else str(deps)
        
        self.save()
        self.file.documentation_status = 'generated'
        self.file.documentation_updated_at = self.updated_at
        self.file.save()


class DocumentationHistory(models.Model):
    """Model to track documentation generation history"""
    file = models.ForeignKey(
        CodeFile, 
        on_delete=models.CASCADE, 
        related_name='documentation_history'
    )
    content = JSONField(encoder=DjangoJSONEncoder, default=dict)
    version = models.CharField(max_length=50)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ])
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Documentation Histories"
        ordering = ['-generated_at']

    def __str__(self):
        return f"Doc history for {self.file.path} (v{self.version})"


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    documentation_preferences = JSONField(
        default=dict,
        help_text="User preferences for documentation display"
    )
    
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',
        blank=True
    )

    def __str__(self):
        return self.username