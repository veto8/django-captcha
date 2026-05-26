# Django CAPTCHA - File Storage Backend

A Django CAPTCHA application with file-based storage backend support. This is an enhanced version of `django-simple-captcha` that allows you to store CAPTCHA data using Django's file storage system instead of only database/cache backends.

## Features

- **File Storage Backend**: Store CAPTCHA data directly in your file system or cloud storage (S3, Azure, etc.) via Django's FileSystemStorage
- **Django 4.2+**: Full compatibility with modern Django versions
- **Image Generation**: Generate CAPTCHA images with Pillow
- **Flexible Storage**: Use database, cache, or file storage depending on your needs
- **Easy Integration**: Simple Django app with minimal configuration

## Installation

### Via pip

```bash
poetry add django-file-captcha
```

Or install from this repository:

```bash
poetry add git+https://github.com/myridia/django-file-captcha.git
```

### Dependencies

- Django >= 4.2
- Pillow >= 6.2.0
- django-ranged-response == 0.2.0

## Quick Start

### 1. Add to Django Settings

```python
INSTALLED_APPS = [
    # ...
    'captcha',
]
```

### 2. Configure CAPTCHA Storage

Choose your storage backend:

#### Option A: File Storage Backend (Default)

```python
# settings.py
CAPTCHA_STORAGE_BACKEND = 'captcha.storage.FileStorageBackend'

# Optional: Configure storage location
CAPTCHA_STORAGE_PATH = 'captcha_storage/'  # Relative to MEDIA_ROOT
```

#### Option B: Cache Backend

```python
CAPTCHA_STORAGE_BACKEND = 'captcha.storage.CacheStorageBackend'
```

#### Option C: Database Backend

```python
CAPTCHA_STORAGE_BACKEND = 'captcha.storage.DatabaseStorageBackend'
```

### 3. Add URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path('captcha/', include('captcha.urls')),
]
```

### 4. Use in Forms

```python
from django import forms
from captcha.fields import CaptchaField

class MyForm(forms.Form):
    name = forms.CharField()
    captcha = CaptchaField()
```

### 5. Use in Templates

```html
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Submit</button>
</form>
```

## File Storage Backend Details

The File Storage Backend is ideal for:
- High-traffic applications (reduces database load)
- Distributed systems with shared file storage
- Cloud deployments with S3 or similar storage
- Scenarios where you need persistent CAPTCHA data

### How It Works

1. CAPTCHA data is generated and stored as files in your configured storage location
2. Each CAPTCHA gets a unique identifier
3. CAPTCHA images are served as regular static files
4. Data can be cleaned up periodically using Django management commands

### File Structure

```
media/
└── captcha_storage/
    ├── captcha_hash_1.json
    ├── captcha_hash_2.json
    └── ...
```

## Configuration Options

```python
# settings.py

# Storage backend to use
CAPTCHA_STORAGE_BACKEND = 'captcha.storage.FileStorageBackend'

# Path for file storage (relative to MEDIA_ROOT)
CAPTCHA_STORAGE_PATH = 'captcha_storage/'

# CAPTCHA image settings
CAPTCHA_IMAGE_SIZE = (400, 50)
CAPTCHA_FONT_SIZE = 36
CAPTCHA_FONT_PATH = None  # Uses system default if not specified

# CAPTCHA length
CAPTCHA_LENGTH = 6

# CAPTCHA timeout in seconds
CAPTCHA_TIMEOUT = 300  # 5 minutes

# Noise level
CAPTCHA_NOISE_FUNCTIONS = (
    'captcha.helpers.noise_arcs',
    'captcha.helpers.noise_dots',
)
```

## Advanced Usage

### Custom Storage Backend

Create your own storage backend by extending the base class:

```python
from captcha.storage import StorageBackend

class CustomBackend(StorageBackend):
    def store(self, captcha_key, data):
        # Your implementation
        pass
    
    def retrieve(self, captcha_key):
        # Your implementation
        pass
    
    def delete(self, captcha_key):
        # Your implementation
        pass
```

### AWS S3 Storage

```python
# settings.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'my-bucket'

CAPTCHA_STORAGE_BACKEND = 'captcha.storage.FileStorageBackend'
```

### Azure Blob Storage

```python
# settings.py
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
AZURE_ACCOUNT_NAME = 'myaccount'

CAPTCHA_STORAGE_BACKEND = 'captcha.storage.FileStorageBackend'
```

## Management Commands

### Cleanup Expired CAPTCHAs

```bash
# Remove CAPTCHAs older than timeout period
python manage.py captcha_cleanup
```

### Clear All CAPTCHAs

```bash
python manage.py captcha_clear
```

## Testing

Run tests with tox:

```bash
# Install tox
pip install tox>=4.31 tox-uv>=1.23

# Run all tests
tox

# Run specific Python version
tox -e py312
```

## Troubleshooting

### CAPTCHA Images Not Displaying

- Ensure `MEDIA_ROOT` and `MEDIA_URL` are configured
- Check file permissions in `CAPTCHA_STORAGE_PATH`
- Verify static files are being served in development

### Storage Backend Errors

- Confirm the storage backend path is correct
- Check Django app is in `INSTALLED_APPS`
- Run migrations if using database backend

### Timeout Issues

- Adjust `CAPTCHA_TIMEOUT` setting
- Check if storage system is accessible
- Monitor file system space for file storage backend

## API Reference

### CaptchaField

```python
from captcha.fields import CaptchaField

# Basic usage
captcha = CaptchaField()

# With custom label
captcha = CaptchaField(label='Verify you are human')

# Make optional
captcha = CaptchaField(required=False)
```

### Form Validation

The CaptchaField automatically validates:
- CAPTCHA key exists in storage
- CAPTCHA has not expired
- User input matches stored CAPTCHA value
- CAPTCHA is not reused

## Performance Considerations

| Backend | Pros | Cons |
|---------|------|------|
| **File Storage** | Fast, scalable, cloud-ready | Requires file sync in distributed systems |
| **Cache** | Very fast, volatile | Limited capacity, lost on restart |
| **Database** | Persistent, file | Slower, requires DB queries |

## Migration Guide

### From Cache Backend to File Storage

```python
# Before (settings.py)
CAPTCHA_STORAGE_BACKEND = 'captcha.storage.CacheStorageBackend'

# After
CAPTCHA_STORAGE_BACKEND = 'captcha.storage.FileStorageBackend'
CAPTCHA_STORAGE_PATH = 'captcha_storage/'
```

No data migration needed - old CAPTCHAs are simply abandoned.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues, questions, or suggestions:
- GitHub Issues: https://github.com/myridia/django-file-captcha/issues
- Original Project: https://github.com/myridia/django-file-captcha

## Changelog

See [CHANGES](CHANGES) file for version history.

## Credits

Hard Forked from https://github.com/mbi/django-simple-captcha
---

**Status**: File storage backend is production-ready. Start using it today for scalable CAPTCHA handling!


## Extra Repository ##
```
 git remote add codeberg ssh://git@codeberg.org/myridia/django-file-capture 
 git push codeberg -f

```

