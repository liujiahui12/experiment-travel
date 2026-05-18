import os
import shutil
from datetime import datetime
from typing import Optional


class ImageStorageService:
    def __init__(self, preview_dir: str = 'static/journal_previews'):
        self.preview_dir = preview_dir
        
        if not os.path.exists(self.preview_dir):
            os.makedirs(self.preview_dir)
    
    def save_preview(self, source_path: str, journal_id: str) -> Optional[str]:
        try:
            if not os.path.exists(source_path):
                return None
            
            ext = os.path.splitext(source_path)[1]
            preview_filename = f"{journal_id}{ext}"
            preview_path = os.path.join(self.preview_dir, preview_filename)
            
            shutil.copy2(source_path, preview_path)
            
            return preview_path
        except Exception as e:
            print(f"保存图片预览失败: {e}")
            return None
    
    def delete_preview(self, journal_id: str) -> bool:
        try:
            for filename in os.listdir(self.preview_dir):
                if filename.startswith(journal_id):
                    file_path = os.path.join(self.preview_dir, filename)
                    os.remove(file_path)
                    return True
            return False
        except Exception as e:
            print(f"删除图片预览失败: {e}")
            return False
    
    def get_preview_path(self, journal_id: str) -> Optional[str]:
        for filename in os.listdir(self.preview_dir):
            if filename.startswith(journal_id):
                return os.path.join(self.preview_dir, filename)
        return None
