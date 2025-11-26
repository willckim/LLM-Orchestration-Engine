"""
LLM Orchestration Engine - Local Storage
Local file-based storage that mimics DynamoDB for development
"""

import json
import os
from typing import Optional, Any
from datetime import datetime
from pathlib import Path
import threading


class LocalStorage:
    """
    Local JSON-based storage that mimics DynamoDB operations
    Used for development and testing without AWS
    """
    
    def __init__(self, storage_path: str = "./data/storage.json"):
        self.storage_path = Path(storage_path)
        self._lock = threading.Lock()
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self):
        """Create storage file if it doesn't exist"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._write_data({"logs": [], "jobs": {}, "metrics": []})
    
    def _read_data(self) -> dict:
        """Read all data from storage"""
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"logs": [], "jobs": {}, "metrics": []}
    
    def _write_data(self, data: dict):
        """Write all data to storage"""
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def put_log(self, log_entry: dict) -> bool:
        """Store a request log entry"""
        with self._lock:
            data = self._read_data()
            
            # Add timestamp if not present
            if "timestamp" not in log_entry:
                log_entry["timestamp"] = datetime.utcnow().isoformat()
            
            data["logs"].append(log_entry)
            
            # Keep only last 10000 logs
            if len(data["logs"]) > 10000:
                data["logs"] = data["logs"][-10000:]
            
            self._write_data(data)
            return True
    
    def get_logs(
        self,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        model: Optional[str] = None,
    ) -> list[dict]:
        """Query logs with filters"""
        data = self._read_data()
        logs = data.get("logs", [])
        
        # Apply filters
        if start_time:
            logs = [l for l in logs if l.get("timestamp", "") >= start_time.isoformat()]
        if end_time:
            logs = [l for l in logs if l.get("timestamp", "") <= end_time.isoformat()]
        if model:
            logs = [l for l in logs if l.get("model") == model]
        
        # Sort by timestamp descending and limit
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return logs[:limit]
    
    def put_job(self, job_id: str, job_data: dict) -> bool:
        """Store an async job"""
        with self._lock:
            data = self._read_data()
            
            job_data["updated_at"] = datetime.utcnow().isoformat()
            if "created_at" not in job_data:
                job_data["created_at"] = datetime.utcnow().isoformat()
            
            data["jobs"][job_id] = job_data
            self._write_data(data)
            return True
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get an async job by ID"""
        data = self._read_data()
        return data.get("jobs", {}).get(job_id)
    
    def update_job(self, job_id: str, updates: dict) -> bool:
        """Update an async job"""
        with self._lock:
            data = self._read_data()
            
            if job_id not in data.get("jobs", {}):
                return False
            
            data["jobs"][job_id].update(updates)
            data["jobs"][job_id]["updated_at"] = datetime.utcnow().isoformat()
            
            self._write_data(data)
            return True
    
    def delete_job(self, job_id: str) -> bool:
        """Delete an async job"""
        with self._lock:
            data = self._read_data()
            
            if job_id in data.get("jobs", {}):
                del data["jobs"][job_id]
                self._write_data(data)
                return True
            return False
    
    def put_metric(self, metric: dict) -> bool:
        """Store a metric data point"""
        with self._lock:
            data = self._read_data()
            
            metric["timestamp"] = datetime.utcnow().isoformat()
            data["metrics"].append(metric)
            
            # Keep only last 50000 metrics
            if len(data["metrics"]) > 50000:
                data["metrics"] = data["metrics"][-50000:]
            
            self._write_data(data)
            return True
    
    def get_metrics(
        self,
        limit: int = 1000,
        metric_name: Optional[str] = None,
    ) -> list[dict]:
        """Query metrics"""
        data = self._read_data()
        metrics = data.get("metrics", [])
        
        if metric_name:
            metrics = [m for m in metrics if m.get("name") == metric_name]
        
        return metrics[-limit:]
    
    def get_stats(self) -> dict:
        """Get storage statistics"""
        data = self._read_data()
        return {
            "total_logs": len(data.get("logs", [])),
            "total_jobs": len(data.get("jobs", {})),
            "total_metrics": len(data.get("metrics", [])),
            "storage_path": str(self.storage_path),
            "storage_size_bytes": self.storage_path.stat().st_size if self.storage_path.exists() else 0,
        }
    
    def clear(self):
        """Clear all storage (for testing)"""
        with self._lock:
            self._write_data({"logs": [], "jobs": {}, "metrics": []})


# DynamoDB-like interface for easy migration
class DynamoDBLocal:
    """
    DynamoDB-compatible interface using local storage
    Makes it easy to switch to real DynamoDB in production
    """
    
    def __init__(self, table_name: str, storage_path: str = "./data"):
        self.table_name = table_name
        self.storage = LocalStorage(f"{storage_path}/{table_name}.json")
    
    def put_item(self, item: dict) -> dict:
        """Put an item (DynamoDB-style)"""
        # Extract key
        key = item.get("pk") or item.get("request_id") or item.get("id")
        
        if "logs" in self.table_name.lower():
            self.storage.put_log(item)
        elif "jobs" in self.table_name.lower():
            self.storage.put_job(key, item)
        else:
            self.storage.put_metric(item)
        
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}
    
    def get_item(self, key: dict) -> dict:
        """Get an item by key (DynamoDB-style)"""
        key_value = list(key.values())[0]
        
        if "jobs" in self.table_name.lower():
            item = self.storage.get_job(key_value)
            if item:
                return {"Item": item}
        
        return {}
    
    def query(self, **kwargs) -> dict:
        """Query items (simplified DynamoDB-style)"""
        limit = kwargs.get("Limit", 100)
        
        if "logs" in self.table_name.lower():
            items = self.storage.get_logs(limit=limit)
        else:
            items = self.storage.get_metrics(limit=limit)
        
        return {"Items": items, "Count": len(items)}


# Singleton instances
_local_storage: Optional[LocalStorage] = None


def get_local_storage() -> LocalStorage:
    """Get or create local storage instance"""
    global _local_storage
    if _local_storage is None:
        _local_storage = LocalStorage()
    return _local_storage


def get_dynamodb_table(table_name: str) -> DynamoDBLocal:
    """Get a DynamoDB-compatible table interface"""
    return DynamoDBLocal(table_name)