from typing import Dict, List, Optional, Any
from datetime import datetime
from services.storage_service import StorageService
from services.image_storage_service import ImageStorageService


class JournalService:
    def __init__(self):
        self.storage_service = StorageService()
        self.image_storage_service = ImageStorageService()
    
    def save_journal(self, 
                     capture_date: str,
                     location: str,
                     content: str,
                     style: str,
                     images_data: List[Dict],
                     timeline: List[Dict],
                     poi_list: List[Dict] = None,
                     original_images: List[str] = None) -> Dict:
        
        journal = {
            'capture_date': capture_date,
            'location': location,
            'content': content,
            'style': style,
            'images_count': len(images_data) if images_data else 0,
            'timeline': timeline,
            'poi_list': poi_list or [],
            'tags': self._extract_tags(content)
        }
        
        journal_id = self.storage_service.save_journal(journal)
        
        if original_images and len(original_images) > 0:
            preview_path = self.image_storage_service.save_preview(original_images[0], journal_id)
            if preview_path:
                journal['preview_image'] = preview_path
                self.storage_service.storage_service._write_data(
                    self.storage_service._update_journal_field(journal_id, 'preview_image', preview_path)
                )
        
        return {
            'success': True,
            'journal_id': journal_id,
            'message': '日记保存成功'
        }
    
    def _extract_tags(self, content: str) -> List[str]:
        tags = []
        import re
        hashtag_pattern = r'#(\w+)'
        matches = re.findall(hashtag_pattern, content)
        tags.extend(matches[:5])
        return tags
    
    def get_journals(self, page: int = 1, per_page: int = 20) -> Dict:
        result = self.storage_service.get_all_journals(page, per_page)
        
        for item in result['items']:
            if 'content' in item and len(item['content']) > 100:
                item['content_preview'] = item['content'][:100] + '...'
            else:
                item['content_preview'] = item.get('content', '')
        
        return result
    
    def get_journal_detail(self, journal_id: str) -> Dict:
        journal = self.storage_service.get_journal_by_id(journal_id)
        
        if not journal:
            return {
                'success': False,
                'message': '日记不存在'
            }
        
        return {
            'success': True,
            'journal': journal
        }
    
    def delete_journal(self, journal_id: str) -> Dict:
        journal = self.storage_service.get_journal_by_id(journal_id)
        
        if not journal:
            return {
                'success': False,
                'message': '日记不存在'
            }
        
        self.image_storage_service.delete_preview(journal_id)
        
        deleted = self.storage_service.delete_journal(journal_id)
        
        if deleted:
            return {
                'success': True,
                'message': '日记删除成功'
            }
        else:
            return {
                'success': False,
                'message': '日记删除失败'
            }
    
    def search_journals(self, location: str = None, start_date: str = None, end_date: str = None) -> Dict:
        results = self.storage_service.search_journals(location, start_date, end_date)
        
        for item in results:
            if 'content' in item and len(item['content']) > 100:
                item['content_preview'] = item['content'][:100] + '...'
            else:
                item['content_preview'] = item.get('content', '')
        
        return {
            'success': True,
            'results': results,
            'total': len(results)
        }
