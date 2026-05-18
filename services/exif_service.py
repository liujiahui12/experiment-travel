from dataclasses import dataclass
from typing import Optional, Tuple
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import datetime


@dataclass
class GPSCoordinate:
    latitude: float
    longitude: float

    def __post_init__(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"纬度超出范围: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"经度超出范围: {self.longitude}")


@dataclass
class EXIFInfo:
    has_gps: bool
    gps_coordinate: Optional[GPSCoordinate]
    capture_time: Optional[datetime.datetime]
    message: str


class EXIFService:
    @staticmethod
    def _get_exif_data(image_path: str) -> dict:
        image = Image.open(image_path)
        exif_data = image._getexif()
        return exif_data if exif_data else {}

    @staticmethod
    def _get_gps_info(exif_data: dict) -> Optional[dict]:
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == "GPSInfo":
                gps_info = {}
                for gps_tag in value.keys():
                    sub_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                    gps_info[sub_tag_name] = value[gps_tag]
                return gps_info
        return None

    @staticmethod
    def _convert_to_degrees(value: Tuple) -> float:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)

    @staticmethod
    def _parse_gps_coordinate(gps_info: dict) -> Optional[GPSCoordinate]:
        try:
            if 'GPSLatitude' not in gps_info or 'GPSLongitude' not in gps_info:
                return None

            lat = EXIFService._convert_to_degrees(gps_info['GPSLatitude'])
            lon = EXIFService._convert_to_degrees(gps_info['GPSLongitude'])

            if gps_info.get('GPSLatitudeRef') == 'S':
                lat = -lat
            if gps_info.get('GPSLongitudeRef') == 'W':
                lon = -lon

            return GPSCoordinate(latitude=lat, longitude=lon)
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _parse_capture_time(exif_data: dict) -> Optional[datetime.datetime]:
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == "DateTimeOriginal":
                try:
                    return datetime.datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    return None
        return None

    @staticmethod
    def parse_exif(image_path: str) -> EXIFInfo:
        try:
            exif_data = EXIFService._get_exif_data(image_path)

            gps_info = EXIFService._get_gps_info(exif_data)
            gps_coordinate = None
            has_gps = False

            if gps_info:
                gps_coordinate = EXIFService._parse_gps_coordinate(gps_info)
                if gps_coordinate:
                    has_gps = True

            capture_time = EXIFService._parse_capture_time(exif_data)

            if has_gps:
                message = "EXIF信息解析成功，包含GPS坐标"
            else:
                message = "EXIF信息解析成功，但未找到GPS坐标"

            return EXIFInfo(
                has_gps=has_gps,
                gps_coordinate=gps_coordinate,
                capture_time=capture_time,
                message=message
            )
        except Exception as e:
            return EXIFInfo(
                has_gps=False,
                gps_coordinate=None,
                capture_time=None,
                message=f"EXIF信息解析失败: {str(e)}"
            )
