"""
测试数据工具模块

提供测试数据生成和管理工具。
"""

import random
import string
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
import json
import csv
import io
from faker import Faker
import names
import phonenumbers
from email_validator import validate_email, EmailNotValidError


class TestDataGenerator:
    """测试数据生成器"""
    
    def __init__(self, locale: str = 'zh_CN'):
        """初始化数据生成器
        
        Args:
            locale: 地区设置
        """
        self.fake = Faker(locale)
    
    def generate_name(self, gender: str = None) -> str:
        """生成姓名
        
        Args:
            gender: 性别 ('male', 'female', None)
            
        Returns:
            姓名
        """
        if gender == 'male':
            return names.get_first_name(gender='male') + ' ' + names.get_last_name()
        elif gender == 'female':
            return names.get_first_name(gender='female') + ' ' + names.get_last_name()
        else:
            return names.get_full_name()
    
    def generate_email(self, domain: str = None) -> str:
        """生成邮箱地址
        
        Args:
            domain: 邮箱域名
            
        Returns:
            邮箱地址
        """
        if domain:
            return self.fake.email(domain=domain)
        else:
            return self.fake.email()
    
    def generate_phone(self, country_code: str = 'CN') -> str:
        """生成电话号码
        
        Args:
            country_code: 国家代码
            
        Returns:
            电话号码
        """
        try:
            # 使用faker生成号码，然后格式化为国际格式
            number = self.fake.phone_number()
            parsed = phonenumbers.parse(number, country_code)
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except:
            # 如果解析失败，返回原始号码
            return self.fake.phone_number()
    
    def generate_address(self) -> Dict[str, str]:
        """生成地址信息
        
        Returns:
            地址信息字典
        """
        return {
            'street': self.fake.street_address(),
            'city': self.fake.city(),
            'state': self.fake.state(),
            'postal_code': self.fake.postcode(),
            'country': self.fake.country()
        }
    
    def generate_company(self) -> Dict[str, str]:
        """生成公司信息
        
        Returns:
            公司信息字典
        """
        return {
            'name': self.fake.company(),
            'job_title': self.fake.job(),
            'department': self.fake.word().capitalize() + ' Department'
        }
    
    def generate_date(self, start_date: date = None, end_date: date = None) -> date:
        """生成随机日期
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            随机日期
        """
        if start_date is None:
            start_date = date(2020, 1, 1)
        if end_date is None:
            end_date = date.today()
        
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        
        return start_date + timedelta(days=random_days)
    
    def generate_datetime(self, start_datetime: datetime = None, 
                         end_datetime: datetime = None) -> datetime:
        """生成随机日期时间
        
        Args:
            start_datetime: 开始日期时间
            end_datetime: 结束日期时间
            
        Returns:
            随机日期时间
        """
        if start_datetime is None:
            start_datetime = datetime(2020, 1, 1)
        if end_datetime is None:
            end_datetime = datetime.now()
        
        time_between = end_datetime - start_datetime
        seconds_between = time_between.total_seconds()
        random_seconds = random.randrange(int(seconds_between))
        
        return start_datetime + timedelta(seconds=random_seconds)
    
    def generate_text(self, min_length: int = 10, max_length: int = 100) -> str:
        """生成随机文本
        
        Args:
            min_length: 最小长度
            max_length: 最大长度
            
        Returns:
            随机文本
        """
        length = random.randint(min_length, max_length)
        return self.fake.text(max_nb_chars=length)
    
    def generate_number(self, min_val: int = 0, max_val: int = 1000) -> int:
        """生成随机数字
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            随机数字
        """
        return random.randint(min_val, max_val)
    
    def generate_float(self, min_val: float = 0.0, max_val: float = 1000.0, 
                      decimals: int = 2) -> float:
        """生成随机浮点数
        
        Args:
            min_val: 最小值
            max_val: 最大值
            decimals: 小数位数
            
        Returns:
            随机浮点数
        """
        value = random.uniform(min_val, max_val)
        return round(value, decimals)
    
    def generate_boolean(self, true_probability: float = 0.5) -> bool:
        """生成随机布尔值
        
        Args:
            true_probability: 为True的概率
            
        Returns:
            随机布尔值
        """
        return random.random() < true_probability
    
    def generate_uuid(self) -> str:
        """生成UUID
        
        Returns:
            UUID字符串
        """
        return str(uuid.uuid4())
    
    def generate_url(self) -> str:
        """生成URL
        
        Returns:
            URL字符串
        """
        return self.fake.url()
    
    def generate_ip_address(self) -> str:
        """生成IP地址
        
        Returns:
            IP地址字符串
        """
        return self.fake.ipv4()
    
    def generate_color(self) -> str:
        """生成颜色值
        
        Returns:
            十六进制颜色值
        """
        return self.fake.hex_color()
    
    def generate_person_data(self, include_company: bool = True, 
                           include_address: bool = True) -> Dict[str, Any]:
        """生成完整的人员数据
        
        Args:
            include_company: 是否包含公司信息
            include_address: 是否包含地址信息
            
        Returns:
            人员数据字典
        """
        gender = random.choice(['male', 'female', None])
        
        data = {
            'id': self.generate_uuid(),
            'first_name': names.get_first_name(gender=gender),
            'last_name': names.get_last_name(),
            'full_name': self.generate_name(gender),
            'email': self.generate_email(),
            'phone': self.generate_phone(),
            'birth_date': self.generate_date(
                date(1950, 1, 1), 
                date(2000, 12, 31)
            ),
            'gender': gender,
            'created_at': self.generate_datetime()
        }
        
        if include_company:
            company_info = self.generate_company()
            data.update(company_info)
        
        if include_address:
            data['address'] = self.generate_address()
        
        return data
    
    def generate_batch_person_data(self, count: int, **kwargs) -> List[Dict[str, Any]]:
        """批量生成人员数据
        
        Args:
            count: 生成数量
            **kwargs: 其他参数
            
        Returns:
            人员数据列表
        """
        return [self.generate_person_data(**kwargs) for _ in range(count)]


class MockDataProvider:
    """模拟数据提供者"""
    
    # 常见中文姓名
    CHINESE_FIRST_NAMES = [
        '伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋',
        '勇', '艳', '杰', '娟', '涛', '明', '超', '秀英', '霞', '平',
        '刚', '桂英', '建华', '志强', '秀兰', '霞', '勇', '艳', '杰', '娟'
    ]
    
    CHINESE_LAST_NAMES = [
        '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
        '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
        '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧'
    ]
    
    # 常见公司名称
    COMPANY_PREFIXES = ['北京', '上海', '深圳', '广州', '杭州', '南京', '成都', '武汉', '西安', '苏州']
    COMPANY_SUFFIXES = ['科技有限公司', '贸易有限公司', '实业有限公司', '网络科技有限公司', '信息咨询有限公司']
    
    # 常见职位
    JOB_TITLES = [
        '软件工程师', '产品经理', 'UI设计师', '数据分析师', '市场营销专员',
        '销售经理', '人事专员', '财务分析师', '运营专员', '客服专员',
        '项目经理', '技术总监', '运营总监', '销售总监', '人事总监'
    ]
    
    @staticmethod
    def get_chinese_name() -> str:
        """获取中文姓名
        
        Returns:
            中文姓名
        """
        first_name = random.choice(MockDataProvider.CHINESE_FIRST_NAMES)
        last_name = random.choice(MockDataProvider.CHINESE_LAST_NAMES)
        return last_name + first_name
    
    @staticmethod
    def get_company_name() -> str:
        """获取公司名称
        
        Returns:
            公司名称
        """
        prefix = random.choice(MockDataProvider.COMPANY_PREFIXES)
        suffix = random.choice(MockDataProvider.COMPANY_SUFFIXES)
        return prefix + suffix
    
    @staticmethod
    def get_job_title() -> str:
        """获取职位名称
        
        Returns:
            职位名称
        """
        return random.choice(MockDataProvider.JOB_TITLES)
    
    @staticmethod
    def get_chinese_phone() -> str:
        """获取中国手机号
        
        Returns:
            中国手机号
        """
        # 中国手机号段
        prefixes = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
                   '150', '151', '152', '153', '155', '156', '157', '158', '159',
                   '180', '181', '182', '183', '184', '185', '186', '187', '188', '189']
        
        prefix = random.choice(prefixes)
        suffix = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        
        return f"{prefix}{suffix}"
    
    @staticmethod
    def get_chinese_id_card() -> str:
        """生成中国身份证号（模拟）
        
        Returns:
            身份证号
        """
        # 地区代码
        areas = ['110101', '110102', '110105', '110106', '110108', '110109',
                '120101', '120102', '120103', '120104', '120105', '120106']
        
        area = random.choice(areas)
        
        # 出生日期
        year = random.randint(1950, 2000)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        
        birth_date = f"{year:04d}{month:02d}{day:02d}"
        
        # 顺序码
        sequence = random.randint(1, 999)
        
        # 校验码（简化处理）
        check_code = random.choice(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'X'])
        
        return f"{area}{birth_date}{sequence:03d}{check_code}"


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱地址
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否有效
        """
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    @staticmethod
    def validate_phone(phone: str, country_code: str = 'CN') -> bool:
        """验证电话号码
        
        Args:
            phone: 电话号码
            country_code: 国家代码
            
        Returns:
            是否有效
        """
        try:
            parsed = phonenumbers.parse(phone, country_code)
            return phonenumbers.is_valid_number(parsed)
        except:
            return False
    
    @staticmethod
    def validate_chinese_id_card(id_card: str) -> bool:
        """验证中国身份证号
        
        Args:
            id_card: 身份证号
            
        Returns:
            是否有效
        """
        if len(id_card) != 18:
            return False
        
        # 检查格式
        if not re.match(r'^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]$', id_card):
            return False
        
        # 简化的校验码检查
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
        
        sum_val = sum(int(id_card[i]) * weights[i] for i in range(17))
        check_code = check_codes[sum_val % 11]
        
        return id_card[17].upper() == check_code
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL
        
        Args:
            url: URL字符串
            
        Returns:
            是否有效
        """
        pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return pattern.match(url) is not None
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """验证IP地址
        
        Args:
            ip: IP地址
            
        Returns:
            是否有效
        """
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        try:
            for part in parts:
                num = int(part)
                if not 0 <= num <= 255:
                    return False
            return True
        except ValueError:
            return False


class TestDataManager:
    """测试数据管理器"""
    
    def __init__(self, generator: TestDataGenerator = None):
        """初始化测试数据管理器
        
        Args:
            generator: 数据生成器
        """
        self.generator = generator or TestDataGenerator()
        self.data_cache = {}
    
    def cache_data(self, key: str, data: Any):
        """缓存数据
        
        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        self.data_cache[key] = data
    
    def get_cached_data(self, key: str) -> Any:
        """获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据
        """
        return self.data_cache.get(key)
    
    def clear_cache(self):
        """清除缓存"""
        self.data_cache.clear()
    
    def export_to_json(self, data: Any, file_path: str):
        """导出数据到JSON文件
        
        Args:
            data: 要导出的数据
            file_path: 文件路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def export_to_csv(self, data: List[Dict[str, Any]], file_path: str):
        """导出数据到CSV文件
        
        Args:
            data: 要导出的数据列表
            file_path: 文件路径
        """
        if not data:
            return
        
        fieldnames = data[0].keys()
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    def generate_test_dataset(self, dataset_type: str, count: int = 100) -> List[Dict[str, Any]]:
        """生成测试数据集
        
        Args:
            dataset_type: 数据集类型 ('users', 'products', 'orders', 'employees')
            count: 生成数量
            
        Returns:
            测试数据集
        """
        if dataset_type == 'users':
            return self.generator.generate_batch_person_data(count)
        elif dataset_type == 'products':
            return self._generate_products(count)
        elif dataset_type == 'orders':
            return self._generate_orders(count)
        elif dataset_type == 'employees':
            return self._generate_employees(count)
        else:
            raise ValueError(f"Unknown dataset type: {dataset_type}")
    
    def _generate_products(self, count: int) -> List[Dict[str, Any]]:
        """生成产品数据"""
        products = []
        categories = ['电子产品', '服装', '家居', '图书', '食品', '运动器材', '化妆品']
        
        for i in range(count):
            product = {
                'id': self.generator.generate_uuid(),
                'name': f"产品{i+1}",
                'category': random.choice(categories),
                'price': self.generator.generate_float(10, 1000, 2),
                'stock': self.generator.generate_number(0, 100),
                'description': self.generator.generate_text(20, 100),
                'created_at': self.generator.generate_datetime(),
                'is_active': self.generator.generate_boolean(0.8)
            }
            products.append(product)
        
        return products
    
    def _generate_orders(self, count: int) -> List[Dict[str, Any]]:
        """生成订单数据"""
        orders = []
        statuses = ['pending', 'paid', 'shipped', 'delivered', 'cancelled']
        
        for i in range(count):
            order = {
                'id': self.generator.generate_uuid(),
                'order_number': f"ORD{self.generator.generate_number(100000, 999999)}",
                'customer_id': self.generator.generate_uuid(),
                'total_amount': self.generator.generate_float(50, 2000, 2),
                'status': random.choice(statuses),
                'created_at': self.generator.generate_datetime(),
                'updated_at': self.generator.generate_datetime(),
                'shipping_address': self.generator.generate_address()
            }
            orders.append(order)
        
        return orders
    
    def _generate_employees(self, count: int) -> List[Dict[str, Any]]:
        """生成员工数据"""
        employees = []
        departments = ['技术部', '市场部', '人事部', '财务部', '运营部', '客服部']
        
        for i in range(count):
            employee = {
                'id': self.generator.generate_uuid(),
                'employee_id': f"EMP{i+1:04d}",
                'name': MockDataProvider.get_chinese_name(),
                'department': random.choice(departments),
                'position': MockDataProvider.get_job_title(),
                'salary': self.generator.generate_number(5000, 20000),
                'hire_date': self.generator.generate_date(date(2010, 1, 1), date(2023, 12, 31)),
                'email': self.generator.generate_email(),
                'phone': MockDataProvider.get_chinese_phone(),
                'is_active': self.generator.generate_boolean(0.9)
            }
            employees.append(employee)
        
        return employees


class TestDataFixtures:
    """测试数据夹具"""
    
    @staticmethod
    def get_sample_user() -> Dict[str, Any]:
        """获取示例用户数据
        
        Returns:
            用户数据字典
        """
        return {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True,
            'created_at': '2023-01-01T00:00:00Z'
        }
    
    @staticmethod
    def get_sample_company() -> Dict[str, Any]:
        """获取示例公司数据
        
        Returns:
            公司数据字典
        """
        return {
            'id': '550e8400-e29b-41d4-a716-446655440001',
            'name': '测试科技有限公司',
            'address': '北京市朝阳区测试街道123号',
            'phone': '010-12345678',
            'email': 'contact@testcompany.com',
            'website': 'https://www.testcompany.com',
            'founded_date': '2020-01-01',
            'is_active': True
        }
    
    @staticmethod
    def get_sample_product() -> Dict[str, Any]:
        """获取示例产品数据
        
        Returns:
            产品数据字典
        """
        return {
            'id': '550e8400-e29b-41d4-a716-446655440002',
            'name': '测试产品',
            'description': '这是一个测试产品',
            'price': 99.99,
            'category': '电子产品',
            'stock': 100,
            'sku': 'TEST-001',
            'is_active': True,
            'created_at': '2023-01-01T00:00:00Z'
        }
    
    @staticmethod
    def get_sample_order() -> Dict[str, Any]:
        """获取示例订单数据
        
        Returns:
            订单数据字典
        """
        return {
            'id': '550e8400-e29b-41d4-a716-446655440003',
            'order_number': 'ORD123456',
            'customer_id': '550e8400-e29b-41d4-a716-446655440000',
            'total_amount': 199.98,
            'status': 'pending',
            'created_at': '2023-01-01T00:00:00Z',
            'items': [
                {
                    'product_id': '550e8400-e29b-41d4-a716-446655440002',
                    'quantity': 2,
                    'price': 99.99
                }
            ]
        }


def create_test_data_factory(data_type: str, count: int = 100) -> List[Dict[str, Any]]:
    """创建测试数据工厂
    
    Args:
        data_type: 数据类型
        count: 生成数量
        
    Returns:
        测试数据列表
    """
    generator = TestDataGenerator()
    manager = TestDataManager(generator)
    return manager.generate_test_dataset(data_type, count)


def generate_test_users(count: int = 100) -> List[Dict[str, Any]]:
    """生成测试用户数据
    
    Args:
        count: 生成数量
        
    Returns:
        用户数据列表
    """
    return create_test_data_factory('users', count)


def generate_test_companies(count: int = 50) -> List[Dict[str, Any]]:
    """生成测试公司数据
    
    Args:
        count: 生成数量
        
    Returns:
        公司数据列表
    """
    companies = []
    for i in range(count):
        company = {
            'id': str(uuid.uuid4()),
            'name': MockDataProvider.get_company_name(),
            'address': TestDataGenerator().generate_address(),
            'phone': MockDataProvider.get_chinese_phone(),
            'email': TestDataGenerator().generate_email(),
            'website': TestDataGenerator().generate_url(),
            'founded_date': TestDataGenerator().generate_date(date(2000, 1, 1), date(2023, 12, 31)),
            'is_active': TestDataGenerator().generate_boolean(0.9)
        }
        companies.append(company)
    
    return companies