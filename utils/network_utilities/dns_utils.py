"""
DNS工具模块

提供DNS查询、解析、缓存等功能
"""

import socket
import dns.resolver
import dns.zone
import dns.query
import dns.message
import dns.rdatatype
import dns.rdataclass
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DNSTool:
    """DNS工具类"""
    
    def __init__(self, servers: Optional[List[str]] = None, timeout: int = 5):
        """
        初始化DNS工具
        
        Args:
            servers: DNS服务器列表
            timeout: 超时时间（秒）
        """
        self.servers = servers or ['8.8.8.8', '8.8.4.4', '1.1.1.1']
        self.timeout = timeout
        self.cache = {}
        self.cache_ttl = {}
        self.cache_lock = threading.Lock()
    
    def resolve_domain(self, domain: str, record_type: str = 'A', 
                      use_cache: bool = True) -> Dict[str, Any]:
        """
        解析域名
        
        Args:
            domain: 要解析的域名
            record_type: 记录类型 ('A', 'AAAA', 'MX', 'CNAME', 'NS', 'TXT', 'SOA')
            use_cache: 是否使用缓存
            
        Returns:
            解析结果字典
        """
        try:
            # 检查缓存
            cache_key = f"{domain}_{record_type}"
            if use_cache and cache_key in self.cache:
                if time.time() < self.cache_ttl.get(cache_key, 0):
                    return {
                        'domain': domain,
                        'record_type': record_type,
                        'results': self.cache[cache_key],
                        'from_cache': True,
                        'timestamp': time.time()
                    }
            
            # 执行DNS查询
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.timeout
            resolver.lifetime = self.timeout
            
            # 设置DNS服务器
            if len(self.servers) > 0:
                resolver.nameservers = self.servers
            
            results = []
            
            try:
                answers = resolver.resolve(domain, record_type)
                for answer in answers:
                    results.append({
                        'value': str(answer),
                        'ttl': answer.ttl if hasattr(answer, 'ttl') else None
                    })
            except dns.resolver.NXDOMAIN:
                return {
                    'domain': domain,
                    'record_type': record_type,
                    'error': 'Domain does not exist',
                    'results': [],
                    'from_cache': False,
                    'timestamp': time.time()
                }
            except dns.resolver.NoAnswer:
                return {
                    'domain': domain,
                    'record_type': record_type,
                    'error': 'No answer for this record type',
                    'results': [],
                    'from_cache': False,
                    'timestamp': time.time()
                }
            except Exception as e:
                return {
                    'domain': domain,
                    'record_type': record_type,
                    'error': str(e),
                    'results': [],
                    'from_cache': False,
                    'timestamp': time.time()
                }
            
            # 缓存结果
            if use_cache:
                with self.cache_lock:
                    self.cache[cache_key] = results
                    # 设置缓存过期时间（使用最小TTL）
                    ttl = min([r.get('ttl', 300) for r in results]) if results else 300
                    self.cache_ttl[cache_key] = time.time() + ttl
            
            return {
                'domain': domain,
                'record_type': record_type,
                'results': results,
                'from_cache': False,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"域名解析失败 {domain}: {e}")
            return {
                'domain': domain,
                'record_type': record_type,
                'error': str(e),
                'results': [],
                'from_cache': False,
                'timestamp': time.time()
            }
    
    def reverse_lookup(self, ip_address: str) -> Dict[str, Any]:
        """
        反向DNS查询
        
        Args:
            ip_address: IP地址
            
        Returns:
            反向查询结果
        """
        try:
            # 验证IP地址格式
            try:
                socket.inet_aton(ip_address)
            except socket.error:
                return {
                    'ip_address': ip_address,
                    'error': 'Invalid IP address format',
                    'hostname': None,
                    'from_cache': False,
                    'timestamp': time.time()
                }
            
            # 执行反向查询
            try:
                hostname, _, _ = socket.gethostbyaddr(ip_address)
                return {
                    'ip_address': ip_address,
                    'hostname': hostname,
                    'from_cache': False,
                    'timestamp': time.time()
                }
            except socket.herror:
                return {
                    'ip_address': ip_address,
                    'hostname': None,
                    'error': 'No reverse DNS record found',
                    'from_cache': False,
                    'timestamp': time.time()
                }
                
        except Exception as e:
            logger.error(f"反向DNS查询失败 {ip_address}: {e}")
            return {
                'ip_address': ip_address,
                'error': str(e),
                'hostname': None,
                'from_cache': False,
                'timestamp': time.time()
            }
    
    def bulk_resolve(self, domains: List[str], record_type: str = 'A',
                    max_workers: int = 10, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        批量域名解析
        
        Args:
            domains: 域名列表
            record_type: 记录类型
            max_workers: 最大并发数
            use_cache: 是否使用缓存
            
        Returns:
            批量解析结果字典
        """
        try:
            results = {}
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_domain = {
                    executor.submit(self.resolve_domain, domain, record_type, use_cache): domain
                    for domain in domains
                }
                
                # 收集结果
                for future in as_completed(future_to_domain):
                    domain = future_to_domain[future]
                    try:
                        result = future.result()
                        results[domain] = result
                    except Exception as e:
                        logger.error(f"批量解析域名失败 {domain}: {e}")
                        results[domain] = {
                            'domain': domain,
                            'record_type': record_type,
                            'error': str(e),
                            'results': [],
                            'from_cache': False,
                            'timestamp': time.time()
                        }
            
            return results
            
        except Exception as e:
            logger.error(f"批量DNS解析失败: {e}")
            raise
    
    def check_dns_propagation(self, domain: str, record_type: str = 'A',
                             servers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        检查DNS传播情况
        
        Args:
            domain: 域名
            record_type: 记录类型
            servers: 要检查的DNS服务器列表
            
        Returns:
            DNS传播检查结果
        """
        try:
            if servers is None:
                servers = [
                    '8.8.8.8',      # Google
                    '8.8.4.4',      # Google
                    '1.1.1.1',      # Cloudflare
                    '1.0.0.1',      # Cloudflare
                    '208.67.222.222', # OpenDNS
                    '208.67.220.220', # OpenDNS
                    '9.9.9.9',      # Quad9
                    '149.112.112.112' # Quad9
                ]
            
            propagation_results = {}
            
            for server in servers:
                try:
                    original_servers = self.servers
                    self.servers = [server]
                    
                    result = self.resolve_domain(domain, record_type, use_cache=False)
                    propagation_results[server] = result
                    
                    self.servers = original_servers
                    
                except Exception as e:
                    propagation_results[server] = {
                        'domain': domain,
                        'record_type': record_type,
                        'error': str(e),
                        'results': [],
                        'from_cache': False,
                        'timestamp': time.time()
                    }
            
            # 分析传播一致性
            all_results = [r.get('results', []) for r in propagation_results.values() 
                          if 'error' not in r]
            
            is_consistent = len(set(str(r) for r in all_results)) <= 1 if all_results else False
            
            return {
                'domain': domain,
                'record_type': record_type,
                'propagation_results': propagation_results,
                'is_consistent': is_consistent,
                'total_servers': len(servers),
                'successful_queries': len(all_results),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"DNS传播检查失败 {domain}: {e}")
            raise
    
    def get_dns_records(self, domain: str, include_all: bool = True) -> Dict[str, Any]:
        """
        获取域名的所有DNS记录
        
        Args:
            domain: 域名
            include_all: 是否包含所有记录类型
            
        Returns:
            DNS记录详情
        """
        try:
            if include_all:
                record_types = ['A', 'AAAA', 'MX', 'CNAME', 'NS', 'TXT', 'SOA', 'PTR', 'SRV']
            else:
                record_types = ['A', 'AAAA', 'MX', 'CNAME', 'NS']
            
            records = {}
            
            for record_type in record_types:
                result = self.resolve_domain(domain, record_type, use_cache=False)
                if result.get('results'):
                    records[record_type] = result['results']
                elif 'error' not in result:
                    records[record_type] = []
            
            return {
                'domain': domain,
                'records': records,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"获取DNS记录失败 {domain}: {e}")
            raise
    
    def check_dns_health(self, servers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        检查DNS服务器健康状况
        
        Args:
            servers: 要检查的DNS服务器列表
            
        Returns:
            DNS服务器健康检查结果
        """
        try:
            if servers is None:
                servers = [
                    '8.8.8.8', '8.8.4.4', '1.1.1.1', '1.0.0.1',
                    '208.67.222.222', '208.67.220.220', '9.9.9.9'
                ]
            
            health_results = {}
            
            for server in servers:
                try:
                    # 测试DNS服务器响应时间
                    start_time = time.time()
                    
                    resolver = dns.resolver.Resolver()
                    resolver.nameservers = [server]
                    resolver.timeout = 3
                    
                    # 执行简单查询
                    resolver.resolve('google.com', 'A')
                    
                    response_time = (time.time() - start_time) * 1000  # 转换为毫秒
                    
                    health_results[server] = {
                        'status': 'healthy',
                        'response_time_ms': round(response_time, 2),
                        'timestamp': time.time()
                    }
                    
                except Exception as e:
                    health_results[server] = {
                        'status': 'unhealthy',
                        'error': str(e),
                        'response_time_ms': None,
                        'timestamp': time.time()
                    }
            
            # 计算统计信息
            healthy_servers = [s for s, r in health_results.items() if r['status'] == 'healthy']
            response_times = [r['response_time_ms'] for r in health_results.values() 
                            if r['status'] == 'healthy' and r['response_time_ms']]
            
            summary = {
                'total_servers': len(servers),
                'healthy_servers': len(healthy_servers),
                'unhealthy_servers': len(servers) - len(healthy_servers),
                'health_percentage': (len(healthy_servers) / len(servers)) * 100,
                'average_response_time': round(np.mean(response_times), 2) if response_times else None,
                'fastest_server': min(healthy_servers, key=lambda s: health_results[s]['response_time_ms']) if healthy_servers else None,
                'slowest_server': max(healthy_servers, key=lambda s: health_results[s]['response_time_ms']) if healthy_servers else None
            }
            
            return {
                'health_results': health_results,
                'summary': summary,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"DNS健康检查失败: {e}")
            raise
    
    def clear_cache(self) -> None:
        """清空DNS缓存"""
        with self.cache_lock:
            self.cache.clear()
            self.cache_ttl.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            缓存信息字典
        """
        with self.cache_lock:
            return {
                'cached_entries': len(self.cache),
                'cache_keys': list(self.cache.keys()),
                'cache_ttl': dict(self.cache_ttl),
                'current_time': time.time()
            }


def check_domain_expiration(domain: str) -> Dict[str, Any]:
    """
    检查域名过期时间
    
    Args:
        domain: 域名
        
    Returns:
        域名过期信息
    """
    try:
        import whois
        import datetime
        
        # 使用whois查询域名信息
        w = whois.whois(domain)
        
        # 解析过期时间
        expiration_date = w.expiration_date
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]
        
        if isinstance(expiration_date, str):
            expiration_date = datetime.datetime.strptime(expiration_date, '%Y-%m-%d')
        
        days_until_expiry = (expiration_date - datetime.datetime.now()).days
        
        return {
            'domain': domain,
            'expiration_date': expiration_date.isoformat(),
            'days_until_expiry': days_until_expiry,
            'is_expired': days_until_expiry <= 0,
            'registrar': w.registrar if hasattr(w, 'registrar') else None,
            'creation_date': w.creation_date[0].isoformat() if hasattr(w, 'creation_date') and w.creation_date else None,
            'status': w.status if hasattr(w, 'status') else None
        }
        
    except Exception as e:
        logger.error(f"检查域名过期时间失败 {domain}: {e}")
        return {
            'domain': domain,
            'error': str(e),
            'is_expired': None,
            'days_until_expiry': None
        }


def validate_dns_config(domain: str) -> Dict[str, Any]:
    """
    验证DNS配置
    
    Args:
        domain: 域名
        
    Returns:
        DNS配置验证结果
    """
    try:
        dns_tool = DNSTool()
        
        validation_results = {
            'domain': domain,
            'checks': {},
            'overall_status': 'unknown',
            'timestamp': time.time()
        }
        
        # 检查A记录
        a_record = dns_tool.resolve_domain(domain, 'A')
        validation_results['checks']['a_record'] = {
            'exists': bool(a_record.get('results')),
            'results': a_record.get('results', []),
            'error': a_record.get('error')
        }
        
        # 检查MX记录
        mx_record = dns_tool.resolve_domain(domain, 'MX')
        validation_results['checks']['mx_record'] = {
            'exists': bool(mx_record.get('results')),
            'results': mx_record.get('results', []),
            'error': mx_record.get('error')
        }
        
        # 检查NS记录
        ns_record = dns_tool.resolve_domain(domain, 'NS')
        validation_results['checks']['ns_record'] = {
            'exists': bool(ns_record.get('results')),
            'results': ns_record.get('results', []),
            'error': ns_record.get('error')
        }
        
        # 检查CNAME记录（如果有）
        cname_record = dns_tool.resolve_domain(domain, 'CNAME')
        validation_results['checks']['cname_record'] = {
            'exists': bool(cname_record.get('results')),
            'results': cname_record.get('results', []),
            'error': cname_record.get('error')
        }
        
        # 检查AAAA记录
        aaaa_record = dns_tool.resolve_domain(domain, 'AAAA')
        validation_results['checks']['aaaa_record'] = {
            'exists': bool(aaaa_record.get('results')),
            'results': aaaa_record.get('results', []),
            'error': aaaa_record.get('error')
        }
        
        # 确定整体状态
        checks = validation_results['checks']
        passed_checks = sum(1 for check in checks.values() if check['exists'])
        total_checks = len(checks)
        
        if passed_checks == total_checks:
            validation_results['overall_status'] = 'valid'
        elif passed_checks > 0:
            validation_results['overall_status'] = 'partial'
        else:
            validation_results['overall_status'] = 'invalid'
        
        validation_results['passed_checks'] = passed_checks
        validation_results['total_checks'] = total_checks
        validation_results['success_rate'] = (passed_checks / total_checks) * 100
        
        return validation_results
        
    except Exception as e:
        logger.error(f"DNS配置验证失败 {domain}: {e}")
        return {
            'domain': domain,
            'error': str(e),
            'overall_status': 'error',
            'timestamp': time.time()
        }


if __name__ == "__main__":
    # 示例用法
    print("DNS工具模块")
    
    # 创建DNS工具实例
    dns_tool = DNSTool()
    
    # 解析域名
    domain_result = dns_tool.resolve_domain('google.com', 'A')
    print(f"Google A记录: {domain_result['results']}")
    
    # 反向查询
    ip_result = dns_tool.reverse_lookup('8.8.8.8')
    print(f"8.8.8.8 反向查询: {ip_result['hostname']}")
    
    # 批量解析
    domains = ['google.com', 'github.com', 'stackoverflow.com']
    bulk_results = dns_tool.bulk_resolve(domains, 'A')
    print(f"批量解析完成: {len(bulk_results)} 个域名")
    
    # DNS传播检查
    propagation = dns_tool.check_dns_propagation('google.com', 'A')
    print(f"DNS传播一致性: {propagation['is_consistent']}")
    
    # DNS健康检查
    health = dns_tool.check_dns_health()
    print(f"DNS服务器健康率: {health['summary']['health_percentage']:.1f}%")
    
    # 获取DNS记录
    records = dns_tool.get_dns_records('google.com')
    print(f"Google DNS记录类型: {list(records['records'].keys())}")
    
    # 域名过期检查
    try:
        expiry = check_domain_expiration('google.com')
        print(f"Google域名过期时间: {expiry['expiration_date']}")
    except:
        print("域名过期检查需要whois库")
    
    # DNS配置验证
    validation = validate_dns_config('google.com')
    print(f"Google DNS配置状态: {validation['overall_status']}")
    
    print("DNS工具示例完成")