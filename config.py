import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-placeholder')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    
    VISION_API_KEY = os.environ.get('VISION_API_KEY', 'YOUR_VISION_API_KEY_PLACEHOLDER')
    VISION_MODEL_NAME = os.environ.get('VISION_MODEL_NAME', 'Qwen2.5-VL-72B')
    VISION_API_URL = os.environ.get('VISION_API_URL', 'https://maas-api-placeholder.com/v1/vision')
    
    TEXT_API_KEY = os.environ.get('TEXT_API_KEY', 'YOUR_TEXT_API_KEY_PLACEHOLDER')
    TEXT_MODEL_NAME = os.environ.get('TEXT_MODEL_NAME', 'DeepSeekV3.2')
    TEXT_API_URL = os.environ.get('TEXT_API_URL', 'https://maas-api-placeholder.com/v1/text')
    
    BAIDU_MAP_AK = os.environ.get('BAIDU_MAP_AK', 'YOUR_BAIDU_MAP_AK_PLACEHOLDER')
    BAIDU_GEOCODING_URL = os.environ.get('BAIDU_GEOCODING_URL', 'https://api.map.baidu.com/reverse_geocoding/v3/')
    BAIDU_POI_URL = os.environ.get('BAIDU_POI_URL', 'https://api.map.baidu.com/place/v2/search')
    
    API_TIMEOUT = 30
    MAX_PROCESSING_TIME = 60
    MAX_RETRIES = 3
    
    CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_TTL = int(os.environ.get('CACHE_TTL', 3600))
    
    EXPORT_DIR = os.environ.get('EXPORT_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports'))
