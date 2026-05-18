"""无GPS图片地域推断服务"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List, Tuple
import hashlib
import time
from functools import lru_cache


class Region(Enum):
    JIANGNAN = "江南"
    XIBEI = "西北"
    QINGZANG = "青藏"
    DONGBEI = "东北"
    XINAN = "西南"


class SceneryType(Enum):
    MOUNTAIN = "山地"
    WATER = "水域"
    DESERT = "沙漠"
    GRASSLAND = "草原"
    SNOW = "雪景"
    FOREST = "森林"
    ANCIENT = "古迹"


@dataclass
class RegionInferralResult:
    region: Region
    confidence: float
    scenery_type: SceneryType
    characteristics: List[str]
    recommended_keywords: List[str]
    cultural_notes: str


@dataclass
class RegionFeatures:
    vegetation_type: str
    building_style: str
    water_features: bool
    mountain_features: bool
    snow_features: bool
    color_temperature: str
    landscape_type: str
    cultural_elements: List[str]


class RegionInferrer:
    def __init__(self, api_key: str = None, cache_size: int = 128):
        from config import Config
        self.api_key = api_key or Config.VISION_API_KEY
        self.cache = {}
        self.cache_ttl = 3600
        self.max_retries = 3
        self.retry_delay = 1
        
        self.region_patterns = self._init_region_patterns()
    
    def _init_region_patterns(self) -> Dict[Region, Dict]:
        return {
            Region.JIANGNAN: {
                'vegetation': ['竹林', '茶园', '油菜花', '莲荷'],
                'building': ['白墙黛瓦', '马头墙', '小桥流水', '粉墙黛瓦'],
                'landscape': ['水乡', '古镇', '园林', '湿地'],
                'colors': ['青灰', '粉白', '黛绿'],
                'keywords': ['烟雨', '江南', '水乡', '诗意', '温婉'],
                'culture': '温婉细腻的江南水乡文化，诗画江南的独特韵味'
            },
            Region.XIBEI: {
                'vegetation': ['胡杨', '戈壁植被', '沙生植物'],
                'building': ['土坯房', '窑洞', '伊斯兰风格'],
                'landscape': ['沙漠', '戈壁', '丹霞', '雅丹'],
                'colors': ['土黄', '赭红', '苍茫'],
                'keywords': ['苍凉', '壮阔', '丝路', '边塞', '戈壁'],
                'culture': '丝路古道的历史沧桑，苍茫大漠的壮美风光'
            },
            Region.QINGZANG: {
                'vegetation': ['高原草甸', '雪莲', '格桑花'],
                'building': ['藏式建筑', '白塔', '经幡'],
                'landscape': ['雪山', '高原', '圣湖', '冰川'],
                'colors': ['雪白', '天蓝', '金黄'],
                'keywords': ['圣洁', '纯净', '高原', '雪山', '信仰'],
                'culture': '神圣纯净的高原净土，信仰与自然的完美融合'
            },
            Region.DONGBEI: {
                'vegetation': ['白桦林', '针叶林', '雪松'],
                'building': ['俄式建筑', '木刻楞', '工业遗址'],
                'landscape': ['雪原', '林海', '冰湖', '雾凇'],
                'colors': ['银白', '深绿', '冰蓝'],
                'keywords': ['北国', '冰雪', '林海', '豪爽', '关东'],
                'culture': '北国风光的壮丽豪迈，冰雪世界的独特魅力'
            },
            Region.XINAN: {
                'vegetation': ['热带雨林', '梯田', '杜鹃花'],
                'building': ['吊脚楼', '竹楼', '民族特色'],
                'landscape': ['喀斯特', '梯田', '峡谷', '溶洞'],
                'colors': ['翠绿', '土红', '多彩'],
                'keywords': ['多彩', '秘境', '民族', '梯田', '风情'],
                'culture': '多民族聚居的多彩秘境，梯田峡谷的壮丽风光'
            }
        }
    
    def infer(self, image_path: str, visual_features: Dict = None) -> RegionInferralResult:
        cache_key = self._generate_cache_key(image_path)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        for attempt in range(self.max_retries):
            try:
                if visual_features is None:
                    visual_features = self._extract_visual_features(image_path)
                
                region_features = self._analyze_region_features(visual_features)
                region = self._determine_region(region_features)
                scenery_type = self._determine_scenery_type(region_features)
                confidence = self._calculate_confidence(region, region_features)
                characteristics = self._extract_characteristics(region)
                keywords = self._get_recommended_keywords(region, scenery_type)
                cultural_notes = self._get_cultural_notes(region)
                
                result = RegionInferralResult(
                    region=region,
                    confidence=confidence,
                    scenery_type=scenery_type,
                    characteristics=characteristics,
                    recommended_keywords=keywords,
                    cultural_notes=cultural_notes
                )
                
                self._save_to_cache(cache_key, result)
                return result
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RegionInferralError(f"地域推断失败: {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))
        
        raise RegionInferralError("地域推断失败: 超过最大重试次数")
    
    def _extract_visual_features(self, image_path: str) -> Dict:
        try:
            from PIL import Image
            import numpy as np
            
            img = Image.open(image_path)
            img_array = np.array(img)
            
            mean_color = img_array.mean(axis=(0, 1))
            
            return {
                'width': img.width,
                'height': img.height,
                'color_mean': mean_color.tolist() if hasattr(mean_color, 'tolist') else [128, 128, 128],
                'brightness': mean_color.mean() if hasattr(mean_color, 'mean') else 128
            }
        except Exception:
            return {
                'width': 800,
                'height': 600,
                'color_mean': [128, 128, 128],
                'brightness': 128
            }
    
    def _analyze_region_features(self, visual_features: Dict) -> RegionFeatures:
        objects = visual_features.get('objects', [])
        colors = visual_features.get('colors', {})
        brightness = visual_features.get('brightness', 128)
        
        vegetation_type = self._detect_vegetation_type(objects, colors)
        building_style = self._detect_building_style(objects)
        
        return RegionFeatures(
            vegetation_type=vegetation_type,
            building_style=building_style,
            water_features='water' in str(objects).lower() or '湖' in str(objects) or '河' in str(objects),
            mountain_features='mountain' in str(objects).lower() or '山' in str(objects),
            snow_features=brightness > 200 or 'snow' in str(objects).lower() or '雪' in str(objects),
            color_temperature='warm' if brightness > 150 else 'cool',
            landscape_type=visual_features.get('landscape', 'general'),
            cultural_elements=visual_features.get('cultural_elements', [])
        )
    
    def _detect_vegetation_type(self, objects: List, colors: Dict) -> str:
        obj_str = str(objects).lower()
        
        if 'bamboo' in obj_str or '竹' in obj_str:
            return '竹林'
        if 'palm' in obj_str or '椰' in obj_str:
            return '热带植物'
        if 'pine' in obj_str or '松' in obj_str:
            return '针叶林'
        if 'flower' in obj_str or '花' in obj_str:
            return '花卉'
        
        return '普通植被'
    
    def _detect_building_style(self, objects: List) -> str:
        obj_str = str(objects).lower()
        
        if 'pagoda' in obj_str or '塔' in obj_str:
            return '古典建筑'
        if 'temple' in obj_str or '寺庙' in obj_str:
            return '宗教建筑'
        if 'ancient' in obj_str or '古镇' in obj_str:
            return '传统建筑'
        if 'modern' in obj_str or '高楼' in obj_str:
            return '现代建筑'
        
        return '一般建筑'
    
    def _determine_region(self, features: RegionFeatures) -> Region:
        if features.snow_features and features.mountain_features:
            return Region.QINGZANG
        
        if features.snow_features:
            return Region.DONGBEI
        
        if features.vegetation_type in ['竹林', '花卉']:
            return Region.JIANGNAN
        
        if features.vegetation_type == '热带植物':
            return Region.XINAN
        
        if features.water_features and not features.mountain_features:
            return Region.JIANGNAN
        
        if features.mountain_features and features.color_temperature == 'warm':
            return Region.XINAN
        
        if features.building_style in ['宗教建筑', '古典建筑']:
            return Region.XIBEI
        
        return Region.JIANGNAN
    
    def _determine_scenery_type(self, features: RegionFeatures) -> SceneryType:
        if features.snow_features:
            return SceneryType.SNOW
        if features.water_features:
            return SceneryType.WATER
        if features.mountain_features:
            return SceneryType.MOUNTAIN
        if 'desert' in features.landscape_type.lower():
            return SceneryType.DESERT
        if 'grass' in features.vegetation_type.lower():
            return SceneryType.GRASSLAND
        
        return SceneryType.MOUNTAIN
    
    def _calculate_confidence(self, region: Region, features: RegionFeatures) -> float:
        base_confidence = 0.5
        pattern = self.region_patterns.get(region, {})
        
        if features.vegetation_type in pattern.get('vegetation', []):
            base_confidence += 0.15
        if features.building_style in pattern.get('building', []):
            base_confidence += 0.15
        if features.water_features and '水' in str(pattern.get('landscape', [])):
            base_confidence += 0.1
        if features.mountain_features and '山' in str(pattern.get('landscape', [])):
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)
    
    def _extract_characteristics(self, region: Region) -> List[str]:
        pattern = self.region_patterns.get(region, {})
        characteristics = []
        
        characteristics.extend(pattern.get('landscape', [])[:2])
        characteristics.extend(pattern.get('colors', [])[:2])
        
        return characteristics[:5]
    
    def _get_recommended_keywords(self, region: Region, scenery_type: SceneryType) -> List[str]:
        pattern = self.region_patterns.get(region, {})
        keywords = pattern.get('keywords', []).copy()
        
        scenery_keywords = {
            SceneryType.SNOW: ['雪景', '冬日'],
            SceneryType.WATER: ['水景', '湖光'],
            SceneryType.MOUNTAIN: ['山色', '峰峦'],
            SceneryType.DESERT: ['大漠', '沙海'],
            SceneryType.GRASSLAND: ['草原', '牧歌']
        }
        
        keywords.extend(scenery_keywords.get(scenery_type, []))
        
        return keywords[:8]
    
    def _get_cultural_notes(self, region: Region) -> str:
        pattern = self.region_patterns.get(region, {})
        return pattern.get('culture', '中国大地的美好风光')
    
    def _generate_cache_key(self, image_path: str) -> str:
        return hashlib.md5(image_path.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[RegionInferralResult]:
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            del self.cache[key]
        return None
    
    def _save_to_cache(self, key: str, result: RegionInferralResult):
        self.cache[key] = (result, time.time())


class RegionInferralError(Exception):
    pass


region_inferrer = RegionInferrer()
