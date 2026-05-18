"""智能旅行手账服务层"""
from .exif_service import EXIFService
from .vision_service import VisionService
from .location_service import LocationService
from .text_service import TextService, TextStyle, Mood, Season, TextGenerationResult, TextGenerationError, text_service

from .scene_classifier import (
    SceneClassifier,
    SceneType,
    EmotionalTone,
    SceneClassificationResult,
    SceneClassificationError,
    scene_classifier
)

from .region_inferrer import (
    RegionInferrer,
    Region,
    SceneryType,
    RegionInferralResult,
    RegionInferralError,
    region_inferrer
)

from .export_service import (
    ExportService,
    ExportFormat,
    ExportResult,
    TravelEntry,
    ExportError,
    export_service
)


__all__ = [
    'EXIFService',
    'VisionService',
    'LocationService',
    'TextService',
    'TextStyle',
    'Mood',
    'Season',
    'TextGenerationResult',
    'TextGenerationError',
    'text_service',
    
    'SceneClassifier',
    'SceneType',
    'EmotionalTone',
    'SceneClassificationResult',
    'SceneClassificationError',
    'scene_classifier',
    
    'RegionInferrer',
    'Region',
    'SceneryType',
    'RegionInferralResult',
    'RegionInferralError',
    'region_inferrer',
    
    'ExportService',
    'ExportFormat',
    'ExportResult',
    'TravelEntry',
    'ExportError',
    'export_service'
]


def get_all_services():
    """获取所有服务实例"""
    return {
        'exif_service': EXIFService(),
        'vision_service': VisionService(),
        'location_service': LocationService(),
        'text_service': text_service,
        'scene_classifier': scene_classifier,
        'region_inferrer': region_inferrer,
        'export_service': export_service
    }
