from dataclasses import dataclass
from typing import Optional, List
import requests
from config import Config


@dataclass
class LocationInfo:
    province: str
    city: str
    district: str
    address: str
    message: str


@dataclass
class POIInfo:
    name: str
    address: str
    distance: float
    category: str
    description: str = ""
    best_time: str = ""
    tips: str = ""


class LocationService:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.ak = self.config.BAIDU_MAP_AK
        self.geocoding_url = self.config.BAIDU_GEOCODING_URL
        self.poi_url = self.config.BAIDU_POI_URL
        self.timeout = self.config.API_TIMEOUT

        self.text_api_key = self.config.TEXT_API_KEY
        self.text_model_name = self.config.TEXT_MODEL_NAME
        self.text_api_url = self.config.TEXT_API_URL
        self._ai_description_cache = {}

    def reverse_geocoding(self, latitude: float, longitude: float) -> LocationInfo:
        try:
            params = {
                'ak': self.ak,
                'output': 'json',
                'coordtype': 'wgs84ll',
                'location': f'{latitude},{longitude}'
            }

            response = requests.get(
                self.geocoding_url,
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('status') == 0:
                    address_component = result.get('result', {}).get('addressComponent', {})

                    return LocationInfo(
                        province=address_component.get('province', ''),
                        city=address_component.get('city', ''),
                        district=address_component.get('district', ''),
                        address=result.get('result', {}).get('formatted_address', ''),
                        message="逆地理编码成功"
                    )
                else:
                    return LocationInfo(
                        province='',
                        city='',
                        district='',
                        address='',
                        message=f"逆地理编码失败: {result.get('message', '未知错误')}"
                    )
            else:
                return LocationInfo(
                    province='',
                    city='',
                    district='',
                    address='',
                    message=f"逆地理编码API调用失败，状态码: {response.status_code}"
                )
        except requests.Timeout:
            return LocationInfo(
                province='',
                city='',
                district='',
                address='',
                message="逆地理编码API请求超时"
            )
        except requests.RequestException as e:
            return LocationInfo(
                province='',
                city='',
                district='',
                address='',
                message=f"逆地理编码API请求失败: {str(e)}"
            )
        except Exception as e:
            return LocationInfo(
                province='',
                city='',
                district='',
                address='',
                message=f"逆地理编码失败: {str(e)}"
            )

    def search_poi(self, query: str, latitude: float, longitude: float, radius: int = 3000) -> List[POIInfo]:
        try:
            params = {
                'ak': self.ak,
                'output': 'json',
                'coordtype': 'wgs84ll',
                'query': query,
                'location': f'{latitude},{longitude}',
                'radius': radius,
                'page_size': 10
            }

            response = requests.get(
                self.poi_url,
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('status') == 0:
                    poi_list = []
                    for poi in result.get('results', []):
                        distance = poi.get('distance')
                        if distance is None or distance == 0:
                            poi_location = poi.get('location', {})
                            poi_lat = float(poi_location.get('lat', 0))
                            poi_lng = float(poi_location.get('lng', 0))
                            if poi_lat and poi_lng:
                                distance = self._calculate_distance(latitude, longitude, poi_lat, poi_lng)
                            else:
                                distance = 0

                        poi_name = poi.get('name', '')
                        poi_category = poi.get('category', '')
                        enriched_info = self.enrich_poi_info(poi_name, poi_category)

                        poi_info = POIInfo(
                            name=poi_name,
                            address=poi.get('address', ''),
                            distance=round(distance) if distance else 0,
                            category=poi_category,
                            description=enriched_info.get('description', ''),
                            best_time=enriched_info.get('best_time', ''),
                            tips=enriched_info.get('tips', '')
                        )
                        poi_list.append(poi_info)
                    return poi_list
                else:
                    return []
            else:
                return []
        except Exception:
            return []

    @staticmethod
    def _calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        import math

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        lng1_rad = math.radians(lng1)
        lng2_rad = math.radians(lng2)

        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        r = 6371000
        distance = r * c

        return distance

    def enrich_poi_info(self, poi_name: str, category: str = "") -> dict:
        poi_knowledge = {
            "故宫": {
                "description": "中国明清两代的皇家宫殿，世界上现存规模最大的宫殿建筑群，被誉为世界五大宫之首。占地面积72万平方米，建筑面积约15万平方米，有大小宫殿七十多座，房屋九千余间。",
                "best_time": "3-4小时",
                "tips": "建议从午门进入，沿中轴线参观三大殿，再游览东西六宫。珍宝馆和钟表馆值得一看"},
            "天安门": {
                "description": "中华人民共和国的象征，世界上最大的城市广场之一，南北长880米，东西宽500米，面积达44万平方米。见证了新中国的成立与发展，是全国重点文物保护单位。",
                "best_time": "1-2小时", "tips": "清晨升旗仪式值得观看，广场东西两侧有人民大会堂和国家博物馆"},
            "长城": {
                "description": "中国古代伟大的防御工程，世界文化遗产，被誉为世界七大奇迹之一。始建于春秋战国时期，总长度超过2万公里，现存保存较好的明长城约8851.8公里。",
                "best_time": "半天至1天", "tips": "建议选择八达岭或慕田峪段，穿舒适的运动鞋，带足饮用水"},
            "颐和园": {
                "description": "中国清朝时期皇家园林，以昆明湖、万寿山为基址，占地约290公顷。园内建筑精美，山水相映，是中国古典园林艺术的集大成者，1998年被列入世界遗产名录。",
                "best_time": "3-4小时", "tips": "可乘船游览昆明湖，长廊彩画值得细细品味，十七孔桥是拍照佳地"},
            "西湖": {
                "description": "杭州的标志性景点，以秀丽的湖光山色闻名于世，湖面面积约6.39平方千米。苏东坡曾赞美'欲把西湖比西子，淡妆浓抹总相宜'。2011年列入世界遗产名录。",
                "best_time": "半天至1天", "tips": "推荐苏堤春晓、断桥残雪等十景，可骑行环湖，傍晚看雷峰夕照"},
            "黄山": {
                "description": "中国十大名山之一，世界文化与自然双重遗产，以奇松、怪石、云海、温泉、冬雪'五绝'著称于世。明代旅行家徐霞客赞叹'五岳归来不看山，黄山归来不看岳'。",
                "best_time": "1-2天", "tips": "建议清晨观日出，带好防寒衣物和雨具，西海大峡谷景色壮观"},
            "黄鹤楼": {
                "description": "江南三大名楼之一，享有'天下江山第一楼'的美誉。始建于三国时期，历代屡毁屡建，现楼为1985年重建。楼高5层，总高度51.4米，李白、崔颢等曾在此留下千古诗篇。",
                "best_time": "1-2小时", "tips": "登楼远眺长江美景，品味历代诗人题咏，楼内陈列历代黄鹤楼模型"},
            "兵马俑": {
                "description": "世界第八大奇迹，秦始皇陵的陪葬坑，发现于1974年。三个兵马俑坑呈品字形排列，面积约2万平方米，有兵马俑近8000件，是研究秦代军事、艺术、科技的珍贵资料。",
                "best_time": "2-3小时", "tips": "一号坑规模最大，建议请导游讲解，参观铜车马展厅和环幕影院"},
            "桂林": {
                "description": "桂林山水甲天下，典型的喀斯特地貌景观。漓江风光旖旎，象鼻山、叠彩山、独秀峰等景点星罗棋布。韩愈曾赞叹'江作青罗带，山如碧玉簪'。",
                "best_time": "2-3天", "tips": "漓江竹筏漂流必体验，阳朔西街夜生活丰富，龙脊梯田值得一去"},
            "泰山": {
                "description": "五岳之首，中华民族的精神象征，世界文化与自然双重遗产。海拔1545米，有'天下第一山'之称。孔子曾在此登临，历代帝王在此封禅祭祀。",
                "best_time": "1天", "tips": "夜爬看日出是经典路线，十八盘最陡峭，山顶住宿需提前预订"},
            "陶溪川": {
                "description": "景德镇地标性文创街区，由原宇宙瓷厂改造而成，保留了工业遗址风貌。集陶瓷文化、艺术展览、创意市集、餐饮娱乐于一体，是感受千年瓷都魅力的绝佳去处。",
                "best_time": "2-3小时", "tips": "周末有创意市集，可体验陶瓷DIY，夜景灯光秀值得一看"},
            "御窑博物馆": {
                "description": "国内首家以御窑遗址为主题的博物馆，展示明清御窑厂遗址和大量御窑瓷器珍品。馆内藏品丰富，是了解皇家制瓷工艺和景德镇陶瓷文化的专业场馆。",
                "best_time": "1-2小时", "tips": "展馆设计精美，可了解御窑历史，拍照打卡圣地"},
            "陶阳里": {
                "description": "景德镇陶阳里历史文化旅游区，明清御窑厂遗址所在地。保存有古窑址、古作坊、古建筑等历史遗存，是了解景德镇千年制瓷历史的重要窗口。",
                "best_time": "2-3小时", "tips": "可参观古窑民俗博物馆，体验传统制瓷工艺，感受瓷都文化"},
            "景德镇": {
                "description": "千年瓷都，中国陶瓷文化的代表城市。制瓷历史长达1700余年，以'白如玉、明如镜、薄如纸、声如磬'的瓷器闻名于世。",
                "best_time": "2-3天", "tips": "古窑民俗博览区必游，陶瓷市场可淘宝，体验拉坯制作"},
            "城隍庙": {
                "description": "武汉城隍庙，历史悠久的道教庙宇，供奉城隍神，是武汉传统民俗信仰的重要场所。庙内建筑古朴典雅，香火鼎盛，周边有传统小吃街，是感受武汉民俗文化的好去处。",
                "best_time": "1小时", "tips": "可体验传统祈福文化，周边品尝武汉特色小吃"},
            "武汉大学": {
                "description": "中国最美大学之一，中西合璧的民国建筑群闻名遐迩。珞珈山上绿树成荫，樱花季时繁花似锦，被誉为'中国大学之母'。老图书馆、行政楼等建筑为全国重点文物保护单位。",
                "best_time": "2-3小时", "tips": "樱花季（3月中下旬）最美，需提前预约，建议参观老建筑群和万林艺术博物馆"},
            "宝通禅寺": {
                "description": "武汉历史最悠久的佛教寺院，始建于南朝刘宋时期，距今已有1500余年历史。寺内古木参天，建筑宏伟，是武汉重要的佛教活动中心和文化遗产。",
                "best_time": "1小时", "tips": "可聆听晨钟暮鼓，感受禅意，参观大雄宝殿和藏经楼"},
            "辛亥革命": {
                "description": "纪念辛亥革命的专业博物馆，展示1911年武昌起义的历史过程。馆内珍藏大量革命文物、照片和文献，是了解中国近代史和革命精神的重要教育基地。",
                "best_time": "1-2小时", "tips": "建议请导游讲解或租借语音导览，了解革命先烈事迹，接受爱国主义教育"},
            "起义门": {
                "description": "武昌起义的标志性建筑，辛亥革命首义之地。城门始建于明代，是武昌古城的南门，1911年革命党人由此攻入城内，开启了中国近代民主革命的新篇章。",
                "best_time": "30分钟", "tips": "登城楼俯瞰城市，了解起义历史，周边有首义广场和辛亥革命武昌起义纪念馆"},
            "滕王阁": {
                "description": "江南三大名楼之首，始建于唐代，因王勃《滕王阁序》'落霞与孤鹜齐飞，秋水共长天一色'而名扬天下。阁高57.5米，共9层，登楼可俯瞰赣江美景。",
                "best_time": "1-2小时", "tips": "背诵《滕王阁序》可免门票，傍晚登楼观江景最美，阁内有历代文人墨宝展览"},
            "万寿宫": {
                "description": "南昌万寿宫历史文化街区，原为祭祀许真君的道教宫观，现已改造为集文化、美食、购物于一体的特色街区。保留明清建筑风貌，是南昌城市记忆的重要载体。",
                "best_time": "2-3小时", "tips": "夜晚灯光秀绚丽，品尝南昌特色小吃，参观非遗文化展示"},
            "南昌之星": {
                "description": "世界第三高、中国第一高的摩天轮，高度160米。乘坐摩天轮可360度俯瞰南昌城市全景和赣江风光，是南昌地标性建筑和网红打卡地。",
                "best_time": "30分钟", "tips": "傍晚乘坐可看日落和城市夜景，建议提前购票避开排队高峰"},
            "赣江": {
                "description": "江西省最大河流，纵贯南昌市区，两岸风光旖旎。沿江有秋水广场、音乐喷泉、赣江市民公园等景点，夜晚灯光秀与城市天际线交相辉映。",
                "best_time": "1-2小时", "tips": "夜晚沿江散步最佳，可观看音乐喷泉表演，赣江大桥是拍照佳地"},
            "南昌双子塔": {
                "description": "南昌第一高楼，高度303米，是南昌城市天际线的标志性建筑。观光厅位于60层，可俯瞰南昌全景，体验云端漫步的刺激。",
                "best_time": "1小时", "tips": "傍晚登塔观日落和夜景，透明玻璃观景台挑战胆量，需提前预约购票"},
            "秋水广场": {
                "description": "南昌市地标性市民广场，位于赣江之滨，拥有亚洲最大的音乐喷泉群。喷泉主喷高度达128米，水幕电影与灯光秀结合，每晚定时上演，是南昌市民休闲和游客观光的必到之处。",
                "best_time": "1-2小时",
                "tips": "音乐喷泉每晚19:30和20:30各一场，建议提前20分钟占位，最佳观赏位置在广场中轴线，夜晚灯光秀绚丽"},
            "南昌故郡": {
                "description": "南昌历史文化展示区，再现豫章古郡风貌。区内复原了明清时期的赣派建筑群，青石板巷道、马头墙、天井院落，展示南昌千年城建史和民俗文化，是了解南昌历史底蕴的重要窗口。",
                "best_time": "1-2小时",
                "tips": "适合汉服拍照，周末有民俗表演和非遗展示，可品尝南昌特色小吃，傍晚灯笼亮起更有古韵"},
            "音乐喷泉": {
                "description": "南昌秋水广场音乐喷泉，亚洲最大的喷泉群之一。主喷高度128米，配合灯光音乐表演，水柱随音乐起舞，水幕电影播放南昌城市形象片，是南昌夜景名片和网红打卡地。",
                "best_time": "30-60分钟",
                "tips": "每晚两场（19:30/20:30），建议提前占位，广场中轴线观赏最佳，带三脚架可拍摄精彩瞬间"},
            "市民公园": {
                "description": "赣江畔的大型城市公园，绿树成荫、花团锦簇，是南昌市民日常休闲的首选。园内有健身步道、儿童游乐区、观江平台等设施，清晨和傍晚人流如织，生活气息浓厚。",
                "best_time": "1-2小时", "tips": "清晨晨练或傍晚散步最佳，观江平台看日落很美，周末适合亲子游玩"},
            "云门公园": {
                "description": "景德镇市区综合性公园，依山而建，园内绿树成荫、湖光山色相映。公园中心有云门湖，湖畔设亲水平台、休闲长廊，是市民晨练、散步、亲子游玩的热门去处。春季花开繁茂，秋季桂香四溢。",
                "best_time": "1-2小时",
                "tips": "清晨晨练或傍晚散步最佳，春季赏花、秋季赏桂，湖边长廊是拍照佳地，适合亲子游玩"},
            "抚州弄牌坊": {
                "description": "景德镇历史街区标志建筑，明清古牌坊群保存完好。牌坊上雕刻精美，龙凤呈祥、花鸟鱼虫图案栩栩如生，展现了赣东北传统石雕工艺的精湛技艺。是了解景德镇城市历史与传统建筑文化的重要窗口。",
                "best_time": "30分钟-1小时",
                "tips": "适合古风摄影，清晨或傍晚光线柔和时拍摄最佳，可结合陶溪川文创街区一并游览，感受古今交融的瓷都风貌"},
        }

        for key, info in poi_knowledge.items():
            if key in poi_name:
                return info

        ai_description = self._generate_ai_poi_description(poi_name, category)
        if ai_description:
            return ai_description

        default_info = {
            "description": f"{poi_name}，一处具有地方特色的景点，适合休闲观光和拍照留念。建议根据实际情况合理安排游览时间。",
            "best_time": "1-2小时",
            "tips": "建议提前了解开放时间和门票信息，错峰出行体验更佳"
        }

        return default_info

    def _generate_ai_poi_description(self, poi_name: str, category: str = "") -> dict:
        if poi_name in self._ai_description_cache:
            return self._ai_description_cache[poi_name]

        try:
            prompt = f"""请为景点"{poi_name}"生成详细的旅游介绍信息。

景点类型：{category if category else '旅游景点'}

请以JSON格式返回以下信息：
{{
    "description": "景点详细介绍（80-120字，包含历史背景、特色亮点、文化价值等，语言优美生动）",
    "best_time": "建议游览时长",
    "tips": "实用游览建议（30-50字，具体可行）"
}}

要求：
1. description要具体详细，避免模板化表述，要有地方特色和文化内涵
2. best_time根据景点类型合理估算
3. tips要给出具体实用的建议，如最佳游览路线、拍照点、注意事项等
4. 只返回JSON，不要其他内容"""

            headers = {
                'Authorization': f'Bearer {self.text_api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.text_model_name,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 300
            }

            response = requests.post(
                self.text_api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                if content:
                    import json
                    import re

                    json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                            ai_info = {
                                "description": data.get('description', ''),
                                "best_time": data.get('best_time', '1-2小时'),
                                "tips": data.get('tips', '')
                            }

                            if ai_info['description'] and len(ai_info['description']) > 30:
                                self._ai_description_cache[poi_name] = ai_info
                                return ai_info
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass

        return None
