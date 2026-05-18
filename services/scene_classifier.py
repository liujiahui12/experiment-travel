"""视觉场景智能分类服务"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List
import hashlib
import json
from functools import lru_cache
import time


class SceneType(Enum):
    NATURAL = "自然风光"
    SEASIDE = "海边"
    ANCIENT_TOWN = "古镇"
    CITY_STREET = "城市街景"
    ARCHITECTURE = "人文建筑"


class EmotionalTone(Enum):
    ROMANTIC = "浪漫"
    HEALING = "治愈"
    LIVELY = "热闹"
    PEACEFUL = "安静"


@dataclass
class SceneClassificationResult:
    scene_type: SceneType
    confidence: float
    emotional_tone: EmotionalTone
    style_keywords: List[str]
    color_palette: Dict[str, str]
    description: str


@dataclass
class VisualFeatures:
    objects: List[str]
    colors: Dict[str, float]
    brightness: float
    saturation: float
    composition_type: str
    has_people: bool
    has_water: bool
    has_mountain: bool
    has_building: bool
    vegetation_ratio: float


class SceneClassifier:
    def __init__(self, api_key: str = None, cache_size: int = 128):
        from config import Config
        self.api_key = api_key or Config.VISION_API_KEY
        self.cache = {}
        self.cache_ttl = 3600
        self.max_retries = 3
        self.retry_delay = 1
    
    def classify(self, image_path: str, visual_analysis: Dict = None) -> SceneClassificationResult:
        cache_key = self._generate_cache_key(image_path)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        for attempt in range(self.max_retries):
            try:
                if visual_analysis is None:
                    visual_analysis = self._analyze_image(image_path)
                
                features = self._extract_features(visual_analysis)
                scene_type = self._determine_scene_type(features)
                emotional_tone = self._determine_emotional_tone(scene_type, features)
                style_keywords = self._generate_style_keywords(scene_type, features)
                color_palette = self._extract_color_palette(features)
                description = self._generate_description(scene_type, features)
                
                result = SceneClassificationResult(
                    scene_type=scene_type,
                    confidence=features.saturation / 100 if features.saturation > 0 else 0.8,
                    emotional_tone=emotional_tone,
                    style_keywords=style_keywords,
                    color_palette=color_palette,
                    description=description
                )
                
                self._save_to_cache(cache_key, result)
                return result
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise SceneClassificationError(f"场景分类失败: {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))
        
        raise SceneClassificationError("场景分类失败: 超过最大重试次数")
    
    def _analyze_image(self, image_path: str) -> Dict:
        try:
            from PIL import Image
            import numpy as np
            
            img = Image.open(image_path)
            img_array = np.array(img)
            
            return {
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
                'array_shape': img_array.shape,
                'mean_color': img_array.mean(axis=(0, 1)).tolist() if len(img_array.shape) == 3 else [img_array.mean()]
            }
        except Exception as e:
            return {
                'width': 800,
                'height': 600,
                'mode': 'RGB',
                'mean_color': [128, 128, 128]
            }
    
    def _extract_features(self, visual_analysis: Dict) -> VisualFeatures:
        objects = visual_analysis.get('objects', [])
        colors = visual_analysis.get('colors', {'dominant': '#4A90E2', 'secondary': '#7ED321'})
        
        return VisualFeatures(
            objects=objects if isinstance(objects, list) else [],
            colors=colors if isinstance(colors, dict) else {},
            brightness=visual_analysis.get('brightness', 50.0),
            saturation=visual_analysis.get('saturation', 60.0),
            composition_type=visual_analysis.get('composition', 'standard'),
            has_people='person' in str(objects).lower() or '人' in str(objects),
            has_water='water' in str(objects).lower() or '水' in str(objects) or '海' in str(objects),
            has_mountain='mountain' in str(objects).lower() or '山' in str(objects),
            has_building='building' in str(objects).lower() or '建筑' in str(objects),
            vegetation_ratio=visual_analysis.get('vegetation', 0.3)
        )
    
    def _determine_scene_type(self, features: VisualFeatures) -> SceneType:
        if features.has_water and features.saturation > 50:
            return SceneType.SEASIDE
        
        if features.has_mountain and features.vegetation_ratio > 0.4:
            return SceneType.NATURAL
        
        if features.has_building and 'ancient' in str(features.objects).lower():
            return SceneType.ANCIENT_TOWN
        
        if features.has_building and not features.has_mountain:
            return SceneType.CITY_STREET
        
        if features.has_building:
            return SceneType.ARCHITECTURE
        
        if features.vegetation_ratio > 0.5:
            return SceneType.NATURAL
        
        return SceneType.NATURAL
    
    def _determine_emotional_tone(self, scene_type: SceneType, features: VisualFeatures) -> EmotionalTone:
        tone_mapping = {
            SceneType.SEASIDE: EmotionalTone.ROMANTIC,
            SceneType.NATURAL: EmotionalTone.HEALING,
            SceneType.ANCIENT_TOWN: EmotionalTone.PEACEFUL,
            SceneType.CITY_STREET: EmotionalTone.LIVELY,
            SceneType.ARCHITECTURE: EmotionalTone.PEACEFUL
        }
        
        base_tone = tone_mapping.get(scene_type, EmotionalTone.HEALING)
        
        if features.has_people:
            if features.brightness > 60:
                return EmotionalTone.LIVELY
            else:
                return EmotionalTone.ROMANTIC
        
        return base_tone
    
    def _generate_style_keywords(self, scene_type: SceneType, features: VisualFeatures) -> List[str]:
        keyword_mapping = {
            SceneType.NATURAL: ['清新', '自然', '治愈', '宁静', '山野'],
            SceneType.SEASIDE: ['浪漫', '惬意', '海风', '日落', '沙滩'],
            SceneType.ANCIENT_TOWN: ['古韵', '典雅', '岁月', '江南', '水墨'],
            SceneType.CITY_STREET: ['繁华', '烟火', '都市', '霓虹', '街巷'],
            SceneType.ARCHITECTURE: ['庄严', '宏伟', '历史', '匠心', '文化']
        }
        
        keywords = keyword_mapping.get(scene_type, ['旅行', '美好'])
        
        if features.has_water:
            keywords.append('水景')
        if features.has_mountain:
            keywords.append('山色')
        
        return keywords[:6]
    
    def _extract_color_palette(self, features: VisualFeatures) -> Dict[str, str]:
        if features.colors and len(features.colors) > 0:
            return features.colors
        
        palette_mapping = {
            SceneType.NATURAL: {'primary': '#228B22', 'secondary': '#87CEEB', 'accent': '#F5DEB3'},
            SceneType.SEASIDE: {'primary': '#00CED1', 'secondary': '#FFE4B5', 'accent': '#FF6B6B'},
            SceneType.ANCIENT_TOWN: {'primary': '#8B4513', 'secondary': '#D2B48C', 'accent': '#DEB887'},
            SceneType.CITY_STREET: {'primary': '#2F4F4F', 'secondary': '#FFD700', 'accent': '#FF4500'},
            SceneType.ARCHITECTURE: {'primary': '#708090', 'secondary': '#CD853F', 'accent': '#B8860B'}
        }
        
        return palette_mapping.get(SceneType.NATURAL, {'primary': '#4A90E2', 'secondary': '#7ED321'})
    
    def _generate_description(self, scene_type: SceneType, features: VisualFeatures) -> str:
        desc_mapping = {
            SceneType.NATURAL: "大自然的鬼斧神工，山川河流的壮美画卷",
            SceneType.SEASIDE: "海天一色的浪漫，海浪轻抚沙滩的诗意",
            SceneType.ANCIENT_TOWN: "时光凝固的古镇，历史的痕迹在砖瓦间流淌",
            SceneType.CITY_STREET: "城市的烟火气息，繁华街巷的生活味道",
            SceneType.ARCHITECTURE: "人文建筑的庄严，凝固的艺术与历史的对话"
        }
        
        return desc_mapping.get(scene_type, "旅途中美好的风景")
    
    def _generate_cache_key(self, image_path: str) -> str:
        return hashlib.md5(image_path.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[SceneClassificationResult]:
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            del self.cache[key]
        return None
    
    def _save_to_cache(self, key: str, result: SceneClassificationResult):
        self.cache[key] = (result, time.time())


class SceneClassificationError(Exception):
    pass


scene_classifier = SceneClassifier()
