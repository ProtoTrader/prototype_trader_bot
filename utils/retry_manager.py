"""
Retry Manager - Robust error handling and retry logic
"""

import asyncio
import functools
import logging
from typing import Callable, Any, Optional, Dict, List, Type
from datetime import datetime, timedelta
import random
from collections import defaultdict

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Custom exception for retry failures"""
    def __init__(self, message: str, attempts: int, errors: List[Exception]):
        super().__init__(message)
        self.attempts = attempts
        self.errors = errors


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = defaultdict(int)
        self.last_failure_time = defaultdict(lambda: None)
        self.circuit_open = defaultdict(bool)
    
    def is_open(self, key: str) -> bool:
        """Check if circuit is open"""
        if not self.circuit_open[key]:
            return False
        
        # Check if recovery timeout has passed
        if self.last_failure_time[key]:
            time_passed = (datetime.now() - self.last_failure_time[key]).seconds
            if time_passed >= self.recovery_timeout:
                # Try to close circuit
                self.circuit_open[key] = False
                self.failure_count[key] = 0
                logger.info(f"Circuit breaker closed for {key}")
                return False
        
        return True
    
    def record_success(self, key: str):
        """Record successful call"""
        self.failure_count[key] = 0
        self.circuit_open[key] = False
    
    def record_failure(self, key: str):
        """Record failed call"""
        self.failure_count[key] += 1
        self.last_failure_time[key] = datetime.now()
        
        if self.failure_count[key] >= self.failure_threshold:
            self.circuit_open[key] = True
            logger.warning(f"Circuit breaker opened for {key}")


# Global circuit breaker
circuit_breaker = CircuitBreaker()


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
    circuit_key: Optional[str] = None
):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch
        circuit_key: Key for circuit breaker (optional)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Check circuit breaker
            if circuit_key and circuit_breaker.is_open(circuit_key):
                raise RetryError(f"Circuit breaker open for {circuit_key}", 0, [])
            
            attempts = 0
            current_delay = delay
            errors = []
            
            while attempts < max_attempts:
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record success
                    if circuit_key:
                        circuit_breaker.record_success(circuit_key)
                    
                    return result
                    
                except exceptions as e:
                    attempts += 1
                    errors.append(e)
                    
                    if attempts >= max_attempts:
                        # Record failure
                        if circuit_key:
                            circuit_breaker.record_failure(circuit_key)
                        
                        logger.error(f"{func.__name__} failed after {attempts} attempts")
                        raise RetryError(
                            f"Max retries ({max_attempts}) exceeded for {func.__name__}",
                            attempts,
                            errors
                        )
                    
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, current_delay * 0.1)
                    sleep_time = current_delay + jitter
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempts}/{max_attempts}), "
                        f"retrying in {sleep_time:.2f}s: {str(e)}"
                    )
                    
                    await asyncio.sleep(sleep_time)
                    
                    # Exponential backoff
                    current_delay = min(current_delay * backoff, max_delay)
            
            raise RetryError(f"Unexpected retry loop exit", attempts, errors)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Check circuit breaker
            if circuit_key and circuit_breaker.is_open(circuit_key):
                raise RetryError(f"Circuit breaker open for {circuit_key}", 0, [])
            
            attempts = 0
            current_delay = delay
            errors = []
            
            while attempts < max_attempts:
                try:
                    result = func(*args, **kwargs)
                    
                    # Record success
                    if circuit_key:
                        circuit_breaker.record_success(circuit_key)
                    
                    return result
                    
                except exceptions as e:
                    attempts += 1
                    errors.append(e)
                    
                    if attempts >= max_attempts:
                        # Record failure
                        if circuit_key:
                            circuit_breaker.record_failure(circuit_key)
                        
                        logger.error(f"{func.__name__} failed after {attempts} attempts")
                        raise RetryError(
                            f"Max retries ({max_attempts}) exceeded for {func.__name__}",
                            attempts,
                            errors
                        )
                    
                    # Add jitter
                    jitter = random.uniform(0, current_delay * 0.1)
                    sleep_time = current_delay + jitter
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempts}/{max_attempts}), "
                        f"retrying in {sleep_time:.2f}s: {str(e)}"
                    )
                    
                    import time
                    time.sleep(sleep_time)
                    
                    # Exponential backoff
                    current_delay = min(current_delay * backoff, max_delay)
            
            raise RetryError(f"Unexpected retry loop exit", attempts, errors)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class TransactionRetryManager:
    """Specialized retry manager for blockchain transactions"""
    
    def __init__(self):
        self.pending_transactions = {}
        self.failed_transactions = defaultdict(list)
    
    async def execute_with_retry(
        self,
        transaction_func: Callable,
        tx_params: Dict,
        max_attempts: int = 3,
        gas_multiplier: float = 1.1
    ) -> Dict:
        """Execute transaction with automatic retry and gas adjustment"""
        
        attempts = 0
        last_error = None
        
        while attempts < max_attempts:
            try:
                # Adjust gas price for retry
                if attempts > 0:
                    if 'gasPrice' in tx_params:
                        tx_params['gasPrice'] = int(tx_params['gasPrice'] * gas_multiplier)
                    elif 'maxFeePerGas' in tx_params:
                        tx_params['maxFeePerGas'] = int(tx_params['maxFeePerGas'] * gas_multiplier)
                        tx_params['maxPriorityFeePerGas'] = int(
                            tx_params.get('maxPriorityFeePerGas', 0) * gas_multiplier
                        )
                
                # Execute transaction
                result = await transaction_func(**tx_params)
                
                if result.get('success'):
                    return result
                else:
                    raise Exception(result.get('error', 'Unknown error'))
                    
            except Exception as e:
                attempts += 1
                last_error = e
                
                error_str = str(e).lower()
                
                # Check for specific errors
                if 'nonce too low' in error_str:
                    # Get fresh nonce
                    logger.info("Nonce too low, fetching fresh nonce")
                    # Update nonce in tx_params
                    continue
                
                elif 'insufficient funds' in error_str:
                    # No point retrying
                    logger.error("Insufficient funds for transaction")
                    raise
                
                elif 'gas too low' in error_str or 'out of gas' in error_str:
                    # Increase gas limit
                    if 'gas' in tx_params:
                        tx_params['gas'] = int(tx_params['gas'] * 1.5)
                    logger.info(f"Increasing gas limit to {tx_params.get('gas')}")
                
                elif 'replacement transaction underpriced' in error_str:
                    # Significantly increase gas price
                    gas_multiplier = 1.5
                    logger.info("Transaction underpriced, increasing gas price")
                
                if attempts < max_attempts:
                    wait_time = min(2 ** attempts, 30)  # Exponential backoff, max 30s
                    logger.warning(
                        f"Transaction failed (attempt {attempts}/{max_attempts}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
        
        # All attempts failed
        self.failed_transactions[tx_params.get('from', 'unknown')].append({
            'params': tx_params,
            'error': str(last_error),
            'attempts': attempts,
            'timestamp': datetime.now()
        })
        
        raise RetryError(
            f"Transaction failed after {attempts} attempts",
            attempts,
            [last_error]
        )
    
    async def monitor_pending_transaction(
        self,
        tx_hash: str,
        web3_instance,
        timeout: int = 300,
        confirmation_blocks: int = 2
    ) -> Dict:
        """Monitor pending transaction with timeout"""
        
        start_time = datetime.now()
        last_block = web3_instance.eth.block_number
        
        while (datetime.now() - start_time).seconds < timeout:
            try:
                # Get transaction receipt
                receipt = web3_instance.eth.get_transaction_receipt(tx_hash)
                
                if receipt:
                    # Wait for confirmations
                    current_block = web3_instance.eth.block_number
                    confirmations = current_block - receipt['blockNumber']
                    
                    if confirmations >= confirmation_blocks:
                        return {
                            'success': receipt['status'] == 1,
                            'receipt': receipt,
                            'confirmations': confirmations
                        }
                    else:
                        # Wait for more confirmations
                        await asyncio.sleep(2)
                else:
                    # Check if transaction is still pending
                    tx = web3_instance.eth.get_transaction(tx_hash)
                    if not tx:
                        # Transaction disappeared - possibly replaced
                        return {
                            'success': False,
                            'error': 'Transaction not found',
                            'replaced': True
                        }
                    
                    # Still pending, check if stuck
                    current_block = web3_instance.eth.block_number
                    if current_block - last_block > 10:  # 10 blocks passed
                        logger.warning(f"Transaction {tx_hash} stuck for 10+ blocks")
                        # Could implement auto-replace logic here
                    
                    last_block = current_block
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error monitoring transaction: {e}")
                await asyncio.sleep(5)
        
        # Timeout reached
        return {
            'success': False,
            'error': 'Transaction timeout',
            'timeout': True
        }


# Global transaction retry manager
tx_retry_manager = TransactionRetryManager()


# Specialized decorators for common operations
def retry_web3_call(max_attempts: int = 5):
    """Decorator for Web3 RPC calls"""
    return with_retry(
        max_attempts=max_attempts,
        delay=0.5,
        backoff=2.0,
        max_delay=10.0,
        exceptions=(Exception,),
        circuit_key='web3_rpc'
    )


def retry_dex_trade(max_attempts: int = 3):
    """Decorator for DEX trades"""
    return with_retry(
        max_attempts=max_attempts,
        delay=2.0,
        backoff=1.5,
        max_delay=30.0,
        exceptions=(Exception,),
        circuit_key='dex_trade'
    )


def retry_api_call(max_attempts: int = 3, circuit_key: Optional[str] = None):
    """Decorator for external API calls"""
    return with_retry(
        max_attempts=max_attempts,
        delay=1.0,
        backoff=2.0,
        max_delay=10.0,
        exceptions=(Exception,),
        circuit_key=circuit_key or 'api_call'
    )