# Django CAPTCHA File Storage Backend - Detailed Mechanics

## Overview

This document provides an in-depth explanation of how the **file storage backend** feature works in the `feature/file-storage-backend` branch of django-captcha. This branch introduces a file-based storage system as an alternative to database or cache-based CAPTCHA storage, enabling better scalability and cloud-native deployments.

## Architecture

### Core Storage System

The file storage backend operates on a **filesystem-based persistence model** where CAPTCHA challenge-response data is stored as JSON files instead of database records or cache entries.

#### Key Components:

1. **FileSystemCaptchaStore** (`captcha/storage.py`)
   - Core storage class implementing CRUD operations for CAPTCHA data
   - Manages file I/O operations using Django's `default_storage` abstraction
   - Handles expiration, pooling, and cleanup logic

2. **CaptchaStore Wrapper** (`captcha/models.py`)
   - Backward-compatible API wrapper maintaining the original `CaptchaStore` interface
   - Delegates all operations to `FileSystemCaptchaStore`
   - Ensures existing code continues to work without modifications

3. **Views Layer** (`captcha/views.py`)
   - `captcha_image()`: Renders CAPTCHA images from stored challenge data
   - `captcha_audio()`: Generates audio alternatives for accessibility
   - `captcha_refresh()`: Provides AJAX refresh functionality

4. **Form Fields Layer** (`captcha/fields.py`)
   - `CaptchaField`: Form field for Django forms
   - `CaptchaTextInput`: Widget rendering challenge and response inputs
   - Handles client-side validation and interaction

---

## Data Flow

### 1. CAPTCHA Generation & Storage

```
User requests form with CAPTCHA
        ↓
Form renders CaptchaField
        ↓
CaptchaTextInput.render() called
        ↓
fetch_captcha_store() invoked
        ↓
CaptchaStore.generate_key(generator) OR CaptchaStore.pick()
        ↓
FileSystemCaptchaStore.generate_key()
        ↓
Generator creates challenge & response
        ↓
FileSystemCaptchaStore.create()
        ↓
Unique hashkey generated using SHA1
        ↓
JSON file saved to storage with:
- challenge (text to display)
- response (expected answer)
- hashkey (unique identifier)
- expiration (ISO format timestamp)
        ↓
Hashkey returned to form for rendering
```

### 2. Image Generation & Display

```
Browser requests CAPTCHA image (captcha_image view)
        ↓
View receives hashkey from URL parameter
        ↓
FileSystemCaptchaStore.get(hashkey)
        ↓
Load JSON file from storage
        ↓
Return data or HTTP 410 if expired
        ↓
Render image using PIL:
- Extract challenge text from stored data
- Load font (TTF or system default)
- Generate character image with noise filters
- Apply color schemes and rotation
- Support animated (GIF/AVIF) format if configured
        ↓
Return image as PNG/GIF/AVIF response
```

### 3. Form Submission & Validation

```
User submits form with CAPTCHA answer
        ↓
CaptchaField.clean() called
        ↓
Response text normalized (stripped, lowercased)
        ↓
Optional: Clean expired CAPTCHAs (if not using pool)
        ↓
Lookup in storage by hashkey and response
        ↓
Check expiration timestamp
        ↓
Success: Delete used CAPTCHA, form validates
        ↓
Failure: Raise ValidationError, form rejects
```

---

## File System Structure

### Storage Location

```
MEDIA_ROOT/
└── captcha_store/                    # Base storage path (configurable)
    ├── a1b2c3d4e5f6...json          # CAPTCHA data file 1
    ├── f6e5d4c3b2a1...json          # CAPTCHA data file 2
    ├── x9y8z7w6v5u4...json          # CAPTCHA data file 3
    └── ... (hundreds/thousands of files)
```

### File Format

Each `.json` file contains:

```json
{
    "challenge": "aBc123",              # Text displayed in CAPTCHA image
    "response": "abc123",               # Expected user answer (lowercased)
    "hashkey": "a1b2c3d4e5f6...",      # SHA1 hash used as file identifier
    "expiration": "2025-05-25T12:30:00+00:00"  # ISO format expiration time
}
```

---

## Storage Operations

### Create (Generate New CAPTCHA)

```python
def create(challenge, response):
    """
    Steps:
    1. Normalize response to lowercase
    2. Generate unique SHA1 hashkey from:
       - Random seed
       - Current timestamp
       - Challenge text
       - Response text
    3. Calculate expiration time (now + CAPTCHA_TIMEOUT)
    4. Create JSON data object
    5. Save to file using default_storage
    6. Return hashkey
    """
```

**Location:** `captcha/storage.py:53-73`

### Retrieve (Load CAPTCHA Data)

```python
def get(hashkey):
    """
    Steps:
    1. Construct file path from hashkey
    2. Open file using default_storage
    3. Parse JSON content
    4. Return data dict
    5. Return None on FileNotFoundError or JSON decode error
    """
```

**Location:** `captcha/storage.py:75-85`

### Verify Existence

```python
def exists(hashkey):
    """
    Quick check if CAPTCHA file exists without reading content.
    Uses default_storage.exists() for efficient lookup.
    """
```

**Location:** `captcha/storage.py:87-91`

### Delete (Remove CAPTCHA)

```python
def delete(hashkey):
    """
    Removes single CAPTCHA file after successful validation.
    Prevents reuse of same CAPTCHA for multiple attempts.
    """
```

**Location:** `captcha/storage.py:93-98`

### Cleanup Expired

```python
def remove_expired():
    """
    Batch operation that:
    1. Lists all .json files in storage directory
    2. For each file:
       - Read and parse JSON
       - Compare expiration timestamp with current time
       - Delete if expired or corrupted
    3. Silently handle missing directories
    
    Performance consideration:
    - Full directory scan required
    - Suitable for periodic background tasks
    - Not for request path in high-traffic scenarios
    """
```

**Location:** `captcha/storage.py:100-122`

---

## Pooling Mechanism

### Concept

Instead of generating a new CAPTCHA for each request, a pool of pre-generated CAPTCHAs can be maintained for faster response times.

### Pool Generation

```python
def create_pool(count=1000):
    """
    Pre-generates a specified number of CAPTCHAs and stores them.
    Typical usage: Run once during deployment or scheduled daily.
    """
```

**Location:** `captcha/storage.py:169-175`

### Pool Picking

```python
def pick():
    """
    Steps:
    1. Check CAPTCHA_GET_FROM_POOL setting
    2. If false: Generate new CAPTCHA (normal behavior)
    3. If true:
       - List all files in storage
       - For each file with .json extension:
         - Parse expiration timestamp
         - Check if expires after CAPTCHA_GET_FROM_POOL_TIMEOUT
       - Return random valid CAPTCHA from pool
       - If pool empty: Generate new CAPTCHA (fallback)
    """
```

**Location:** `captcha/storage.py:131-167`

### Pool Benefits

- **Reduced CPU load**: No image generation on every request
- **Faster response times**: Pre-computed challenges
- **Better for CDN**: Smaller dynamic request overhead
- **Scalability**: Can be pre-warmed during off-peak hours

### Pool Drawbacks

- **File system space**: Stores many unused CAPTCHAs
- **Predictability risk**: Smaller pool = easier to brute force
- **Management overhead**: Need cleanup/maintenance tasks

---

## Key Generation Algorithm

### Hashkey Generation

```python
def _generate_hashkey(challenge, response):
    """
    SHA1-based deterministic hash generation.
    
    Input composition:
    - randrange(0, 2^64)              # 64-bit random number
    - time.time()                      # Unix timestamp with microseconds
    - challenge                        # Challenge text string
    - response                         # Response text string
    
    Process:
    1. Concatenate all inputs as strings
    2. Encode to UTF-8 bytes
    3. Compute SHA1 hash
    4. Return hexadecimal digest
    
    Resulting hashkey is 40 hex characters (160 bits)
    
    Collision probability: ~2^-160 (cryptographically safe)
    """
```

**Location:** `captcha/storage.py:36-45`

### Why SHA1?

- **Deterministic**: Same inputs always produce same hash
- **Fast**: Sufficient for session key generation
- **Standard**: Well-tested and widely available
- **Sufficient entropy**: Time + random + challenge + response = collision-resistant

---

## Expiration Management

### Expiration Model

```
Current time: 12:00:00
CAPTCHA_TIMEOUT: 300 seconds (5 minutes)
Expiration time: 12:05:00
        ↓
(Server time must be synchronized across instances)
```

### Expiration Check Logic

```python
# During validation
expiration_dt = timezone.datetime.fromisoformat(data["expiration"])
if expiration_dt <= timezone.now():
    # CAPTCHA has expired, reject
else:
    # CAPTCHA still valid, allow
```

### Cleanup Strategies

**Strategy 1: On-Demand Cleanup** (default)
```python
# In CaptchaField.clean()
if not settings.CAPTCHA_GET_FROM_POOL:
    CaptchaStore.remove_expired()
```
- Triggered during form validation
- Suitable for low-traffic sites
- Can cause occasional latency spikes

**Strategy 2: Scheduled Cleanup** (recommended for high traffic)
```bash
# Management command
python manage.py captcha_cleanup
```
- Run periodically via Celery/APScheduler
- Prevents storage bloat
- Smooth performance characteristics

---

## Image Rendering Pipeline

### Step 1: Font Loading

```python
# Determine font path from settings
if isinstance(settings.CAPTCHA_FONT_PATH, str):
    fontpath = settings.CAPTCHA_FONT_PATH
elif isinstance(settings.CAPTCHA_FONT_PATH, (list, tuple)):
    fontpath = random.choice(settings.CAPTCHA_FONT_PATH)  # Vary fonts

# Load font
if fontpath.lower().endswith("ttf"):
    font = ImageFont.truetype(fontpath, settings.CAPTCHA_FONT_SIZE * scale)
else:
    font = ImageFont.load(fontpath)  # Bitmap font
```

**Location:** `captcha/views.py:66-78`

### Step 2: Character Processing

```python
# Split text into characters, combining punctuation
charlist = []
for char in text:
    if char in settings.CAPTCHA_PUNCTUATION and len(charlist) >= 1:
        charlist[-1] += char  # Attach to previous char
    else:
        charlist.append(char)
```

**Example:** "A+B-C" → `['A+', 'B-', 'C']`

**Location:** `captcha/views.py:89-94`

### Step 3: Per-Character Rendering

For each character:
1. Create foreground color image (random color per character)
2. Create character image with padding
3. Apply optional letter rotation (3D twist effect)
4. Create mask image with character placement
5. Composite character onto main image
6. Accumulate horizontal position for next character

**Location:** `captcha/views.py:99-131`

### Step 4: Noise & Filters

```python
# Optional: Apply per-frame noise for animated CAPTCHA
if settings.CAPTCHA_ANIMATED:
    image = add_noise(image)
    frames.append(image)
else:
    # Static CAPTCHA: Apply noise once
    image = add_noise(image)
```

Noise functions configured in settings:
- `captcha.helpers.noise_arcs`: Draw curved lines
- `captcha.helpers.noise_dots`: Scatter random dots
- Custom filter functions for additional effects

**Location:** `captcha/views.py:42-50, 186`

### Step 5: Format Output

```python
if settings.CAPTCHA_ANIMATED:
    # Save as GIF or AVIF with frame sequence
    frames[0].save(out, "GIF", save_all=True, append_images=frames[1:],
                   duration=500, loop=0, disposal=2)
    content_type = "image/gif"
else:
    # Save single PNG image
    image.save(out, "PNG")
    content_type = "image/png"

# Return HTTP response with proper content type
```

**Location:** `captcha/views.py:169-190`

### Deterministic Rendering

```python
# CRITICAL: Seed random generator with hashkey
random.seed(key)
# ... render image ...
# Reset random generator to prevent security issues
random.seed()
```

**Purpose:** Ensures identical image for same hashkey across renders
**Security:** Prevents attacker from predicting RNG after seed knowledge

**Location:** `captcha/views.py:62, 201`

---

## Configuration Parameters

### Storage Settings

| Setting | Default | Type | Purpose |
|---------|---------|------|---------|
| `CAPTCHA_STORAGE_PATH` | `"captcha_store"` | str | Directory for storing JSON files (relative to MEDIA_ROOT) |
| `CAPTCHA_GET_FROM_POOL` | `False` | bool | Enable pre-generated CAPTCHA pool |
| `CAPTCHA_GET_FROM_POOL_TIMEOUT` | `600` | int | Minimum seconds until pool CAPTCHA expires (seconds) |

### Image Generation Settings

| Setting | Default | Type | Purpose |
|---------|---------|------|---------|
| `CAPTCHA_IMAGE_SIZE` | `(400, 50)` | tuple | (width, height) of rendered image |
| `CAPTCHA_FONT_SIZE` | `36` | int | Character font size in pixels |
| `CAPTCHA_FONT_PATH` | `None` | str/list | Path to TTF/bitmap font file(s) |
| `CAPTCHA_BACKGROUND_COLOR` | `#ffffff` | str | Hex color or `"transparent"` |
| `CAPTCHA_LETTER_ROTATION` | `None` | tuple | (min, max) degrees rotation range |
| `CAPTCHA_PUNCTUATION` | `".,;:"` | str | Characters to attach to previous |
| `CAPTCHA_ANIMATED` | `False` | bool | Generate animated GIF/AVIF |
| `CAPTCHA_ANIMATED_USE_AVIF` | `False` | bool | Use AVIF instead of GIF |
| `CAPTCHA_2X_IMAGE` | `False` | bool | Support 2x scale for Retina displays |

### Validation Settings

| Setting | Default | Type | Purpose |
|---------|---------|------|---------|
| `CAPTCHA_TIMEOUT` | `300` | int | Seconds until CAPTCHA expires |
| `CAPTCHA_LENGTH` | `6` | int | Number of characters (challenge-dependent) |
| `CAPTCHA_TEST_MODE` | `False` | bool | Accept `"passed"` as answer |

### Accessibility Settings

| Setting | Default | Type | Purpose |
|---------|---------|------|---------|
| `CAPTCHA_FLITE_PATH` | `None` | str | Path to flite binary for audio generation |
| `CAPTCHA_SOX_PATH` | `None` | str | Path to sox binary for audio noise |

---

## Security Considerations

### 1. Hashkey Security

**Strength:**
- 64-bit random number provides ~2^64 entropy
- Current timestamp ensures uniqueness
- SHA1 hash provides collision resistance

**Weakness:**
- SHA1 is cryptographically weak (but sufficient here)
- Hashkey visible in URLs (not secret, just unique)

### 2. Response Validation

**Protections:**
- Case-insensitive comparison prevents trivial variation
- Single-use deletion prevents replay attacks
- Expiration time prevents indefinite reuse

**Vulnerability:**
- Network sniffing could capture hashkey + response pair
- Mitigation: Always use HTTPS

### 3. Storage Security

**File Permissions:**
```bash
chmod 600 media/captcha_store/*.json  # Owner read/write only
```

**Isolation:**
- Separate directory from application code
- Dedicated storage backend (S3, Azure, etc.)
- Encrypted at-rest for sensitive deployments

### 4. Brute Force Protection

**With Fixed CAPTCHA:**
- Attacker knows challenge (visible in image)
- Response is limited set (6 characters = 36^6 or 2.2 billion combinations)
- Timeout prevents infinite retry window

**Mitigation:**
- Keep timeout short (300-600 seconds)
- Rate limit failed attempts
- Use pool with large pre-generated set

---

## Storage Backend Compatibility

### Django File Storage Backends

The file storage system uses Django's `default_storage` abstraction, supporting:

#### FileSystem Storage (Default)
```python
# settings.py
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = '/var/media/'
MEDIA_URL = '/media/'
```

#### AWS S3
```python
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'my-bucket'
AWS_S3_REGION_NAME = 'us-east-1'
```

#### Azure Blob Storage
```python
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
AZURE_ACCOUNT_NAME = 'myaccount'
AZURE_ACCOUNT_KEY = 'mykey'
```

#### Google Cloud Storage
```python
DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
GS_BUCKET_NAME = 'my-bucket'
```

**Benefit:** Storage backend is **pluggable** without code changes!

---

## Performance Characteristics

### File Operations Complexity

| Operation | Time | Scalability |
|-----------|------|-------------|
| Create CAPTCHA | O(1) | Excellent - hash calculation + file write |
| Get CAPTCHA | O(1) | Excellent - direct file read |
| Delete CAPTCHA | O(1) | Excellent - single file delete |
| List Expired | O(n) | Fair - full directory scan required |
| Pick from Pool | O(n) | Fair - scan until valid found |

### Bottlenecks

1. **Directory Listing**: Large number of files slows `listdir()`
   - Solution: Partition into subdirectories by date/hash prefix
   
2. **File System Limits**: Some file systems slow with 100k+ files
   - Solution: Use cloud storage (S3, Azure) which handles this
   
3. **Cleanup Operations**: Scanning all files is I/O intensive
   - Solution: Run as background task, not in request path

### Optimization Strategies

**Strategy 1: Date-based Partitioning**
```
captcha_store/
├── 2025-05-25/
│   ├── a1b2c3d4e5f6...json
│   └── ...
└── 2025-05-26/
    ├── f6e5d4c3b2a1...json
    └── ...
```
Reduces file count per directory, improves cleanup speed.

**Strategy 2: Hash Prefix Partitioning**
```
captcha_store/
├── a/
│   ├── a1b2c3d4e5f6...json
│   └── ...
└── f/
    ├── f6e5d4c3b2a1...json
    └── ...
```
Distributes evenly, helpful for file system limits.

**Strategy 3: Cloud Storage**
- Delegate to S3/Azure for directory operations
- Automatic distribution across storage nodes
- Built-in replication and availability

---

## Backward Compatibility

### CaptchaStore Model Wrapper

The `captcha/models.py` module provides a **non-database model** that wraps `FileSystemCaptchaStore`:

```python
class CaptchaStore:
    """Maintains original API, delegates to FileSystemCaptchaStore"""
    
    @classmethod
    def generate_key(cls, generator=None):
        return FileSystemCaptchaStore.generate_key(generator)
    
    @classmethod
    def pick(cls):
        return FileSystemCaptchaStore.pick()
```

**Compatibility:**
- Existing code using `CaptchaStore.generate_key()` still works
- Old database code (if any) must be manually migrated
- Forms and fields require no changes

---

## Deployment Scenarios

### Scenario 1: Single Server
```
Server A:
├── Application
├── Django
├── MEDIA_ROOT → /var/media/captcha_store/
└── File storage (local filesystem)
```
Simple, works out of the box.

### Scenario 2: Load Balanced (Shared Storage)
```
Server A ──┐
           ├─→ NFS Mount (Shared)
Server B ──┤   └── /mnt/shared/captcha_store/
           │
Server C ──┘
```
All servers read/write same files. Requires NFS/network file system.

### Scenario 3: Cloud Deployment (Recommended)
```
Server A ──┐
           ├─→ S3 Bucket
Server B ──┤   └── s3://my-bucket/captcha_store/
           │
Server C ──┘
```
Fully managed, no infrastructure overhead, best scalability.

---

## Testing Considerations

### Test Mode

```python
# settings.py (development only!)
CAPTCHA_TEST_MODE = True
```

Any form submission with answer `"passed"` automatically validates. Useful for:
- Automated testing
- Manual testing without solving CAPTCHAs
- CI/CD pipelines

### Mocking Storage

```python
from unittest.mock import patch

with patch('captcha.storage.FileSystemCaptchaStore.get') as mock_get:
    mock_get.return_value = {
        'challenge': 'abc123',
        'response': 'abc123',
        'expiration': '2025-12-31T00:00:00Z'
    }
    # Test code
```

### Storage Cleanup in Tests

```python
# Ensure clean state
@pytest.fixture
def clean_captcha_storage():
    FileSystemCaptchaStore.remove_expired()
    yield
    FileSystemCaptchaStore.remove_expired()
```

---

## Migration from Database Backend

### Step 1: Enable File Storage
```python
# settings.py
CAPTCHA_STORAGE_BACKEND = 'captcha.storage.FileSystemCaptchaStore'
```

### Step 2: Create Storage Directory
```bash
mkdir -p media/captcha_store
chmod 700 media/captcha_store
```

### Step 3: No Data Migration Needed
- Old CAPTCHAs in database are abandoned
- File storage is independent
- No downtime required

### Step 4: Optional: Pre-populate Pool
```bash
python manage.py shell
>>> from captcha.models import CaptchaStore
>>> CaptchaStore.create_pool(5000)  # Generate 5000 CAPTCHAs
```

---

## Troubleshooting

### Issue: CAPTCHA Images Not Displaying

**Cause:** File not found / permissions issue
```bash
# Check storage directory exists
ls -la media/captcha_store/

# Check file permissions
chmod 644 media/captcha_store/*.json

# Check file exists
find media/captcha_store/ -name "*.json" | head
```

### Issue: HTTP 410 Gone Errors

**Cause:** CAPTCHA expired
```python
# Reduce timeout
CAPTCHA_TIMEOUT = 600  # 10 minutes instead of 5

# Or increase pool timeout
CAPTCHA_GET_FROM_POOL_TIMEOUT = 300
```

### Issue: Storage Full / Performance Degradation

**Cause:** Too many expired files accumulating
```bash
# Manual cleanup
python manage.py shell
>>> from captcha.storage import FileSystemCaptchaStore
>>> FileSystemCaptchaStore.remove_expired()

# Or schedule periodic cleanup (recommended)
# Use Celery beat or Django-APScheduler
```

---

## Summary

The **file storage backend** in the `feature/file-storage-backend` branch provides:

✅ **Scalability**: Works with cloud storage (S3, Azure)  
✅ **Performance**: Direct file I/O, no database queries  
✅ **Flexibility**: Pluggable storage backends  
✅ **Compatibility**: Drop-in replacement for database model  
✅ **Security**: SHA1 hashing, single-use, expiration  
✅ **Simplicity**: JSON-based format, easy to inspect/debug  

This architecture makes django-captcha suitable for high-traffic applications, distributed systems, and modern cloud deployments.
