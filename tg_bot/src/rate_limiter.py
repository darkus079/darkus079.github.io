import asyncio
import time
from typing import Dict, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter for controlling request frequency and daily limits
    """
    
    def __init__(self):
        # Daily limits tracking
        self.daily_requests: Dict[int, int] = defaultdict(int)  # user_id -> request_count
        self.last_reset_day: int = self._get_current_day()
        
        # Request timestamps for rate limiting
        self.user_requests: Dict[int, list] = defaultdict(list)
        
        # Configuration (will be set from settings)
        self.global_daily_limit = 10000
        self.per_user_daily_limit = 500
        self.request_timeout_seconds = 10.0
        
    def _get_current_day(self) -> int:
        """Get current day as integer (YYYYMMDD)"""
        return int(time.strftime("%Y%m%d"))
    
    def _clean_old_requests(self):
        """Clean old requests and reset daily counters if needed"""
        current_day = self._get_current_day()
        
        # Reset daily counters if day changed
        if current_day != self.last_reset_day:
            self.daily_requests.clear()
            self.last_reset_day = current_day
            logger.info("🔄 Daily counters reset")
        
        # Clean old request timestamps
        current_time = time.time()
        for user_id in list(self.user_requests.keys()):
            # Remove timestamps older than timeout
            self.user_requests[user_id] = [
                ts for ts in self.user_requests[user_id] 
                if current_time - ts < self.request_timeout_seconds
            ]
            
            # Remove empty lists
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
    
    async def check_limit(self, user_id: int) -> bool:
        """
        Check if user can make a request
        
        Returns:
            bool: True if request is allowed, False if limited
        """
        self._clean_old_requests()
        
        # Check global daily limit
        total_requests = sum(self.daily_requests.values())
        if total_requests >= self.global_daily_limit:
            logger.warning(f"🌍 Global daily limit reached: {total_requests}/{self.global_daily_limit}")
            return False
        
        # Check per-user daily limit
        if self.daily_requests[user_id] >= self.per_user_daily_limit:
            logger.warning(f"👤 User {user_id} daily limit reached: {self.daily_requests[user_id]}/{self.per_user_daily_limit}")
            return False
        
        # Check rate limiting (requests per time window)
        current_time = time.time()
        user_recent_requests = [
            ts for ts in self.user_requests[user_id] 
            if current_time - ts < self.request_timeout_seconds
        ]
        
        # Allow request if not too frequent
        if len(user_recent_requests) < 5:  # Max 5 requests per time window
            return True
        
        logger.warning(f"⏰ User {user_id} rate limited: {len(user_recent_requests)} requests in {self.request_timeout_seconds}s")
        return False
    
    async def record_request(self, user_id: int):
        """Record a successful request"""
        current_time = time.time()
        
        self.daily_requests[user_id] += 1
        self.user_requests[user_id].append(current_time)
        
        logger.debug(f"📊 User {user_id} made request ({self.daily_requests[user_id]}/{self.per_user_daily_limit} today)")
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get statistics for a user"""
        self._clean_old_requests()
        
        current_time = time.time()
        recent_requests = [
            ts for ts in self.user_requests.get(user_id, [])
            if current_time - ts < self.request_timeout_seconds
        ]
        
        return {
            "daily_requests": self.daily_requests.get(user_id, 0),
            "daily_limit": self.per_user_daily_limit,
            "recent_requests": len(recent_requests),
            "recent_limit": 5
        }
    
    def get_global_stats(self) -> Dict:
        """Get global statistics"""
        self._clean_old_requests()
        
        return {
            "total_daily_requests": sum(self.daily_requests.values()),
            "global_limit": self.global_daily_limit,
            "active_users": len(self.daily_requests)
        }

# Create global instance
rate_limiter = RateLimiter()