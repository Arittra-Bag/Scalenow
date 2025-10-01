"""File system organizer for managing knowledge repository files and structure."""

import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import json
import re

from ..models.knowledge_item import KnowledgeItem
from ..models.post_content import ImageData
from ..models.exceptions import StorageError
from ..utils.config import Config
from ..utils.logger import get_logger
from ..utils.validators import URLValidator
from .repository_models import KnowledgeRepository

logger = get_logger(__name__)


class FileOrganizer:
    """Organizer for managing knowledge repository file structure and operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the file organizer."""
        self.config = config or Config.from_env()
        
        # Base paths
        self.base_path = Path(self.config.knowledge_repo_path)
        self.docs_path = self.base_path / "docs"
        self.excels_path = self.base_path / "excels"
        self.infographics_path = self.base_path / "infographics"
        self.backups_path = self.base_path / "backups"
        self.temp_path = self.base_path / "temp"
        
        # Ensure directories exist
        self.create_folder_structure()
        
        logger.info(f"File organizer initialized: {self.base_path}")
    
    def create_folder_structure(self) -> None:
        """Create the complete folder structure for the knowledge repository."""
        try:
            directories = [
                self.base_path,
                self.docs_path,
                self.excels_path,
                self.infographics_path,
                self.backups_path,
                self.temp_path,
                
                # Subdirectories for organization
                self.docs_path / "summaries",
                self.docs_path / "full_reports",
                self.excels_path / "archives",
                self.infographics_path / "by_category",
                self.infographics_path / "by_date",
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {directory}")
            
            # Create category subdirectories for infographics
            from ..models.knowledge_item import Category
            for category in Category:
                category_dir = self.infographics_path / "by_category" / self._sanitize_filename(category.value)
                category_dir.mkdir(exist_ok=True)
            
            logger.info("Folder structure created successfully")
            
        except Exception as e:
            raise StorageError(f"Failed to create folder structure: {e}")
    
    def save_infographic(
        self,
        image_data: ImageData,
        knowledge_item: KnowledgeItem,
        organize_by_category: bool = True
    ) -> str:
        """Save an infographic with proper organization and naming."""
        try:
            # Generate filename
            filename = self.generate_infographic_filename(image_data, knowledge_item)
            
            # Determine save location
            if organize_by_category:
                category_dir = self.infographics_path / "by_category" / self._sanitize_filename(knowledge_item.category.value)
                save_path = category_dir / filename
            else:
                save_path = self.infographics_path / filename
            
            # Ensure directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download and save image if it has a URL
            if image_data.url and not image_data.local_path:
                success = self._download_image(image_data.url, save_path)
                if success:
                    image_data.local_path = str(save_path)
                    logger.info(f"Infographic saved: {save_path}")
                    return str(save_path)
                else:
                    logger.warning(f"Failed to download infographic: {image_data.url}")
                    return ""
            
            # Copy existing local file
            elif image_data.local_path:
                source_path = Path(image_data.local_path)
                if source_path.exists():
                    shutil.copy2(source_path, save_path)
                    image_data.local_path = str(save_path)
                    logger.info(f"Infographic copied: {save_path}")
                    return str(save_path)
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to save infographic: {e}")
            return ""
    
    def generate_infographic_filename(
        self,
        image_data: ImageData,
        knowledge_item: KnowledgeItem
    ) -> str:
        """Generate a descriptive filename for an infographic."""
        try:
            # Base components
            date_str = knowledge_item.extraction_date.strftime('%Y%m%d') if knowledge_item.extraction_date else 'unknown'
            topic = self._sanitize_filename(knowledge_item.topic)[:30]  # Limit length
            category = self._sanitize_filename(knowledge_item.category.value)[:20]
            
            # Get file extension from original filename or URL
            extension = self._get_image_extension(image_data)
            
            # Generate unique identifier from knowledge item ID
            item_id_short = knowledge_item.id[:8] if knowledge_item.id else 'unknown'
            
            # Construct filename
            filename = f"{date_str}_{category}_{topic}_{item_id_short}{extension}"
            
            # Ensure filename is valid and not too long
            filename = self._sanitize_filename(filename)
            if len(filename) > 200:
                filename = filename[:190] + f"_{item_id_short}{extension}"
            
            return filename
            
        except Exception as e:
            logger.error(f"Failed to generate infographic filename: {e}")
            # Fallback filename
            return f"infographic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    
    def _get_image_extension(self, image_data: ImageData) -> str:
        """Get the appropriate file extension for an image."""
        # Try to get extension from filename
        if image_data.filename:
            ext = Path(image_data.filename).suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                return ext
        
        # Try to get extension from URL
        if image_data.url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(image_data.url)
                path = Path(parsed_url.path)
                ext = path.suffix.lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                    return ext
            except:
                pass
        
        # Default to .jpg
        return '.jpg'
    
    def _download_image(self, url: str, save_path: Path) -> bool:
        """Download an image from URL to local path."""
        try:
            import requests
            
            headers = {
                'User-Agent': self.config.user_agent,
                'Accept': 'image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.request_timeout_seconds,
                stream=True
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"URL does not return an image: {url}")
                return False
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > self.config.max_image_size_mb:
                    logger.warning(f"Image too large ({size_mb:.1f}MB): {url}")
                    return False
            
            # Save image
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.debug(f"Image downloaded: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return False
    
    def organize_files_by_date(self, repository: KnowledgeRepository) -> Dict[str, List[str]]:
        """Organize repository files by date."""
        try:
            date_organization = {}
            
            for item in repository.items:
                if not item.extraction_date:
                    continue
                
                date_key = item.extraction_date.strftime('%Y-%m')
                if date_key not in date_organization:
                    date_organization[date_key] = []
                
                # Add item info
                item_info = {
                    'id': item.id,
                    'title': item.post_title,
                    'category': item.category.value,
                    'source': item.source_link
                }
                date_organization[date_key].append(item_info)
            
            # Create date-based directories and index files
            for date_key, items in date_organization.items():
                date_dir = self.base_path / "by_date" / date_key
                date_dir.mkdir(parents=True, exist_ok=True)
                
                # Create index file
                index_file = date_dir / "index.json"
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'date': date_key,
                        'item_count': len(items),
                        'items': items,
                        'generated': datetime.now().isoformat()
                    }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Files organized by date: {len(date_organization)} periods")
            return date_organization
            
        except Exception as e:
            raise StorageError(f"Failed to organize files by date: {e}")
    
    def organize_files_by_category(self, repository: KnowledgeRepository) -> Dict[str, List[str]]:
        """Organize repository files by category."""
        try:
            category_organization = {}
            
            for item in repository.items:
                category_key = item.category.value
                if category_key not in category_organization:
                    category_organization[category_key] = []
                
                # Add item info
                item_info = {
                    'id': item.id,
                    'title': item.post_title,
                    'topic': item.topic,
                    'source': item.source_link,
                    'date': item.extraction_date.isoformat() if item.extraction_date else None
                }
                category_organization[category_key].append(item_info)
            
            # Create category-based directories and index files
            for category_key, items in category_organization.items():
                category_dir = self.base_path / "by_category" / self._sanitize_filename(category_key)
                category_dir.mkdir(parents=True, exist_ok=True)
                
                # Create index file
                index_file = category_dir / "index.json"
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'category': category_key,
                        'item_count': len(items),
                        'items': items,
                        'generated': datetime.now().isoformat()
                    }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Files organized by category: {len(category_organization)} categories")
            return category_organization
            
        except Exception as e:
            raise StorageError(f"Failed to organize files by category: {e}")
    
    def generate_filename(
        self,
        knowledge_item: KnowledgeItem,
        file_type: str = "general",
        extension: str = ".txt"
    ) -> str:
        """Generate a standardized filename for knowledge items."""
        try:
            # Base components
            date_str = knowledge_item.extraction_date.strftime('%Y%m%d') if knowledge_item.extraction_date else 'unknown'
            topic = self._sanitize_filename(knowledge_item.topic)[:30]
            category = self._sanitize_filename(knowledge_item.category.value)[:20]
            item_id_short = knowledge_item.id[:8] if knowledge_item.id else 'unknown'
            
            # Construct filename based on type
            if file_type == "excel":
                filename = f"knowledge_{date_str}_{category}_{item_id_short}.xlsx"
            elif file_type == "word":
                filename = f"knowledge_{date_str}_{category}_{item_id_short}.docx"
            elif file_type == "summary":
                filename = f"summary_{date_str}_{topic}_{item_id_short}.txt"
            else:
                filename = f"{file_type}_{date_str}_{topic}_{item_id_short}{extension}"
            
            return self._sanitize_filename(filename)
            
        except Exception as e:
            logger.error(f"Failed to generate filename: {e}")
            return f"{file_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for cross-platform compatibility."""
        if not filename:
            return "untitled"
        
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[^\w\s\-_.]', '', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename.strip('._')
        
        # Limit length
        if len(filename) > 200:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:190] + ('.' + ext if ext else '')
        
        # Ensure it's not empty
        if not filename:
            filename = "untitled"
        
        return filename
    
    def create_backup(
        self,
        repository: KnowledgeRepository,
        backup_type: str = "full"
    ) -> str:
        """Create a backup of the knowledge repository."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{backup_type}_{timestamp}"
            backup_dir = self.backups_path / backup_name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            if backup_type == "full":
                # Copy entire repository structure
                for source_dir in [self.docs_path, self.excels_path, self.infographics_path]:
                    if source_dir.exists():
                        dest_dir = backup_dir / source_dir.name
                        shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
                
                # Save repository data
                repo_file = backup_dir / "repository.json"
                with open(repo_file, 'w', encoding='utf-8') as f:
                    f.write(repository.to_json())
            
            elif backup_type == "data_only":
                # Save only the repository data
                repo_file = backup_dir / "repository.json"
                with open(repo_file, 'w', encoding='utf-8') as f:
                    f.write(repository.to_json())
            
            # Create backup manifest
            manifest = {
                'backup_type': backup_type,
                'created': datetime.now().isoformat(),
                'item_count': len(repository.items),
                'repository_version': repository.version,
                'files_included': []
            }
            
            # List included files
            for file_path in backup_dir.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(backup_dir)
                    manifest['files_included'].append(str(relative_path))
            
            manifest_file = backup_dir / "manifest.json"
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Backup created: {backup_dir}")
            return str(backup_dir)
            
        except Exception as e:
            raise StorageError(f"Failed to create backup: {e}")
    
    def restore_from_backup(self, backup_path: str) -> KnowledgeRepository:
        """Restore repository from backup."""
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                raise StorageError(f"Backup directory not found: {backup_path}")
            
            # Check for manifest
            manifest_file = backup_dir / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                logger.info(f"Restoring backup: {manifest.get('backup_type', 'unknown')} from {manifest.get('created', 'unknown')}")
            
            # Restore repository data
            repo_file = backup_dir / "repository.json"
            if not repo_file.exists():
                raise StorageError("Repository data not found in backup")
            
            with open(repo_file, 'r', encoding='utf-8') as f:
                repository = KnowledgeRepository.from_json(f.read())
            
            # Restore files if it's a full backup
            for source_dir in [backup_dir / "docs", backup_dir / "excels", backup_dir / "infographics"]:
                if source_dir.exists():
                    dest_dir = self.base_path / source_dir.name
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    shutil.copytree(source_dir, dest_dir)
            
            logger.info(f"Repository restored from backup: {len(repository.items)} items")
            return repository
            
        except Exception as e:
            raise StorageError(f"Failed to restore from backup: {e}")
    
    def cleanup_old_files(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old temporary and backup files."""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            cleanup_stats = {
                'temp_files_removed': 0,
                'old_backups_removed': 0,
                'space_freed_mb': 0
            }
            
            # Clean temporary files
            if self.temp_path.exists():
                for file_path in self.temp_path.rglob('*'):
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_date:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleanup_stats['temp_files_removed'] += 1
                        cleanup_stats['space_freed_mb'] += file_size / (1024 * 1024)
            
            # Clean old backups (keep more recent ones)
            backup_cutoff = datetime.now().timestamp() - (days_to_keep * 2 * 24 * 60 * 60)  # Keep backups longer
            if self.backups_path.exists():
                for backup_dir in self.backups_path.iterdir():
                    if backup_dir.is_dir() and backup_dir.stat().st_mtime < backup_cutoff:
                        dir_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                        shutil.rmtree(backup_dir)
                        cleanup_stats['old_backups_removed'] += 1
                        cleanup_stats['space_freed_mb'] += dir_size / (1024 * 1024)
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {'temp_files_removed': 0, 'old_backups_removed': 0, 'space_freed_mb': 0}
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics for the knowledge repository."""
        try:
            stats = {
                'base_path': str(self.base_path),
                'total_size_mb': 0,
                'directories': {},
                'file_counts': {},
                'last_updated': datetime.now().isoformat()
            }
            
            # Analyze each directory
            for dir_path in [self.docs_path, self.excels_path, self.infographics_path, self.backups_path]:
                if dir_path.exists():
                    dir_name = dir_path.name
                    dir_size = 0
                    file_count = 0
                    
                    for file_path in dir_path.rglob('*'):
                        if file_path.is_file():
                            file_size = file_path.stat().st_size
                            dir_size += file_size
                            file_count += 1
                    
                    dir_size_mb = dir_size / (1024 * 1024)
                    stats['directories'][dir_name] = {
                        'size_mb': round(dir_size_mb, 2),
                        'file_count': file_count
                    }
                    stats['total_size_mb'] += dir_size_mb
                    stats['file_counts'][dir_name] = file_count
            
            stats['total_size_mb'] = round(stats['total_size_mb'], 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {}
    
    def validate_file_structure(self) -> Dict[str, Any]:
        """Validate the integrity of the file structure."""
        try:
            validation_results = {
                'valid': True,
                'issues': [],
                'directories_checked': 0,
                'files_checked': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Check required directories
            required_dirs = [
                self.base_path,
                self.docs_path,
                self.excels_path,
                self.infographics_path,
                self.backups_path
            ]
            
            for dir_path in required_dirs:
                validation_results['directories_checked'] += 1
                if not dir_path.exists():
                    validation_results['valid'] = False
                    validation_results['issues'].append(f"Missing directory: {dir_path}")
                elif not dir_path.is_dir():
                    validation_results['valid'] = False
                    validation_results['issues'].append(f"Path is not a directory: {dir_path}")
            
            # Check file permissions
            for dir_path in required_dirs:
                if dir_path.exists():
                    try:
                        # Test write permission
                        test_file = dir_path / ".test_write"
                        test_file.touch()
                        test_file.unlink()
                    except Exception as e:
                        validation_results['valid'] = False
                        validation_results['issues'].append(f"No write permission: {dir_path} - {e}")
            
            # Check for orphaned files
            for file_path in self.base_path.rglob('*'):
                if file_path.is_file():
                    validation_results['files_checked'] += 1
                    
                    # Check if file is in expected location
                    relative_path = file_path.relative_to(self.base_path)
                    if not any(str(relative_path).startswith(expected) for expected in ['docs/', 'excels/', 'infographics/', 'backups/', 'temp/']):
                        validation_results['issues'].append(f"Orphaned file: {relative_path}")
            
            logger.info(f"File structure validation: {'PASSED' if validation_results['valid'] else 'FAILED'}")
            return validation_results
            
        except Exception as e:
            logger.error(f"File structure validation failed: {e}")
            return {
                'valid': False,
                'issues': [f"Validation error: {e}"],
                'directories_checked': 0,
                'files_checked': 0,
                'timestamp': datetime.now().isoformat()
            }