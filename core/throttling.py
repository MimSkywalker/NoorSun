"""
لایه‌ی مستقل rate limiting، ترکیبی بر اساس IP و شناسه (شماره موبایل/ایمیل).

طراحی مشابه الگوی «تک دروازه‌ی مجاز» که در پروژه تکرار شده (مثل
record_stock_movement در فاز۷): هر View حساس، قبل از پردازش، از این ماژول
عبور می‌کند؛ نه IP به‌تنهایی کافی است نه شناسه به‌تنهایی — هر دو با هم
لایه‌ی دفاعی کامل‌تری می‌سازند (IP جلوی حمله‌ی توزیع‌شده روی چند شماره را
می‌گیرد؛ شناسه جلوی حمله‌ی متمرکز روی یک شماره از پشت VPN/IPهای مختلف را).

هر دو شمارنده مستقل از هم بررسی می‌شوند؛ مسدودشدن هرکدام کافی‌ست.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_PREFIX = 'throttle'


@dataclass
class ThrottleResult:
    allowed: bool
    retry_after_seconds: Optional[int] = None
    reason: Optional[str] = None  # 'ip' یا 'identifier'، برای لاگ/دیباگ


class ThrottleRule:
    """

    """
    def __init__(self, max_attempts: int, window_seconds: int, block_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds



RULE_IP_DEFAULT = ThrottleRule(max_attempts=20, window_seconds=15 * 60, block_seconds=30 * 60)
# شناسه (شماره موبایل/ایمیل): محدودیت سخت‌گیرانه‌تر، مستقیماً روی یک حساب
RULE_IDENTIFIER_DEFAULT = ThrottleRule(max_attempts=5, window_seconds=15 * 60, block_seconds=30 * 60)


def get_client_ip(request) -> str:
    """


    """
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _attempts_key(scope: str, kind: str, value: str) -> str:
    return f'{CACHE_PREFIX}:{scope}:{kind}:attempts:{value}'


def _block_key(scope: str, kind: str, value: str) -> str:
    return f'{CACHE_PREFIX}:{scope}:{kind}:blocked:{value}'


def _is_blocked(scope: str, kind: str, value: str) -> Optional[int]:
    """ """
    ttl = cache.ttl(_block_key(scope, kind, value))
    if ttl and ttl > 0:
        return ttl
    return None


def _record_attempt(scope: str, kind: str, value: str, rule: ThrottleRule) -> None:
    key = _attempts_key(scope, kind, value)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=rule.window_seconds)
        count = 1

    if count >= rule.max_attempts:
        cache.set(_block_key(scope, kind, value), True, timeout=rule.block_seconds)
        logger.warning(
            "Throttle: %s/%s='%s' پس از %s تلاش ناموفق، به مدت %s ثانیه مسدود شد.",
            scope, kind, value, count, rule.block_seconds,
        )


def check_throttle(scope: str, ip: str, identifier: Optional[str] = None,
                    ip_rule: ThrottleRule = RULE_IP_DEFAULT,
                    identifier_rule: ThrottleRule = RULE_IDENTIFIER_DEFAULT) -> ThrottleResult:
    """

    """
    ip_blocked_for = _is_blocked(scope, 'ip', ip)
    if ip_blocked_for:
        return ThrottleResult(allowed=False, retry_after_seconds=ip_blocked_for, reason='ip')

    if identifier:
        id_blocked_for = _is_blocked(scope, 'identifier', identifier)
        if id_blocked_for:
            return ThrottleResult(allowed=False, retry_after_seconds=id_blocked_for, reason='identifier')

    return ThrottleResult(allowed=True)


def record_failed_attempt(scope: str, ip: str, identifier: Optional[str] = None,
                           ip_rule: ThrottleRule = RULE_IP_DEFAULT,
                           identifier_rule: ThrottleRule = RULE_IDENTIFIER_DEFAULT) -> None:
    """ """
    _record_attempt(scope, 'ip', ip, ip_rule)
    if identifier:
        _record_attempt(scope, 'identifier', identifier, identifier_rule)


def reset_throttle(scope: str, ip: str, identifier: Optional[str] = None) -> None:
    """

    """
    cache.delete(_attempts_key(scope, 'ip', ip))
    cache.delete(_block_key(scope, 'ip', ip))
    if identifier:
        cache.delete(_attempts_key(scope, 'identifier', identifier))
        cache.delete(_block_key(scope, 'identifier', identifier))