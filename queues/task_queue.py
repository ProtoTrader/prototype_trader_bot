import asyncio
import json
import traceback
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import logging
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

from cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3

@dataclass
class Task:
    id: str
    type: str
    data: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    attempts: int = 0
    max_attempts: int = 3
    result: Optional[Any] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.type,
            'data': self.data,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'attempts': self.attempts,
            'max_attempts': self.max_attempts,
            'result': self.result,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        return cls(
            id=data['id'],
            type=data['type'],
            data=data['data'],
            priority=TaskPriority(data['priority']),
            status=TaskStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            attempts=data.get('attempts', 0),
            max_attempts=data.get('max_attempts', 3),
            result=data.get('result'),
            error=data.get('error')
        )

class TaskQueue:
    def __init__(self, name: str, cache: Optional[RedisCache] = None):
        self.name = name
        self.cache = cache or RedisCache()
        self.handlers: Dict[str, Callable] = {}
        self.workers: List[asyncio.Task] = []
        self.running = False
        
    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a task type"""
        self.handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
        
    async def enqueue(
        self, 
        task_type: str, 
        data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Add a task to the queue"""
        task = Task(
            id=str(uuid.uuid4()),
            type=task_type,
            data=data,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store task metadata
        self.cache.set(f"task:{task.id}", task.to_dict(), expire=86400)
        
        # Add to priority queue
        queue_name = f"queue:{self.name}:{priority.name}"
        self.cache.add_to_queue(queue_name, task.id)
        
        logger.info(f"Enqueued task {task.id} of type {task_type} with priority {priority.name}")
        return task.id
        
    async def process_task(self, task_id: str) -> bool:
        """Process a single task"""
        task_data = self.cache.get(f"task:{task_id}")
        if not task_data:
            logger.error(f"Task {task_id} not found")
            return False
            
        task = Task.from_dict(task_data)
        
        # Update status
        task.status = TaskStatus.PROCESSING
        task.updated_at = datetime.now()
        task.attempts += 1
        self.cache.set(f"task:{task.id}", task.to_dict(), expire=86400)
        
        handler = self.handlers.get(task.type)
        if not handler:
            logger.error(f"No handler for task type: {task.type}")
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task type: {task.type}"
            self.cache.set(f"task:{task.id}", task.to_dict(), expire=86400)
            return False
            
        try:
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task.data)
            else:
                result = handler(task.data)
                
            # Update task with result
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.updated_at = datetime.now()
            self.cache.set(f"task:{task.id}", task.to_dict(), expire=86400)
            
            logger.info(f"Task {task.id} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {str(e)}")
            task.error = str(e)
            task.updated_at = datetime.now()
            
            if task.attempts < task.max_attempts:
                task.status = TaskStatus.RETRYING
                # Re-queue with lower priority
                retry_priority = TaskPriority(max(0, task.priority.value - 1))
                queue_name = f"queue:{self.name}:{retry_priority.name}"
                self.cache.add_to_queue(queue_name, task.id)
                logger.info(f"Re-queued task {task.id} for retry")
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"Task {task.id} failed after {task.attempts} attempts")
                
            self.cache.set(f"task:{task.id}", task.to_dict(), expire=86400)
            return False
            
    async def worker(self, worker_id: int):
        """Worker coroutine that processes tasks"""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            task_id = None
            
            # Check queues by priority
            for priority in sorted(TaskPriority, key=lambda p: p.value, reverse=True):
                queue_name = f"queue:{self.name}:{priority.name}"
                task_id = self.cache.pop_from_queue(queue_name, timeout=1)
                if task_id:
                    break
                    
            if task_id:
                try:
                    await self.process_task(task_id)
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {str(e)}")
            else:
                await asyncio.sleep(0.1)
                
        logger.info(f"Worker {worker_id} stopped")
        
    async def start(self, num_workers: int = 3):
        """Start the task queue with workers"""
        self.running = True
        
        for i in range(num_workers):
            worker = asyncio.create_task(self.worker(i))
            self.workers.append(worker)
            
        logger.info(f"Started {num_workers} workers for queue {self.name}")
        
    async def stop(self):
        """Stop all workers"""
        self.running = False
        
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()
            
        logger.info(f"Stopped queue {self.name}")
        
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get task status"""
        task_data = self.cache.get(f"task:{task_id}")
        if task_data:
            return Task.from_dict(task_data)
        return None
        
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        stats = {}
        for priority in TaskPriority:
            queue_name = f"queue:{self.name}:{priority.name}"
            stats[priority.name] = self.cache.queue_length(queue_name)
        return stats

# Specialized queues for different task types
class TradingQueue(TaskQueue):
    """Queue for trading operations"""
    def __init__(self, cache: Optional[RedisCache] = None):
        super().__init__("trading", cache)
        
        # Register trading handlers
        self.register_handler("buy_token", self._handle_buy_token)
        self.register_handler("sell_token", self._handle_sell_token)
        self.register_handler("check_price", self._handle_check_price)
        self.register_handler("execute_stop_loss", self._handle_stop_loss)
        self.register_handler("execute_take_profit", self._handle_take_profit)
        
    async def _handle_buy_token(self, data: dict):
        from trading_engine import TradingEngine
        engine = TradingEngine()
        return await engine.buy_token(
            wallet_address=data['wallet_address'],
            chain=data['chain'],
            token_address=data['token_address'],
            amount=data['amount'],
            slippage=data.get('slippage', 0.5),
            user_id=data['user_id']
        )
        
    async def _handle_sell_token(self, data: dict):
        from trading_engine import TradingEngine
        engine = TradingEngine()
        return await engine.sell_token(
            wallet_address=data['wallet_address'],
            chain=data['chain'],
            token_address=data['token_address'],
            amount=data['amount'],
            slippage=data.get('slippage', 0.5),
            user_id=data['user_id']
        )
        
    async def _handle_check_price(self, data: dict):
        from trading_engine import TradingEngine
        engine = TradingEngine()
        return await engine.get_token_price(
            chain=data['chain'],
            token_address=data['token_address']
        )
        
    async def _handle_stop_loss(self, data: dict):
        # Implement stop loss execution
        pass
        
    async def _handle_take_profit(self, data: dict):
        # Implement take profit execution
        pass

class NotificationQueue(TaskQueue):
    """Queue for notifications"""
    def __init__(self, cache: Optional[RedisCache] = None):
        super().__init__("notification", cache)
        
        self.register_handler("send_telegram", self._handle_telegram)
        self.register_handler("send_alert", self._handle_alert)
        
    async def _handle_telegram(self, data: dict):
        from telegram import Bot
        bot = Bot(token=data['token'])
        await bot.send_message(
            chat_id=data['chat_id'],
            text=data['text'],
            parse_mode=data.get('parse_mode', 'HTML')
        )
        
    async def _handle_alert(self, data: dict):
        # Implement alert handling
        pass

class AnalyticsQueue(TaskQueue):
    """Queue for analytics and data processing"""
    def __init__(self, cache: Optional[RedisCache] = None):
        super().__init__("analytics", cache)
        
        self.register_handler("calculate_pnl", self._handle_calculate_pnl)
        self.register_handler("update_statistics", self._handle_update_stats)
        
    async def _handle_calculate_pnl(self, data: dict):
        # Implement PnL calculation
        pass
        
    async def _handle_update_stats(self, data: dict):
        # Implement statistics update
        pass