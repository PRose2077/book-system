from datetime import datetime, timezone
from bson import ObjectId

class UploadFile:
    def __init__(self, filename, size):
        self._id = str(ObjectId())
        self.filename = filename
        self.size = size
        self.upload_time = datetime.now(timezone.utc)
        self.status = 'queued' # 新状态：queued -> processing -> completed/failed
        self.processed_records = 0
        self.total_records = 0
        self.error_message = None
        self.queue_position = None # 队列位置
    def to_dict(self):
        return {
            '_id': self._id,
            'filename': self.filename,
            'size': self.size,
            'upload_time': self.upload_time,
            'status': self.status,
            'processed_records': self.processed_records,
            'total_records': self.total_records,
            'error_message': self.error_message
        }