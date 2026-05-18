"""多风格文案生成服务"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List
import hashlib
import time
import re
from datetime import datetime
import requests
from config import Config


class TextStyle(Enum):
    XIAOHONGSHU = "小红书风"
    LITERARY = "文艺治愈风"
    DIARY = "简约日记风"
    MOMENTS = "朋友圈短句风"


class Mood(Enum):
    ROMANTIC = "浪漫"
    HEALING = "治愈"
    LIVELY = "热闹"
    PEACEFUL = "安静"


class Season(Enum):
    SPRING = "春"
    SUMMER = "夏"
    AUTUMN = "秋"
    WINTER = "冬"


@dataclass
class CopyContext:
    image_content: str
    location: str
    capture_time: str
    poi_list: list


@dataclass
class CopyResult:
    success: bool
    content: Optional[str]
    message: str


@dataclass
class TextGenerationResult:
    text: str
    style: TextStyle
    mood: Mood
    season: Season
    tags: List[str]
    polished: bool
    original_text: Optional[str] = None


@dataclass
class StyleConfig:
    emoji_pattern: str
    tone: str
    sentence_length: str
    ending_style: str
    hashtag_count: int


class TextService:
    def __init__(self, config: Config = None, cache_size: int = 256):
        self.config = config or Config()
        self.api_key = self.config.TEXT_API_KEY
        self.model_name = self.config.TEXT_MODEL_NAME
        self.api_url = self.config.TEXT_API_URL
        self.timeout = self.config.API_TIMEOUT
        self.cache = {}
        self.cache_ttl = 7200
        self.max_retries = 3
        self.retry_delay = 1
        
        self.style_configs = self._init_style_configs()
        self.mood_keywords = self._init_mood_keywords()
        self.season_keywords = self._init_season_keywords()
    
    def _init_style_configs(self) -> Dict[TextStyle, StyleConfig]:
        return {
            TextStyle.XIAOHONGSHU: StyleConfig(
                emoji_pattern="🌟✨📸💫",
                tone="活泼、分享、种草",
                sentence_length="中长句",
                ending_style="问句或感叹句",
                hashtag_count=5
            ),
            TextStyle.LITERARY: StyleConfig(
                emoji_pattern="🍃🌸🌙✨",
                tone="温柔、诗意、治愈",
                sentence_length="长句",
                ending_style="省略号或意象",
                hashtag_count=3
            ),
            TextStyle.DIARY: StyleConfig(
                emoji_pattern="📝📍⛅",
                tone="简洁、记录、朴实",
                sentence_length="中句",
                ending_style="陈述句",
                hashtag_count=2
            ),
            TextStyle.MOMENTS: StyleConfig(
                emoji_pattern="💫✨",
                tone="简短、精炼、情感",
                sentence_length="短句",
                ending_style="emoji或符号",
                hashtag_count=1
            )
        }
    
    def _init_mood_keywords(self) -> Dict[Mood, List[str]]:
        return {
            Mood.ROMANTIC: ['浪漫', '温柔', '心动', '夕阳', '牵手', '甜蜜', '玫瑰', '月光'],
            Mood.HEALING: ['治愈', '宁静', '安心', '舒适', '温暖', '阳光', '微风', '绿意'],
            Mood.LIVELY: ['热闹', '欢声笑语', '熙攘', '烟火气', '市井', '繁华', '人来人往'],
            Mood.PEACEFUL: ['安静', '静谧', '祥和', '悠然', '岁月静好', '慢时光', '悠哉']
        }
    
    def _init_season_keywords(self) -> Dict[Season, List[str]]:
        return {
            Season.SPRING: ['春天', '春日', '花开', '樱花', '油菜花', '嫩绿', '踏青', '春游'],
            Season.SUMMER: ['夏天', '夏日', '阳光', '海滩', '西瓜', '蝉鸣', '荷花', '避暑'],
            Season.AUTUMN: ['秋天', '秋日', '枫叶', '银杏', '金黄', '丰收', '秋高气爽', '层林尽染'],
            Season.WINTER: ['冬天', '冬日', '雪', '雪景', '冰雪', '雾凇', '暖阳', '围炉']
        }
    
    def _build_prompt(self, context: CopyContext, style: str = "literary") -> str:
        style_mapping = {
            "xiaohongshu": "xiaohongshu",
            "literary": "literary",
            "simple": "simple",
            "moments": "moments"
        }
        
        mapped_style = style_mapping.get(style, "literary")
        
        style_prompts = {
            "xiaohongshu": {
                "role": "小红书风格的旅行博主",
                "requirements": """请严格按照小红书风格生成文案：
1. 开头用活泼emoji（如✨、📸、💫）
2. 使用活泼、分享、种草的语气
3. 多用感叹号和波浪号表达兴奋
4. 加入"姐妹们""快冲""绝了"等网络用语
5. 文案字数150-250字
6. 结尾添加3-5个热门话题标签""",
                "tone": "活泼生动，充满分享欲和种草感"
            },
            "literary": {
                "role": "文艺治愈风格的旅行写手",
                "requirements": """请严格按照文艺治愈风格生成文案：
1. 开头用诗意emoji（如🍃、🌸、🌙）
2. 使用温柔、诗意、治愈的语气
3. 注重氛围营造和情感表达
4. 适当使用省略号营造意境
5. 文案字数200-300字
6. 结尾添加2-3个文艺话题标签""",
                "tone": "温柔诗意，注重意境和情感共鸣"
            },
            "simple": {
                "role": "简约日记风格的旅行记录者",
                "requirements": """请严格按照简约日记风格生成文案：
1. 开头简洁，用简单emoji（如📍、📝）
2. 使用简洁、客观、记录式的语气
3. 重点记录地点、时间、体验
4. 避免过多修饰和情感表达
5. 文案字数100-200字
6. 结尾添加1-2个话题标签""",
                "tone": "简洁专业，注重信息记录"
            },
            "moments": {
                "role": "朋友圈短句风格的分享者",
                "requirements": """请严格按照朋友圈短句风格生成文案：
1. 文案简短精炼，控制在50-100字
2. 一句话表达心情或感悟
3. 可以用短句+emoji的形式
4. 不需要话题标签
5. 适合朋友圈快速分享""",
                "tone": "短小精悍，一语道尽心情"
            }
        }
        
        style_config = style_prompts.get(mapped_style, style_prompts["literary"])
        
        prompt = f"""你是一位{style_config['role']}，请根据以下信息生成旅行文案：

图片内容分析：{context.image_content}
拍摄地点：{context.location}
拍摄时间：{context.capture_time}
"""
        
        if context.poi_list:
            poi_names = [poi['name'] for poi in context.poi_list[:3]]
            prompt += f"周边热门景点：{', '.join(poi_names)}\n"
        
        prompt += f"""
{style_config['requirements']}

文案基调：{style_config['tone']}

注意：文案要具体、真实，避免模板化，让读者有身临其境的感觉。
"""
        return prompt
    
    def generate_copy(self, context: CopyContext, style: str = "literary") -> CopyResult:
        try:
            prompt = self._build_prompt(context, style)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.8,
                'max_tokens': 800
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                if content:
                    return CopyResult(
                        success=True,
                        content=content,
                        message="文案生成成功"
                    )
                else:
                    return CopyResult(
                        success=False,
                        content=None,
                        message="文案生成失败：返回内容为空"
                    )
            else:
                return CopyResult(
                    success=False,
                    content=None,
                    message=f"文案生成API调用失败，状态码: {response.status_code}"
                )
        except requests.Timeout:
            return CopyResult(
                success=False,
                content=None,
                message="文案生成API请求超时"
            )
        except requests.RequestException as e:
            return CopyResult(
                success=False,
                content=None,
                message=f"文案生成API请求失败: {str(e)}"
            )
        except Exception as e:
            return CopyResult(
                success=False,
                content=None,
                message=f"文案生成失败: {str(e)}"
            )
    
    def generate(
        self,
        scene_info: Dict,
        style: TextStyle = TextStyle.XIAOHONGSHU,
        custom_mood: Optional[Mood] = None,
        custom_text: Optional[str] = None
    ) -> TextGenerationResult:
        cache_key = self._generate_cache_key(scene_info, style, custom_mood)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        for attempt in range(self.max_retries):
            try:
                mood = custom_mood or self._detect_mood(scene_info)
                season = self._detect_season(scene_info)
                
                if custom_text:
                    text = self._polish_text(custom_text, style, mood)
                    polished = True
                    original_text = custom_text
                else:
                    text = self._generate_text(scene_info, style, mood, season)
                    polished = False
                    original_text = None
                
                tags = self._generate_tags(scene_info, style, mood, season)
                
                result = TextGenerationResult(
                    text=text,
                    style=style,
                    mood=mood,
                    season=season,
                    tags=tags,
                    polished=polished,
                    original_text=original_text
                )
                
                self._save_to_cache(cache_key, result)
                return result
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise TextGenerationError(f"文案生成失败: {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))
        
        raise TextGenerationError("文案生成失败: 超过最大重试次数")
    
    def polish(self, text: str, style: TextStyle = TextStyle.XIAOHONGSHU) -> str:
        try:
            polished = self._polish_text(text, style, Mood.HEALING)
            return polished
        except Exception as e:
            raise TextGenerationError(f"文案润色失败: {str(e)}")
    
    def _detect_mood(self, scene_info: Dict) -> Mood:
        text = str(scene_info.get('description', '')) + str(scene_info.get('keywords', []))
        text_lower = text.lower()
        
        mood_scores = {}
        for mood, keywords in self.mood_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            mood_scores[mood] = score
        
        if max(mood_scores.values()) > 0:
            return max(mood_scores, key=mood_scores.get)
        
        scene_type = scene_info.get('scene_type', '').lower()
        if '海' in scene_type or '浪漫' in text_lower:
            return Mood.ROMANTIC
        if '山' in scene_type or '自然' in scene_type:
            return Mood.HEALING
        if '城市' in scene_type or '街' in scene_type:
            return Mood.LIVELY
        if '古镇' in scene_type or '建筑' in scene_type:
            return Mood.PEACEFUL
        
        return Mood.HEALING
    
    def _detect_season(self, scene_info: Dict) -> Season:
        text = str(scene_info.get('description', '')) + str(scene_info.get('keywords', []))
        text_lower = text.lower()
        
        season_scores = {}
        for season, keywords in self.season_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            season_scores[season] = score
        
        if max(season_scores.values()) > 0:
            return max(season_scores, key=season_scores.get)
        
        current_month = datetime.now().month
        if 3 <= current_month <= 5:
            return Season.SPRING
        elif 6 <= current_month <= 8:
            return Season.SUMMER
        elif 9 <= current_month <= 11:
            return Season.AUTUMN
        else:
            return Season.WINTER
    
    def _generate_text(
        self,
        scene_info: Dict,
        style: TextStyle,
        mood: Mood,
        season: Season
    ) -> str:
        location = scene_info.get('location', '这里')
        description = scene_info.get('description', '')
        keywords = scene_info.get('keywords', [])
        
        config = self.style_configs[style]
        
        templates = {
            TextStyle.XIAOHONGSHU: self._generate_xiaohongshu,
            TextStyle.LITERARY: self._generate_literary,
            TextStyle.DIARY: self._generate_diary,
            TextStyle.MOMENTS: self._generate_moments
        }
        
        generator = templates.get(style, self._generate_xiaohongshu)
        return generator(location, description, keywords, mood, season, config)
    
    def _generate_xiaohongshu(
        self,
        location: str,
        description: str,
        keywords: List[str],
        mood: Mood,
        season: Season,
        config: StyleConfig
    ) -> str:
        emoji = config.emoji_pattern[:2]
        keyword = keywords[0] if keywords else '美好'
        
        templates = [
            f"{emoji} {location}的{keyword}真的太绝了！\n\n每次来都有新发现，{mood.value}的氛围感拉满～\n\n📸 姐妹们快冲！",
            f"{emoji} 终于打卡了{location}！\n\n{season.value}日的{keyword}，{mood.value}指数满分💯\n\n值得N刷的地方～",
            f"{emoji} 在{location}发现宝藏地！\n\n{keyword}的氛围感绝了，{mood.value}到不行～\n\n姐妹们记得收藏！"
        ]
        
        import random
        return random.choice(templates)
    
    def _generate_literary(
        self,
        location: str,
        description: str,
        keywords: List[str],
        mood: Mood,
        season: Season,
        config: StyleConfig
    ) -> str:
        emoji = config.emoji_pattern[0]
        keyword = keywords[0] if keywords else '时光'
        
        templates = [
            f"{emoji} 在{location}，遇见了{season.value}日里最{mood.value}的{keyword}。\n\n时光慢下来，心也跟着静下来...",
            f"{emoji} {location}的{keyword}，藏着{mood.value}的秘密。\n\n{season.value}风轻拂，一切刚刚好...",
            f"{emoji} 于{location}，邂逅{keyword}。\n\n{mood.value}的{season.value}日，值得被铭记..."
        ]
        
        import random
        return random.choice(templates)
    
    def _generate_diary(
        self,
        location: str,
        description: str,
        keywords: List[str],
        mood: Mood,
        season: Season,
        config: StyleConfig
    ) -> str:
        emoji = config.emoji_pattern[0]
        keyword = keywords[0] if keywords else '风景'
        
        date_str = datetime.now().strftime('%m月%d日')
        
        templates = [
            f"{emoji} {date_str} · {location}\n\n{season.value}日出行，{keyword}很美。心情{mood.value}。",
            f"{emoji} {date_str}\n\n地点：{location}\n天气：晴\n心情：{mood.value}\n\n{keyword}值得一去。",
            f"{emoji} {date_str} 打卡{location}\n\n{season.value}日{keyword}，{mood.value}的一天。"
        ]
        
        import random
        return random.choice(templates)
    
    def _generate_moments(
        self,
        location: str,
        description: str,
        keywords: List[str],
        mood: Mood,
        season: Season,
        config: StyleConfig
    ) -> str:
        emoji = config.emoji_pattern[0]
        keyword = keywords[0] if keywords else '风景'
        
        templates = [
            f"{location}的{keyword}，{mood.value}～{emoji}",
            f"{season.value}日{location}，{mood.value}的一天✨",
            f"{keyword}打卡，{mood.value}{emoji}"
        ]
        
        import random
        return random.choice(templates)
    
    def _polish_text(self, text: str, style: TextStyle, mood: Mood) -> str:
        text = text.strip()
        
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'。{2,}', '。', text)
        text = re.sub(r'！{2,}', '！', text)
        text = re.sub(r'？{2,}', '？', text)
        
        common_errors = {
            '的地得': {'美丽的景色': '美丽的景色', '开心得笑': '开心地笑'},
            '在再': {'在见': '再见', '再一次': '再一次'}
        }
        
        config = self.style_configs[style]
        if style == TextStyle.XIAOHONGSHU:
            if not text.endswith(('！', '？', '~', '～')):
                text = text.rstrip('。') + '～'
        elif style == TextStyle.LITERARY:
            if not text.endswith(('...', '…', '。')):
                text = text.rstrip() + '...'
        elif style == TextStyle.MOMENTS:
            if not any(emoji in text for emoji in ['✨', '💫', '🌟', '💫']):
                text = text.rstrip() + ' ✨'
        
        return text
    
    def _generate_tags(
        self,
        scene_info: Dict,
        style: TextStyle,
        mood: Mood,
        season: Season
    ) -> List[str]:
        config = self.style_configs[style]
        tags = []
        
        location = scene_info.get('location', '')
        if location:
            tags.append(f"#{location}")
        
        tags.append(f"#{mood.value}")
        tags.append(f"#{season.value}日旅行")
        
        keywords = scene_info.get('keywords', [])
        for kw in keywords[:2]:
            tags.append(f"#{kw}")
        
        if style == TextStyle.XIAOHONGSHU:
            tags.extend(['#旅行打卡', '#宝藏地点'])
        
        return tags[:config.hashtag_count + 2]
    
    def _generate_cache_key(self, scene_info: Dict, style: TextStyle, mood: Optional[Mood]) -> str:
        key_str = f"{str(scene_info)}_{style.value}_{mood.value if mood else 'auto'}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[TextGenerationResult]:
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            del self.cache[key]
        return None
    
    def _save_to_cache(self, key: str, result: TextGenerationResult):
        self.cache[key] = (result, time.time())


class TextGenerationError(Exception):
    pass


text_service = TextService()
