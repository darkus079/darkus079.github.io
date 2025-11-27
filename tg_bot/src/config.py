from pydantic_settings import BaseSettings
from typing import List, Optional
import json

class Settings(BaseSettings):
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str
    ADMIN_IDS: List[int] = [123456789]
    
    # Application Settings
    LOG_LEVEL: str = "INFO"
    DEFAULT_MODE: str = "links"
    GLOBAL_DAILY_LIMIT: int = 10000
    PER_USER_DAILY_LIMIT: int = 500
    POLL_INTERVAL_SECONDS: float = 1.0
    REQUEST_TIMEOUT_SECONDS: float = 10.0
    FILES_DIR: str = "files"
    
    # Optional Settings
    TELEGRAM_PROXY_URL: Optional[str] = None
    
    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_PARSING_TOPIC: str = "parsing-tasks"
    KAFKA_CONSUMER_GROUP: str = "parsing-workers"
    MAX_CONCURRENT_TASKS: int = 3

    class Config:
        env_file = ".env"
        extra = "ignore"  # Игнорировать лишние поля

    def __init__(self, **kwargs):
        # Преобразуем ADMIN_IDS если это строка
        if 'ADMIN_IDS' in kwargs and isinstance(kwargs['ADMIN_IDS'], str):
            try:
                # Пробуем распарсить JSON
                admin_ids_str = kwargs['ADMIN_IDS'].replace("'", '"')
                kwargs['ADMIN_IDS'] = json.loads(admin_ids_str)
            except json.JSONDecodeError:
                # Если это просто строка с числами через запятую
                admin_ids_str = kwargs['ADMIN_IDS'].strip('[]')
                kwargs['ADMIN_IDS'] = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
        
        super().__init__(**kwargs)

settings = Settings()