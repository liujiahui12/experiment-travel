"""导出服务"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List, Union
from datetime import datetime
import os
import json


class ExportFormat(Enum):
    TXT = "txt"
    MARKDOWN = "md"
    JSON = "json"


@dataclass
class TravelEntry:
    date: datetime
    location: str
    images: List[str]
    text: str
    tags: List[str]
    mood: Optional[str] = None
    weather: Optional[str] = None


@dataclass
class ExportResult:
    success: bool
    file_path: str
    format: ExportFormat
    entries_count: int
    message: str
    error: Optional[str] = None


class ExportService:
    def __init__(self, output_dir: str = None):
        from config import Config
        self.output_dir = output_dir or Config.EXPORT_DIR or "exports"
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
    
    def export_txt(
        self,
        entries: List[TravelEntry],
        filename: str = None,
        include_images: bool = True
    ) -> ExportResult:
        try:
            if not entries:
                return ExportResult(
                    success=False,
                    file_path="",
                    format=ExportFormat.TXT,
                    entries_count=0,
                    message="导出失败: 没有可导出的内容",
                    error="entries为空"
                )
            
            filename = filename or self._generate_filename("txt")
            file_path = os.path.join(self.output_dir, filename)
            
            content = self._format_txt_content(entries, include_images)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return ExportResult(
                success=True,
                file_path=file_path,
                format=ExportFormat.TXT,
                entries_count=len(entries),
                message=f"成功导出{len(entries)}条旅行记录"
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                file_path="",
                format=ExportFormat.TXT,
                entries_count=0,
                message="导出失败",
                error=str(e)
            )
    
    def export_markdown(
        self,
        entries: List[TravelEntry],
        filename: str = None,
        include_timeline: bool = True
    ) -> ExportResult:
        try:
            if not entries:
                return ExportResult(
                    success=False,
                    file_path="",
                    format=ExportFormat.MARKDOWN,
                    entries_count=0,
                    message="导出失败: 没有可导出的内容",
                    error="entries为空"
                )
            
            filename = filename or self._generate_filename("md")
            file_path = os.path.join(self.output_dir, filename)
            
            content = self._format_markdown_content(entries, include_timeline)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return ExportResult(
                success=True,
                file_path=file_path,
                format=ExportFormat.MARKDOWN,
                entries_count=len(entries),
                message=f"成功导出{len(entries)}条旅行记录"
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                file_path="",
                format=ExportFormat.MARKDOWN,
                entries_count=0,
                message="导出失败",
                error=str(e)
            )
    
    def export_timeline_diary(
        self,
        entries: List[TravelEntry],
        filename: str = None,
        title: str = "我的旅行手账"
    ) -> ExportResult:
        try:
            if not entries:
                return ExportResult(
                    success=False,
                    file_path="",
                    format=ExportFormat.MARKDOWN,
                    entries_count=0,
                    message="导出失败: 没有可导出的内容",
                    error="entries为空"
                )
            
            sorted_entries = sorted(entries, key=lambda x: x.date)
            
            filename = filename or self._generate_filename("md", prefix="timeline")
            file_path = os.path.join(self.output_dir, filename)
            
            content = self._format_timeline_content(sorted_entries, title)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return ExportResult(
                success=True,
                file_path=file_path,
                format=ExportFormat.MARKDOWN,
                entries_count=len(entries),
                message=f"成功导出时间轴日记，共{len(entries)}天"
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                file_path="",
                format=ExportFormat.MARKDOWN,
                entries_count=0,
                message="导出失败",
                error=str(e)
            )
    
    def _format_txt_content(self, entries: List[TravelEntry], include_images: bool) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("旅行手账")
        lines.append("=" * 60)
        lines.append("")
        
        for entry in entries:
            lines.append(f"日期: {entry.date.strftime('%Y年%m月%d日')}")
            lines.append(f"地点: {entry.location}")
            
            if entry.weather:
                lines.append(f"天气: {entry.weather}")
            if entry.mood:
                lines.append(f"心情: {entry.mood}")
            
            lines.append("")
            lines.append(entry.text)
            
            if include_images and entry.images:
                lines.append("")
                lines.append("照片:")
                for img in entry.images:
                    lines.append(f"  - {img}")
            
            if entry.tags:
                lines.append("")
                lines.append(f"标签: {', '.join(entry.tags)}")
            
            lines.append("")
            lines.append("-" * 60)
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_markdown_content(self, entries: List[TravelEntry], include_timeline: bool) -> str:
        lines = []
        lines.append("# 旅行手账\n")
        lines.append(f"> 记录美好旅程，共{len(entries)}天\n")
        
        if include_timeline:
            lines.append("\n## 时间轴概览\n")
            for entry in entries:
                date_str = entry.date.strftime('%m-%d')
                lines.append(f"- **{date_str}** - {entry.location}")
        
        lines.append("\n---\n")
        
        for entry in entries:
            lines.append(f"\n## {entry.date.strftime('%Y年%m月%d日')} · {entry.location}\n")
            
            metadata = []
            if entry.weather:
                metadata.append(f"🌤️ {entry.weather}")
            if entry.mood:
                metadata.append(f"😊 {entry.mood}")
            
            if metadata:
                lines.append(f"\n*{' | '.join(metadata)}*\n")
            
            lines.append(f"\n{entry.text}\n")
            
            if entry.images:
                lines.append("\n### 照片记录\n")
                for i, img in enumerate(entry.images, 1):
                    lines.append(f"![照片{i}]({img})")
            
            if entry.tags:
                lines.append(f"\n**标签:** {' '.join([f'`{tag}`' for tag in entry.tags])}\n")
            
            lines.append("\n---\n")
        
        lines.append(f"\n\n---\n\n*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
        
        return "".join(lines)
    
    def _format_timeline_content(self, entries: List[TravelEntry], title: str) -> str:
        lines = []
        lines.append(f"# {title}\n")
        
        start_date = entries[0].date.strftime('%Y年%m月%d日')
        end_date = entries[-1].date.strftime('%Y年%m月%d日')
        days = (entries[-1].date - entries[0].date).days + 1
        
        lines.append(f"\n> {start_date} ~ {end_date} | 共{days}天 | {len(entries)}个地点\n")
        lines.append("\n---\n")
        
        lines.append("\n## 旅行时间轴\n")
        
        for i, entry in enumerate(entries, 1):
            date_str = entry.date.strftime('%m月%d日')
            day_num = (entry.date - entries[0].date).days + 1
            
            lines.append(f"\n### 📍 第{day_num}天 · {date_str} · {entry.location}\n")
            
            if entry.weather or entry.mood:
                meta_info = []
                if entry.weather:
                    meta_info.append(f"天气: {entry.weather}")
                if entry.mood:
                    meta_info.append(f"心情: {entry.mood}")
                lines.append(f"\n*{', '.join(meta_info)}*\n")
            
            lines.append(f"\n{entry.text}\n")
            
            if entry.images:
                lines.append(f"\n📷 **{len(entry.images)}张照片**\n")
            
            if entry.tags:
                lines.append(f"\n🏷️ {' '.join([f'`{tag}`' for tag in entry.tags])}\n")
            
            if i < len(entries):
                lines.append("\n⬇️\n")
        
        lines.append("\n---\n")
        lines.append("\n## 旅行足迹\n")
        lines.append(f"\n**途经地点:** {' → '.join([e.location for e in entries])}\n")
        
        all_tags = set()
        for entry in entries:
            all_tags.update(entry.tags)
        
        if all_tags:
            lines.append(f"\n**所有标签:** {' '.join([f'`{tag}`' for tag in sorted(all_tags)])}\n")
        
        lines.append(f"\n\n---\n\n*记录于 {datetime.now().strftime('%Y年%m月%d日 %H:%M')}*\n")
        
        return "".join(lines)
    
    def _generate_filename(self, ext: str, prefix: str = "travel") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{ext}"
    
    def export_batch(
        self,
        entries: List[TravelEntry],
        formats: List[ExportFormat] = None
    ) -> List[ExportResult]:
        if formats is None:
            formats = [ExportFormat.TXT, ExportFormat.MARKDOWN]
        
        results = []
        
        for fmt in formats:
            if fmt == ExportFormat.TXT:
                result = self.export_txt(entries)
            elif fmt == ExportFormat.MARKDOWN:
                result = self.export_markdown(entries)
            else:
                result = ExportResult(
                    success=False,
                    file_path="",
                    format=fmt,
                    entries_count=0,
                    message="不支持的导出格式",
                    error=f"Unknown format: {fmt}"
                )
            
            results.append(result)
        
        return results


class ExportError(Exception):
    pass


export_service = ExportService()
