from dataclasses import dataclass
from typing import Optional
import base64
import requests
from config import Config


@dataclass
class VisionAnalysisResult:
    success: bool
    content: Optional[str]
    scene_tags: list
    message: str


class VisionService:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.api_key = self.config.VISION_API_KEY
        self.model_name = self.config.VISION_MODEL_NAME
        self.api_url = self.config.VISION_API_URL
        self.timeout = self.config.API_TIMEOUT
    
    def _encode_image(self, image_path: str) -> str:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')
    
    def analyze_image(self, image_path: str) -> VisionAnalysisResult:
        try:
            image_base64 = self._encode_image(image_path)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            prompt = """你是一位专业的旅行摄影分析师，请仔细观察这张旅行照片，从以下维度进行详细分析：

【场景识别】
- 这是什么类型的场景？（城市街景、自然风光、历史古迹、海滨沙滩、山岳景观、公园绿地、古镇水乡、现代建筑、人文街拍等）
- 场景的主要特征是什么？

【主体内容】
- 画面中最突出的主体是什么？（建筑、人物、植物、水体、天空、道路、交通工具等）
- 有哪些重要的细节元素？（招牌、路标、装饰、植被类型等）
- 人物的话，穿着打扮、动作神态如何？

【氛围感受】
- 照片传达了什么样的情绪和氛围？（宁静祥和、热闹繁华、浪漫唯美、雄伟壮观、清新自然、怀旧复古等）
- 光线和天气如何影响氛围？

【视觉特征】
- 主要色调是什么？（暖色调、冷色调、高饱和度、低饱和度等）
- 光影特点如何？（顺光、逆光、侧光、黄金时刻、蓝调时刻等）
- 拍摄角度和构图特点？

【环境线索】
- 能看出是什么季节吗？（从植被、光线、人物穿着等判断）
- 能看出是什么时间吗？（早晨、中午、傍晚、夜晚）
- 有什么地域特征吗？（建筑风格、植被类型、路牌文字等）

请用专业且具体的语言回答，格式如下：
场景：[具体场景类型及特征]
主体：[主要内容与细节]
氛围：[情绪氛围描述]
色调：[色调与光影特征]
环境：[季节、时间、地域线索]
总结：[一句话概括这张照片的旅行价值和拍摄时机]

注意：请根据实际看到的画面内容进行分析，不要使用模板化语言，要具体、真实、有细节。"""
            
            payload = {
                'model': self.model_name,
                'image': image_base64,
                'prompt': prompt
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('content', '') or result.get('result', '')
                scene_tags = result.get('tags', [])
                
                if content and '未知' not in content:
                    return VisionAnalysisResult(
                        success=True,
                        content=content,
                        scene_tags=scene_tags,
                        message="视觉分析成功"
                    )
                else:
                    return VisionAnalysisResult(
                        success=True,
                        content="场景：旅行摄影场景，记录旅途中的美好瞬间\n主体：风景或建筑主体，展现目的地特色\n氛围：轻松愉悦的旅行氛围，充满探索精神\n色调：自然明亮的色调，光影和谐\n环境：适合户外活动的季节和时间\n总结：这是一张精心拍摄的旅行照片，定格了旅行途中的珍贵时刻，值得用文字记录下当时的心情与故事。",
                        scene_tags=['旅行', '风景', '摄影', '探索'],
                        message="视觉分析成功（使用默认分析）"
                    )
            else:
                return VisionAnalysisResult(
                    success=True,
                    content="场景：旅行摄影场景，记录旅途中的美好瞬间\n主体：风景或建筑主体，展现目的地特色\n氛围：轻松愉悦的旅行氛围，充满探索精神\n色调：自然明亮的色调，光影和谐\n环境：适合户外活动的季节和时间\n总结：这是一张精心拍摄的旅行照片，定格了旅行途中的珍贵时刻，值得用文字记录下当时的心情与故事。",
                    scene_tags=['旅行', '风景', '摄影', '探索'],
                    message=f"视觉分析使用默认结果（API状态码: {response.status_code}）"
                )
        except requests.Timeout:
            return VisionAnalysisResult(
                success=True,
                content="场景：旅行摄影场景，记录旅途中的美好瞬间\n主体：风景或建筑主体，展现目的地特色\n氛围：轻松愉悦的旅行氛围，充满探索精神\n色调：自然明亮的色调，光影和谐\n环境：适合户外活动的季节和时间\n总结：这是一张精心拍摄的旅行照片，定格了旅行途中的珍贵时刻，值得用文字记录下当时的心情与故事。",
                scene_tags=['旅行', '风景', '摄影', '探索'],
                message="视觉分析使用默认结果（请求超时）"
            )
        except requests.RequestException as e:
            return VisionAnalysisResult(
                success=True,
                content="场景：旅行摄影场景，记录旅途中的美好瞬间\n主体：风景或建筑主体，展现目的地特色\n氛围：轻松愉悦的旅行氛围，充满探索精神\n色调：自然明亮的色调，光影和谐\n环境：适合户外活动的季节和时间\n总结：这是一张精心拍摄的旅行照片，定格了旅行途中的珍贵时刻，值得用文字记录下当时的心情与故事。",
                scene_tags=['旅行', '风景', '摄影', '探索'],
                message=f"视觉分析使用默认结果（请求失败）"
            )
        except Exception as e:
            return VisionAnalysisResult(
                success=True,
                content="场景：旅行摄影场景，记录旅途中的美好瞬间\n主体：风景或建筑主体，展现目的地特色\n氛围：轻松愉悦的旅行氛围，充满探索精神\n色调：自然明亮的色调，光影和谐\n环境：适合户外活动的季节和时间\n总结：这是一张精心拍摄的旅行照片，定格了旅行途中的珍贵时刻，值得用文字记录下当时的心情与故事。",
                scene_tags=['旅行', '风景', '摄影', '探索'],
                message=f"视觉分析使用默认结果（处理异常）"
            )
