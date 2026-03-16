"""
日期时间工具模块

提供各种日期时间操作的实用工具函数，包括日期计算、格式化、时区处理等。
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import Union, List, Optional, Dict, Any, Tuple, Set
import time as time_module
import calendar
import re
from dateutil import parser
from dateutil.relativedelta import relativedelta
from dateutil.tz import gettz, tzlocal
import pytz
from enum import Enum


class DateUnit(Enum):
    """日期单位枚举"""
    YEAR = 'year'
    MONTH = 'month'
    WEEK = 'week'
    DAY = 'day'
    HOUR = 'hour'
    MINUTE = 'minute'
    SECOND = 'second'
    MICROSECOND = 'microsecond'


class DateTimeUtils:
    """日期时间工具类"""
    
    # 常见日期时间格式
    FORMATS = {
        'date': '%Y-%m-%d',
        'datetime': '%Y-%m-%d %H:%M:%S',
        'datetime_ms': '%Y-%m-%d %H:%M:%S.%f',
        'time': '%H:%M:%S',
        'time_ms': '%H:%M:%S.%f',
        'iso_date': '%Y%m%d',
        'iso_datetime': '%Y%m%dT%H%M%S',
        'iso_datetime_ms': '%Y%m%dT%H%M%S.%f',
        'rfc822': '%a, %d %b %Y %H:%M:%S %z',
        'rfc3339': '%Y-%m-%dT%H:%M:%S%z',
        'chinese_date': '%Y年%m月%d日',
        'chinese_datetime': '%Y年%m月%d日 %H:%M:%S',
        'us_date': '%m/%d/%Y',
        'us_datetime': '%m/%d/%Y %I:%M:%S %p',
        'log': '%Y-%m-%d %H:%M:%S,%f',
        'filename': '%Y%m%d_%H%M%S',
    }
    
    @staticmethod
    def now(tz: Optional[Union[str, timezone]] = None) -> datetime:
        """获取当前时间
        
        Args:
            tz: 时区，None表示本地时区
            
        Returns:
            当前时间
        """
        if tz is None:
            return datetime.now()
        elif isinstance(tz, str):
            return datetime.now(pytz.timezone(tz))
        else:
            return datetime.now(tz)
    
    @staticmethod
    def now_utc() -> datetime:
        """获取当前UTC时间
        
        Returns:
            当前UTC时间
        """
        return datetime.now(timezone.utc)
    
    @staticmethod
    def today() -> date:
        """获取今天的日期
        
        Returns:
            今天的日期
        """
        return date.today()
    
    @staticmethod
    def today_str(format: str = '%Y-%m-%d') -> str:
        """获取今天的日期字符串
        
        Args:
            format: 日期格式
            
        Returns:
            日期字符串
        """
        return DateTimeUtils.format_date(DateTimeUtils.today(), format)
    
    @staticmethod
    def now_str(format: str = '%Y-%m-%d %H:%M:%S', 
                tz: Optional[Union[str, timezone]] = None) -> str:
        """获取当前时间字符串
        
        Args:
            format: 时间格式
            tz: 时区
            
        Returns:
            时间字符串
        """
        return DateTimeUtils.format_datetime(DateTimeUtils.now(tz), format)
    
    @staticmethod
    def parse_date(date_string: str, 
                  format: Optional[str] = None,
                  fuzzy: bool = True) -> Optional[datetime]:
        """解析日期字符串
        
        Args:
            date_string: 日期字符串
            format: 格式字符串，如果不提供则自动解析
            fuzzy: 是否模糊解析（忽略无效字符）
            
        Returns:
            解析后的datetime对象，解析失败返回None
        """
        if not date_string:
            return None
        
        try:
            if format:
                return datetime.strptime(date_string, format)
            else:
                return parser.parse(date_string, fuzzy=fuzzy)
        except (ValueError, TypeError, parser.ParserError):
            return None
    
    @staticmethod
    def parse_date_strict(date_string: str, 
                         formats: Optional[List[str]] = None) -> Optional[datetime]:
        """严格解析日期字符串（尝试多种格式）
        
        Args:
            date_string: 日期字符串
            formats: 要尝试的格式列表，None则使用默认格式列表
            
        Returns:
            解析后的datetime对象，解析失败返回None
        """
        if formats is None:
            formats = [
                '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
                '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
                '%m/%d/%Y', '%Y%m%d', '%Y年%m月%d日',
                '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ'
            ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def format_date(dt: Union[datetime, date, str, None], 
                   format_string: str = '%Y-%m-%d',
                   default: str = '') -> str:
        """格式化日期
        
        Args:
            dt: 日期时间对象、日期字符串或None
            format_string: 格式字符串
            default: 默认值（当dt为None时返回）
            
        Returns:
            格式化后的字符串
        """
        if dt is None:
            return default
        
        if isinstance(dt, str):
            parsed = DateTimeUtils.parse_date(dt)
            if parsed is None:
                return default
            dt = parsed
        
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, time())
        
        return dt.strftime(format_string)
    
    @staticmethod
    def format_datetime(dt: Union[datetime, str, None],
                       format_string: str = '%Y-%m-%d %H:%M:%S',
                       tz: Optional[Union[str, timezone]] = None,
                       default: str = '') -> str:
        """格式化日期时间
        
        Args:
            dt: 日期时间对象、字符串或None
            format_string: 格式字符串
            tz: 目标时区
            default: 默认值
            
        Returns:
            格式化后的字符串
        """
        if dt is None:
            return default
        
        if isinstance(dt, str):
            parsed = DateTimeUtils.parse_date(dt)
            if parsed is None:
                return default
            dt = parsed
        
        if tz is not None:
            dt = DateTimeUtils.to_timezone(dt, tz)
        
        return dt.strftime(format_string)
    
    @staticmethod
    def to_timestamp(dt: Union[datetime, date, str, None], 
                    default: float = 0.0) -> float:
        """转换为时间戳
        
        Args:
            dt: 日期时间对象、字符串或None
            default: 默认值
            
        Returns:
            时间戳（秒）
        """
        if dt is None:
            return default
        
        if isinstance(dt, str):
            dt = DateTimeUtils.parse_date(dt)
            if dt is None:
                return default
        
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, time())
        
        if dt.tzinfo is None:
            # 本地时间转为UTC时间戳
            return time_module.mktime(dt.timetuple()) + dt.microsecond / 1e6
        else:
            # 带时区的时间
            return dt.timestamp()
    
    @staticmethod
    def from_timestamp(timestamp: float, 
                      tz: Optional[Union[str, timezone]] = None) -> datetime:
        """从时间戳创建日期时间
        
        Args:
            timestamp: 时间戳（秒）
            tz: 时区信息
            
        Returns:
            日期时间对象
        """
        if tz is None:
            return datetime.fromtimestamp(timestamp)
        elif isinstance(tz, str):
            return datetime.fromtimestamp(timestamp, pytz.timezone(tz))
        else:
            return datetime.fromtimestamp(timestamp, tz)
    
    @staticmethod
    def get_timezone(tz_name: str = 'Asia/Shanghai') -> timezone:
        """获取时区对象
        
        Args:
            tz_name: 时区名称
            
        Returns:
            时区对象
        """
        return pytz.timezone(tz_name)
    
    @staticmethod
    def get_local_timezone() -> timezone:
        """获取本地时区
        
        Returns:
            本地时区对象
        """
        return tzlocal()
    
    @staticmethod
    def to_timezone(dt: datetime, tz: Union[str, timezone]) -> datetime:
        """转换时区
        
        Args:
            dt: 日期时间对象
            tz: 目标时区
            
        Returns:
            转换后的日期时间
        """
        if isinstance(tz, str):
            target_tz = DateTimeUtils.get_timezone(tz)
        else:
            target_tz = tz
        
        if dt.tzinfo is None:
            # 假设为本地时间，先转为UTC
            dt = pytz.UTC.localize(dt)
        
        return dt.astimezone(target_tz)
    
    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """转换为UTC时间
        
        Args:
            dt: 日期时间对象
            
        Returns:
            UTC时间
        """
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        else:
            dt = dt.astimezone(pytz.UTC)
        return dt
    
    @staticmethod
    def to_local(dt: datetime, local_tz: Optional[str] = None) -> datetime:
        """转换为本地时间
        
        Args:
            dt: 日期时间对象
            local_tz: 本地时区名称，默认系统时区
            
        Returns:
            本地时间
        """
        if local_tz is None:
            local_tz = time_module.tzname[0]
        
        return DateTimeUtils.to_timezone(dt, local_tz)
    
    @staticmethod
    def get_timezone_offset(tz_name: str, dt: Optional[datetime] = None) -> int:
        """获取时区偏移量（秒）
        
        Args:
            tz_name: 时区名称
            dt: 日期时间，None表示当前时间
            
        Returns:
            偏移量（秒）
        """
        tz = DateTimeUtils.get_timezone(tz_name)
        if dt is None:
            dt = datetime.now(tz)
        elif dt.tzinfo is None:
            dt = tz.localize(dt)
        
        offset = dt.utcoffset()
        return int(offset.total_seconds()) if offset else 0
    
    @staticmethod
    def is_dst(dt: Optional[datetime] = None, tz: Optional[str] = None) -> bool:
        """判断是否为夏令时
        
        Args:
            dt: 日期时间，None表示当前时间
            tz: 时区名称
            
        Returns:
            是否为夏令时
        """
        if dt is None:
            dt = DateTimeUtils.now(tz)
        
        return bool(dt.dst())
    
    @staticmethod
    def add_days(dt: Union[datetime, date], days: int) -> Union[datetime, date]:
        """添加天数
        
        Args:
            dt: 基准日期
            days: 要添加的天数（负数表示减去）
            
        Returns:
            添加天数后的日期
        """
        return dt + timedelta(days=days)
    
    @staticmethod
    def subtract_days(dt: Union[datetime, date], days: int) -> Union[datetime, date]:
        """减去天数
        
        Args:
            dt: 基准日期
            days: 要减去的天数
            
        Returns:
            减去天数后的日期
        """
        return DateTimeUtils.add_days(dt, -days)
    
    @staticmethod
    def add_weeks(dt: Union[datetime, date], weeks: int) -> Union[datetime, date]:
        """添加周数
        
        Args:
            dt: 基准日期
            weeks: 要添加的周数
            
        Returns:
            添加周数后的日期
        """
        return dt + timedelta(weeks=weeks)
    
    @staticmethod
    def add_months(dt: Union[datetime, date], months: int) -> Union[datetime, date]:
        """添加月数
        
        Args:
            dt: 基准日期
            months: 要添加的月数
            
        Returns:
            添加月数后的日期
        """
        return dt + relativedelta(months=months)
    
    @staticmethod
    def subtract_months(dt: Union[datetime, date], months: int) -> Union[datetime, date]:
        """减去月数
        
        Args:
            dt: 基准日期
            months: 要减去的月数
            
        Returns:
            减去月数后的日期
        """
        return DateTimeUtils.add_months(dt, -months)
    
    @staticmethod
    def add_years(dt: Union[datetime, date], years: int) -> Union[datetime, date]:
        """添加年数
        
        Args:
            dt: 基准日期
            years: 要添加的年数
            
        Returns:
            添加年数后的日期
        """
        return dt + relativedelta(years=years)
    
    @staticmethod
    def subtract_years(dt: Union[datetime, date], years: int) -> Union[datetime, date]:
        """减去年数
        
        Args:
            dt: 基准日期
            years: 要减去的年数
            
        Returns:
            减去年数后的日期
        """
        return DateTimeUtils.add_years(dt, -years)
    
    @staticmethod
    def add_time(dt: datetime, **kwargs) -> datetime:
        """添加时间
        
        Args:
            dt: 基准时间
            **kwargs: 时间参数（hours, minutes, seconds, microseconds）
            
        Returns:
            添加时间后的时间
        """
        return dt + timedelta(**kwargs)
    
    @staticmethod
    def date_range(start_date: Union[date, str], 
                  end_date: Union[date, str],
                  inclusive: bool = True) -> List[date]:
        """获取日期范围内的所有日期
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            inclusive: 是否包含结束日期
            
        Returns:
            日期列表
        """
        if isinstance(start_date, str):
            start_date = DateTimeUtils.parse_date(start_date).date()
        if isinstance(end_date, str):
            end_date = DateTimeUtils.parse_date(end_date).date()
        
        if not start_date or not end_date:
            return []
        
        if start_date > end_date:
            return []
        
        delta = end_date - start_date
        days = delta.days + (1 if inclusive else 0)
        return [start_date + timedelta(days=i) for i in range(days)]
    
    @staticmethod
    def month_range(year: int, month: int) -> Tuple[date, date]:
        """获取月份的范围
        
        Args:
            year: 年份
            month: 月份
            
        Returns:
            (月份第一天, 月份最后一天)
        """
        first_day = date(year, month, 1)
        _, last_day_num = calendar.monthrange(year, month)
        last_day = date(year, month, last_day_num)
        return first_day, last_day
    
    @staticmethod
    def week_range(dt: Union[date, datetime], 
                  week_start: int = 0) -> Tuple[date, date]:
        """获取周的范围
        
        Args:
            dt: 基准日期
            week_start: 周开始日 (0=Monday, 6=Sunday)
            
        Returns:
            (周开始日期, 周结束日期)
        """
        start = DateTimeUtils.get_week_start(dt, week_start)
        end = start + timedelta(days=6)
        return start, end
    
    @staticmethod
    def get_age(birth_date: Union[date, datetime, str], 
               reference_date: Union[date, datetime, str, None] = None) -> Dict[str, int]:
        """计算年龄
        
        Args:
            birth_date: 出生日期
            reference_date: 参考日期，默认使用当前日期
            
        Returns:
            包含years, months, days的字典
        """
        if isinstance(birth_date, str):
            birth_date = DateTimeUtils.parse_date(birth_date)
        if reference_date is None:
            reference_date = DateTimeUtils.today()
        elif isinstance(reference_date, str):
            reference_date = DateTimeUtils.parse_date(reference_date)
        
        if not birth_date or not reference_date:
            return {'years': 0, 'months': 0, 'days': 0}
        
        if isinstance(birth_date, datetime):
            birth_date = birth_date.date()
        if isinstance(reference_date, datetime):
            reference_date = reference_date.date()
        
        delta = relativedelta(reference_date, birth_date)
        return {
            'years': delta.years,
            'months': delta.months,
            'days': delta.days
        }
    
    @staticmethod
    def get_age_years(birth_date: Union[date, datetime, str],
                     reference_date: Union[date, datetime, str, None] = None) -> int:
        """计算年龄（年）
        
        Args:
            birth_date: 出生日期
            reference_date: 参考日期
            
        Returns:
            年龄（年）
        """
        age = DateTimeUtils.get_age(birth_date, reference_date)
        return age['years']
    
    @staticmethod
    def get_week_start(dt: Union[date, datetime], week_start: int = 0) -> date:
        """获取周开始日期
        
        Args:
            dt: 基准日期
            week_start: 周开始日 (0=Monday, 6=Sunday)
            
        Returns:
            周开始日期
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        days_since_start = (dt.weekday() - week_start) % 7
        return dt - timedelta(days=days_since_start)
    
    @staticmethod
    def get_week_end(dt: Union[date, datetime], week_start: int = 0) -> date:
        """获取周结束日期
        
        Args:
            dt: 基准日期
            week_start: 周开始日 (0=Monday, 6=Sunday)
            
        Returns:
            周结束日期
        """
        start = DateTimeUtils.get_week_start(dt, week_start)
        return start + timedelta(days=6)
    
    @staticmethod
    def get_month_start(dt: Union[date, datetime]) -> date:
        """获取月开始日期
        
        Args:
            dt: 基准日期
            
        Returns:
            月开始日期
        """
        if isinstance(dt, datetime):
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
        else:
            return dt.replace(day=1)
    
    @staticmethod
    def get_month_end(dt: Union[date, datetime]) -> date:
        """获取月结束日期
        
        Args:
            dt: 基准日期
            
        Returns:
            月结束日期
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        next_month = DateTimeUtils.add_months(dt, 1)
        return DateTimeUtils.get_month_start(next_month) - timedelta(days=1)
    
    @staticmethod
    def get_quarter_start(dt: Union[date, datetime]) -> date:
        """获取季度开始日期
        
        Args:
            dt: 基准日期
            
        Returns:
            季度开始日期
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        quarter_month = ((dt.month - 1) // 3) * 3 + 1
        return date(dt.year, quarter_month, 1)
    
    @staticmethod
    def get_quarter_end(dt: Union[date, datetime]) -> date:
        """获取季度结束日期
        
        Args:
            dt: 基准日期
            
        Returns:
            季度结束日期
        """
        start = DateTimeUtils.get_quarter_start(dt)
        next_quarter = DateTimeUtils.add_months(start, 3)
        return next_quarter - timedelta(days=1)
    
    @staticmethod
    def get_year_start(dt: Union[date, datetime]) -> date:
        """获取年开始日期
        
        Args:
            dt: 基准日期
            
        Returns:
            年开始日期
        """
        if isinstance(dt, datetime):
            return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).date()
        else:
            return dt.replace(month=1, day=1)
    
    @staticmethod
    def get_year_end(dt: Union[date, datetime]) -> date:
        """获取年结束日期
        
        Args:
            dt: 基准日期
            
        Returns:
            年结束日期
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        return dt.replace(month=12, day=31)
    
    @staticmethod
    def get_quarter(dt: Union[date, datetime]) -> int:
        """获取季度
        
        Args:
            dt: 基准日期
            
        Returns:
            季度（1-4）
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        return (dt.month - 1) // 3 + 1
    
    @staticmethod
    def get_week_number(dt: Union[date, datetime]) -> int:
        """获取周数（ISO周数）
        
        Args:
            dt: 基准日期
            
        Returns:
            周数
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        return dt.isocalendar()[1]
    
    @staticmethod
    def is_weekend(dt: Union[date, datetime]) -> bool:
        """判断是否为周末
        
        Args:
            dt: 要判断的日期
            
        Returns:
            是否为周末
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        weekday = dt.weekday()
        return weekday >= 5  # 5=Saturday, 6=Sunday
    
    @staticmethod
    def is_weekday(dt: Union[date, datetime]) -> bool:
        """判断是否为工作日
        
        Args:
            dt: 要判断的日期
            
        Returns:
            是否为工作日
        """
        return not DateTimeUtils.is_weekend(dt)
    
    @staticmethod
    def is_business_day(dt: Union[date, datetime], 
                       holidays: Optional[List[date]] = None) -> bool:
        """判断是否为工作日
        
        Args:
            dt: 要判断的日期
            holidays: 假期列表
            
        Returns:
            是否为工作日
        """
        if holidays is None:
            holidays = []
        
        if isinstance(dt, datetime):
            dt = dt.date()
        
        # 检查是否为周末
        if DateTimeUtils.is_weekend(dt):
            return False
        
        # 检查是否为假期
        if dt in holidays:
            return False
        
        return True
    
    @staticmethod
    def get_business_days(start_date: Union[date, str], 
                         end_date: Union[date, str],
                         holidays: Optional[List[date]] = None) -> List[date]:
        """获取两个日期之间的工作日列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            holidays: 假期列表
            
        Returns:
            工作日列表
        """
        if holidays is None:
            holidays = []
        
        if isinstance(start_date, str):
            start_date = DateTimeUtils.parse_date(start_date).date()
        if isinstance(end_date, str):
            end_date = DateTimeUtils.parse_date(end_date).date()
        
        current = start_date
        business_days = []
        
        while current <= end_date:
            if DateTimeUtils.is_business_day(current, holidays):
                business_days.append(current)
            current += timedelta(days=1)
        
        return business_days
    
    @staticmethod
    def get_weekday_name(dt: Union[date, datetime], 
                        short: bool = False,
                        locale: str = 'en') -> str:
        """获取星期几的名称
        
        Args:
            dt: 日期
            short: 是否返回短名称
            locale: 语言（en/zh）
            
        Returns:
            星期几的名称
        """
        weekdays_en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                      'Friday', 'Saturday', 'Sunday']
        short_weekdays_en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        weekdays_zh = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        short_weekdays_zh = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        
        if locale == 'zh':
            names = short_weekdays_zh if short else weekdays_zh
        else:
            names = short_weekdays_en if short else weekdays_en
        
        return names[dt.weekday()]
    
    @staticmethod
    def get_month_name(dt: Union[date, datetime], 
                      short: bool = False,
                      locale: str = 'en') -> str:
        """获取月份名称
        
        Args:
            dt: 日期
            short: 是否返回短名称
            locale: 语言（en/zh）
            
        Returns:
            月份名称
        """
        months_en = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December']
        short_months_en = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        months_zh = ['一月', '二月', '三月', '四月', '五月', '六月',
                    '七月', '八月', '九月', '十月', '十一月', '十二月']
        short_months_zh = ['1月', '2月', '3月', '4月', '5月', '6月',
                          '7月', '8月', '9月', '10月', '11月', '12月']
        
        if locale == 'zh':
            names = short_months_zh if short else months_zh
        else:
            names = short_months_en if short else months_en
        
        return names[dt.month - 1]
    
    @staticmethod
    def next_weekday(dt: Union[date, datetime], 
                    weekday: int) -> date:
        """获取下一个指定星期几
        
        Args:
            dt: 起始日期
            weekday: 星期几（0=Monday, 6=Sunday）
            
        Returns:
            下一个指定日期
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        days_ahead = weekday - dt.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return dt + timedelta(days=days_ahead)
    
    @staticmethod
    def previous_weekday(dt: Union[date, datetime],
                        weekday: int) -> date:
        """获取上一个指定星期几
        
        Args:
            dt: 起始日期
            weekday: 星期几（0=Monday, 6=Sunday）
            
        Returns:
            上一个指定日期
        """
        if isinstance(dt, datetime):
            dt = dt.date()
        
        days_back = dt.weekday() - weekday
        if days_back < 0:
            days_back += 7
        return dt - timedelta(days=days_back)
    
    @staticmethod
    def is_leap_year(year: int) -> bool:
        """判断是否为闰年
        
        Args:
            year: 年份
            
        Returns:
            是否为闰年
        """
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    
    @staticmethod
    def get_days_in_month(year: int, month: int) -> int:
        """获取月份天数
        
        Args:
            year: 年份
            month: 月份
            
        Returns:
            天数
        """
        return calendar.monthrange(year, month)[1]
    
    @staticmethod
    def get_days_in_year(year: int) -> int:
        """获取年份天数
        
        Args:
            year: 年份
            
        Returns:
            天数（闰年366，平年365）
        """
        return 366 if DateTimeUtils.is_leap_year(year) else 365
    
    @staticmethod
    def date_diff(date1: Union[date, datetime, str],
                 date2: Union[date, datetime, str],
                 unit: str = 'days') -> float:
        """计算日期差
        
        Args:
            date1: 第一个日期
            date2: 第二个日期
            unit: 单位（days, hours, minutes, seconds, weeks）
            
        Returns:
            日期差
        """
        if isinstance(date1, str):
            date1 = DateTimeUtils.parse_date(date1)
        if isinstance(date2, str):
            date2 = DateTimeUtils.parse_date(date2)
        
        if not date1 or not date2:
            return 0.0
        
        if isinstance(date1, datetime) and isinstance(date2, datetime):
            delta = date1 - date2
        elif isinstance(date1, date) and isinstance(date2, date):
            delta = date.toordinal(date1) - date.toordinal(date2)
            if unit == 'days':
                return float(delta)
        else:
            # 统一转换为datetime
            if isinstance(date1, date):
                date1 = datetime.combine(date1, time())
            if isinstance(date2, date):
                date2 = datetime.combine(date2, time())
            delta = date1 - date2
        
        if unit == 'days':
            return delta.days
        elif unit == 'hours':
            return delta.total_seconds() / 3600
        elif unit == 'minutes':
            return delta.total_seconds() / 60
        elif unit == 'seconds':
            return delta.total_seconds()
        elif unit == 'weeks':
            return delta.days / 7
        else:
            return delta.total_seconds()
    
    @staticmethod
    def range_overlap(range1: Tuple[datetime, datetime],
                     range2: Tuple[datetime, datetime]) -> bool:
        """判断两个时间范围是否有重叠
        
        Args:
            range1: 第一个时间范围 (start, end)
            range2: 第二个时间范围 (start, end)
            
        Returns:
            是否重叠
        """
        start1, end1 = range1
        start2, end2 = range2
        
        return max(start1, start2) < min(end1, end2)
    
    @staticmethod
    def get_overlap_duration(range1: Tuple[datetime, datetime],
                            range2: Tuple[datetime, datetime]) -> timedelta:
        """获取两个时间范围的重叠时长
        
        Args:
            range1: 第一个时间范围
            range2: 第二个时间范围
            
        Returns:
            重叠时长
        """
        start1, end1 = range1
        start2, end2 = range2
        
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start < overlap_end:
            return overlap_end - overlap_start
        else:
            return timedelta(0)
    
    @staticmethod
    def get_holidays(year: int, country: str = 'CN') -> List[date]:
        """获取节假日列表
        
        Args:
            year: 年份
            country: 国家代码
            
        Returns:
            节假日列表
        """
        holidays = []
        
        if country == 'CN':
            # 中国法定节假日
            # 元旦
            holidays.append(date(year, 1, 1))
            
            # 春节（农历正月初一，需要复杂计算，这里简化处理）
            # 实际情况应该使用农历库或预定义列表
            
            # 清明节（4月4日或5日）
            holidays.append(date(year, 4, 4))
            holidays.append(date(year, 4, 5))
            
            # 劳动节
            holidays.append(date(year, 5, 1))
            
            # 端午节（农历五月初五）
            
            # 中秋节（农历八月十五）
            
            # 国庆节
            for day in range(1, 8):
                holidays.append(date(year, 10, day))
        
        return holidays


class TimeZoneUtils:
    """时区工具类"""
    
    @staticmethod
    def get_all_timezones() -> List[str]:
        """获取所有时区名称
        
        Returns:
            时区名称列表
        """
        return pytz.all_timezones
    
    @staticmethod
    def get_common_timezones() -> List[str]:
        """获取常用时区名称
        
        Returns:
            常用时区名称列表
        """
        return pytz.common_timezones
    
    @staticmethod
    def get_country_timezones(country_code: str) -> List[str]:
        """获取国家的时区列表
        
        Args:
            country_code: 国家代码（如 'CN', 'US'）
            
        Returns:
            时区名称列表
        """
        return pytz.country_timezones.get(country_code, [])
    
    @staticmethod
    def get_timezone_abbreviation(tz_name: str, dt: Optional[datetime] = None) -> str:
        """获取时区缩写
        
        Args:
            tz_name: 时区名称
            dt: 日期时间
            
        Returns:
            时区缩写
        """
        tz = DateTimeUtils.get_timezone(tz_name)
        if dt is None:
            dt = datetime.now(tz)
        elif dt.tzinfo is None:
            dt = tz.localize(dt)
        
        return dt.tzname()
    
    @staticmethod
    def get_timezone_offset_str(tz_name: str, dt: Optional[datetime] = None) -> str:
        """获取时区偏移量字符串
        
        Args:
            tz_name: 时区名称
            dt: 日期时间
            
        Returns:
            偏移量字符串（如 '+0800'）
        """
        offset_seconds = DateTimeUtils.get_timezone_offset(tz_name, dt)
        hours = offset_seconds // 3600
        minutes = (offset_seconds % 3600) // 60
        return f"{hours:+03d}{minutes:02d}"


class DurationUtils:
    """持续时间工具类"""
    
    @staticmethod
    def calculate_duration(start: Union[datetime, date, str], 
                          end: Union[datetime, date, str]) -> Dict[str, int]:
        """计算两个日期之间的持续时间
        
        Args:
            start: 开始时间
            end: 结束时间
            
        Returns:
            包含days, hours, minutes, seconds的字典
        """
        if isinstance(start, str):
            start = DateTimeUtils.parse_date(start)
        if isinstance(end, str):
            end = DateTimeUtils.parse_date(end)
        
        if not start or not end:
            return {'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 0, 'total_seconds': 0}
        
        if isinstance(start, date) and not isinstance(start, datetime):
            start = datetime.combine(start, time())
        if isinstance(end, date) and not isinstance(end, datetime):
            end = datetime.combine(end, time())
        
        delta = end - start
        total_seconds = int(delta.total_seconds())
        
        days = total_seconds // (24 * 3600)
        hours = (total_seconds % (24 * 3600)) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'total_seconds': total_seconds
        }
    
    @staticmethod
    def format_duration(seconds: int, 
                       format: str = 'auto',
                       locale: str = 'zh') -> str:
        """格式化持续时间
        
        Args:
            seconds: 秒数
            format: 格式（auto, hms, dhms, iso）
            locale: 语言（zh/en）
            
        Returns:
            格式化的时间字符串
        """
        if seconds < 0:
            seconds = abs(seconds)
            prefix = '-' if locale == 'en' else '负'
        else:
            prefix = ''
        
        days = seconds // (24 * 3600)
        hours = (seconds % (24 * 3600)) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if format == 'auto':
            if days > 0:
                format = 'dhms'
            elif hours > 0:
                format = 'hms'
            else:
                format = 'ms'
        
        if format == 'dhms':
            if locale == 'zh':
                return f"{prefix}{days}天{hours}小时{minutes}分{secs}秒"
            else:
                return f"{prefix}{days}d {hours}h {minutes}m {secs}s"
        elif format == 'hms':
            total_hours = seconds / 3600
            if locale == 'zh':
                return f"{prefix}{int(total_hours)}小时{minutes}分{secs}秒"
            else:
                return f"{prefix}{total_hours:.1f}h"
        elif format == 'ms':
            total_minutes = seconds / 60
            if locale == 'zh':
                return f"{prefix}{int(total_minutes)}分{secs}秒"
            else:
                return f"{prefix}{total_minutes:.1f}m"
        elif format == 'iso':
            return f"{prefix}P{days}DT{hours}H{minutes}M{secs}S"
        else:
            if locale == 'zh':
                return f"{prefix}{seconds}秒"
            else:
                return f"{prefix}{seconds}s"
    
    @staticmethod
    def parse_duration(duration_string: str) -> int:
        """解析持续时间字符串
        
        Args:
            duration_string: 持续时间字符串，如"1d2h30m", "90s", "1天2小时"
            
        Returns:
            秒数
        """
        duration_string = duration_string.lower().strip()
        
        # 匹配模式：数字+单位
        patterns = [
            (r'(\d+)\s*d(?:ay)?s?', 86400),  # 天
            (r'(\d+)\s*h(?:our)?s?', 3600),   # 小时
            (r'(\d+)\s*m(?:in(?:ute)?)?s?', 60),  # 分钟
            (r'(\d+)\s*s(?:ec(?:ond)?)?s?', 1),   # 秒
            # 中文单位
            (r'(\d+)\s*天', 86400),
            (r'(\d+)\s*小时', 3600),
            (r'(\d+)\s*分钟', 60),
            (r'(\d+)\s*秒', 1),
        ]
        
        total_seconds = 0
        
        for pattern, multiplier in patterns:
            matches = re.findall(pattern, duration_string)
            for match in matches:
                total_seconds += int(match) * multiplier
        
        # 如果没有匹配，尝试解析简单的数字（假设为秒）
        if total_seconds == 0 and duration_string.isdigit():
            total_seconds = int(duration_string)
        
        return total_seconds
    
    @staticmethod
    def human_readable_duration(seconds: int, locale: str = 'zh') -> str:
        """人性化可读的持续时间
        
        Args:
            seconds: 秒数
            locale: 语言
            
        Returns:
            人性化描述
        """
        if seconds < 60:
            return f"{seconds}{'秒' if locale == 'zh' else 's'}"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}{'分钟' if locale == 'zh' else 'm'}"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}{'小时' if locale == 'zh' else 'h'}{minutes}{'分钟' if locale == 'zh' else 'm'}"
            else:
                return f"{hours}{'小时' if locale == 'zh' else 'h'}"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            if hours > 0:
                return f"{days}{'天' if locale == 'zh' else 'd'}{hours}{'小时' if locale == 'zh' else 'h'}"
            else:
                return f"{days}{'天' if locale == 'zh' else 'd'}"


class TimeRange:
    """时间范围类"""
    
    def __init__(self, start: datetime, end: datetime):
        """
        初始化时间范围
        
        Args:
            start: 开始时间
            end: 结束时间
        """
        if start > end:
            raise ValueError("开始时间不能晚于结束时间")
        
        self.start = start
        self.end = end
    
    @property
    def duration(self) -> timedelta:
        """获取持续时间"""
        return self.end - self.start
    
    @property
    def seconds(self) -> float:
        """获取总秒数"""
        return self.duration.total_seconds()
    
    def contains(self, dt: datetime) -> bool:
        """检查是否包含指定时间
        
        Args:
            dt: 要检查的时间
            
        Returns:
            是否包含
        """
        return self.start <= dt <= self.end
    
    def overlaps(self, other: 'TimeRange') -> bool:
        """检查是否与其他时间范围重叠
        
        Args:
            other: 其他时间范围
            
        Returns:
            是否重叠
        """
        return max(self.start, other.start) < min(self.end, other.end)
    
    def intersection(self, other: 'TimeRange') -> Optional['TimeRange']:
        """获取与另一个时间范围的交集
        
        Args:
            other: 其他时间范围
            
        Returns:
            交集时间范围，如果没有重叠则返回None
        """
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        
        if start < end:
            return TimeRange(start, end)
        return None
    
    def union(self, other: 'TimeRange') -> List['TimeRange']:
        """获取与另一个时间范围的并集
        
        Args:
            other: 其他时间范围
            
        Returns:
            并集时间范围列表（可能包含一个或两个）
        """
        if self.overlaps(other) or self.end == other.start or other.end == self.start:
            start = min(self.start, other.start)
            end = max(self.end, other.end)
            return [TimeRange(start, end)]
        else:
            return [self, other] if self.start < other.start else [other, self]
    
    def __repr__(self) -> str:
        return f"TimeRange({self.start} -> {self.end})"


# 便捷函数
def get_timestamp() -> int:
    """获取当前时间戳（秒）
    
    Returns:
        当前时间戳
    """
    return int(time_module.time())


def get_millisecond_timestamp() -> int:
    """获取当前毫秒时间戳
    
    Returns:
        当前时间戳（毫秒）
    """
    return int(time_module.time() * 1000)


def get_microsecond_timestamp() -> int:
    """获取当前微秒时间戳
    
    Returns:
        当前时间戳（微秒）
    """
    return int(time_module.time() * 1000000)


def timestamp_to_datetime(timestamp: Union[int, float], 
                         tz: Optional[Union[str, timezone]] = None) -> datetime:
    """时间戳转换为datetime
    
    Args:
        timestamp: 时间戳（秒）
        tz: 时区
        
    Returns:
        datetime对象
    """
    if tz is None:
        return datetime.fromtimestamp(timestamp)
    elif isinstance(tz, str):
        return datetime.fromtimestamp(timestamp, pytz.timezone(tz))
    else:
        return datetime.fromtimestamp(timestamp, tz)


def datetime_to_timestamp(dt: datetime) -> float:
    """datetime转换为时间戳
    
    Args:
        dt: datetime对象
        
    Returns:
        时间戳（秒）
    """
    return dt.timestamp()


def date_to_datetime(d: date) -> datetime:
    """日期转换为datetime
    
    Args:
        d: 日期对象
        
    Returns:
        datetime对象（时间为00:00:00）
    """
    return datetime.combine(d, time())


def datetime_to_date(dt: datetime) -> date:
    """datetime转换为日期
    
    Args:
        dt: datetime对象
        
    Returns:
        日期对象
    """
    return dt.date()


def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """判断两个时间是否在同一天
    
    Args:
        dt1: 第一个时间
        dt2: 第二个时间
        
    Returns:
        是否在同一天
    """
    return dt1.date() == dt2.date()


def is_same_week(dt1: datetime, dt2: datetime, week_start: int = 0) -> bool:
    """判断两个时间是否在同一周
    
    Args:
        dt1: 第一个时间
        dt2: 第二个时间
        week_start: 周开始日
        
    Returns:
        是否在同一周
    """
    week1_start = DateTimeUtils.get_week_start(dt1, week_start)
    week2_start = DateTimeUtils.get_week_start(dt2, week_start)
    return week1_start == week2_start


def is_same_month(dt1: datetime, dt2: datetime) -> bool:
    """判断两个时间是否在同一月
    
    Args:
        dt1: 第一个时间
        dt2: 第二个时间
        
    Returns:
        是否在同一月
    """
    return dt1.year == dt2.year and dt1.month == dt2.month


def is_same_quarter(dt1: datetime, dt2: datetime) -> bool:
    """判断两个时间是否在同一季度
    
    Args:
        dt1: 第一个时间
        dt2: 第二个时间
        
    Returns:
        是否在同一季度
    """
    return dt1.year == dt2.year and DateTimeUtils.get_quarter(dt1) == DateTimeUtils.get_quarter(dt2)


def is_same_year(dt1: datetime, dt2: datetime) -> bool:
    """判断两个时间是否在同一年
    
    Args:
        dt1: 第一个时间
        dt2: 第二个时间
        
    Returns:
        是否在同一年
    """
    return dt1.year == dt2.year