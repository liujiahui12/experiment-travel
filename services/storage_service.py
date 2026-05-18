import json
import os
import threading
from typing import List, Dict, Optional, Any
from datetime import datetime
import shutil


class StorageService:
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self.journals_file = os.path.join(data_dir, 'journals.json')
        self.backup_dir = os.path.join(data_dir, 'journals_backup')
        self.lock = threading.Lock()
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        if not os.path.exists(self.journals_file):
            self._write_data([])
    
    def _read_data(self) -> List[Dict]:
        try:
            with open(self.journals_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _write_data(self, data: List[Dict]) -> None:
        with open(self.journals_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _create_backup(self) -> None:
        if os.path.exists(self.journals_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f'journals_{timestamp}.json')
            shutil.copy2(self.journals_file, backup_file)
            
            backups = sorted([f for f in os.listdir(self.backup_dir) if f.startswith('journals_')])
            while len(backups) > 10:
                os.remove(os.path.join(self.backup_dir, backups[0]))
                backups = backups[1:]
    
    def save_journal(self, journal: Dict) -> str:
        with self.lock:
            self._create_backup()
            
            data = self._read_data()
            
            journal_id = f"journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
            journal['id'] = journal_id
            journal['created_at'] = datetime.now().isoformat()
            journal['updated_at'] = datetime.now().isoformat()
            
            data.append(journal)
            self._write_data(data)
            
            return journal_id
    
    def get_all_journals(self, page: int = 1, per_page: int = 20) -> Dict:
        with self.lock:
            data = self._read_data()
            
            sorted_data = sorted(data, key=lambda x: x.get('created_at', ''), reverse=True)
            
            total = len(sorted_data)
            start = (page - 1) * per_page
            end = start + per_page
            items = sorted_data[start:end]
            
            return {
                'items': items,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
    
    def get_journal_by_id(self, journal_id: str) -> Optional[Dict]:
        with self.lock:
            data = self._read_data()
            
            for journal in data:
                if journal.get('id') == journal_id:
                    return journal
            
            return None
    
    def delete_journal(self, journal_id: str) -> bool:
        with self.lock:
            self._create_backup()
            
            data = self._read_data()
            
            for i, journal in enumerate(data):
                if journal.get('id') == journal_id:
                    data.pop(i)
                    self._write_data(data)
                    return True
            
            return False
    
    def search_journals(self, location: str = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        with self.lock:
            data = self._read_data()
            
            results = []
            for journal in data:
                match = True
                
                if location:
                    journal_location = journal.get('location', '').lower()
                    if location.lower() not in journal_location:
                        match = False
                
                if start_date or end_date:
                    journal_date = journal.get('capture_date', '')
                    if journal_date:
                        normalized_journal_date = journal_date.replace('年', '-').replace('月', '-').replace('日', '')
                        
                        if start_date:
                            normalized_start = start_date.replace('/', '-')
                            if normalized_journal_date < normalized_start:
                                match = False
                        
                        if end_date:
                            normalized_end = end_date.replace('/', '-')
                            if normalized_journal_date > normalized_end:
                                match = False
                
                if match:
                    results.append(journal)
            
            return sorted(results, key=lambda x: x.get('created_at', ''), reverse=True)
