"""
安全工具模块

提供安全相关的工具函数，包括加密解密、身份认证、权限管理、令牌生成、哈希计算、审计等。
"""

from .audit_utils import (
    AuditLogger, SecurityAuditor, ComplianceChecker, AuditTrail,
    AuditLevel, AuditLogger as AuditLoggerClass
)

from .authentication_utils import (
    AuthenticationManager, AuthenticationError, PasswordPolicyError,
    SessionExpiredError, AuthMethod, SessionStatus, UserCredentials, SessionInfo,
    authenticate, create_user, validate_session, generate_token, verify_token,
    change_password, revoke_session, revoke_user_sessions, validate_password_policy,
    cleanup_expired_sessions, get_user_info, get_session_info, auth_manager
)

from .authorization_utils import (
    RoleManager, AuthorizationError, RoleNotFoundError, PermissionNotFoundError,
    AccessDeniedError, PermissionType, ResourceType, AccessEffect,
    Permission, Role, UserRole, AccessControlEntry,
    create_permission, create_role, assign_role_to_user, has_permission,
    check_access, get_user_permissions_summary, get_effective_permissions,
    get_user_roles, add_acl_entry, remove_acl_entry, update_role,
    delete_role, revoke_role_from_user, role_manager
)

from .certificate_utils import (
    CertificateGenerator, CertificateValidator, CertificateManager,
    CertificateInfo, CertificateChain, CertificateType, CertificateStatus,
    CertificateError, CertificateValidationError,
    generate_self_signed_certificate, parse_certificate,
    validate_certificate_chain, get_certificate_from_host,
    save_certificate, load_certificate, create_pkcs12_bundle,
    verify_certificate_signature, cert_manager
)

from .encryption_utils import (
    EncryptionUtils, HashUtils, PasswordUtils, CryptographicUtils,
    secure_compare, generate_secure_random_bytes, mask_sensitive_data
)

from .hash_utils import (
    HashUtils, HashAlgorithm, KeyDerivationFunction, HashStrength,
    HashResult, KeyDerivationResult,
    basic_hash, hmac_hash, salted_hash, secure_password_hash,
    verify_password, derive_key, hash_file, generate_salt,
    constant_time_compare, hash_data_multiple, hash_utils
)

from .token_utils import (
    TokenManager, OAuth2TokenManager, RateLimiter,
    TokenType, TokenAlgorithm, TokenInfo, TokenPayload,
    TokenError, TokenExpiredError, TokenInvalidError,
    generate_access_token, verify_access_token, generate_refresh_token,
    refresh_tokens, revoke_token, generate_api_key, hash_api_key, verify_api_key
)

from .security_metrics import (
    SecurityMetricsCollector, SecurityDashboard,
    SecurityEventType, SecurityLevel, SecurityEvent, SecurityMetrics,
    record_security_event, get_security_metrics, get_user_risk_score,
    get_ip_risk_score, generate_security_report, get_security_dashboard,
    security_collector
)

__all__ = [
    # Audit utils
    'AuditLogger', 'SecurityAuditor', 'ComplianceChecker', 'AuditTrail',
    'AuditLevel', 'AuditLoggerClass',
    
    # Authentication utils
    'AuthenticationManager', 'AuthenticationError', 'PasswordPolicyError',
    'SessionExpiredError', 'AuthMethod', 'SessionStatus', 'UserCredentials', 'SessionInfo',
    'authenticate', 'create_user', 'validate_session', 'generate_token', 'verify_token',
    'change_password', 'revoke_session', 'revoke_user_sessions', 'validate_password_policy',
    'cleanup_expired_sessions', 'get_user_info', 'get_session_info', 'auth_manager',
    
    # Authorization utils
    'RoleManager', 'AuthorizationError', 'RoleNotFoundError', 'PermissionNotFoundError',
    'AccessDeniedError', 'PermissionType', 'ResourceType', 'AccessEffect',
    'Permission', 'Role', 'UserRole', 'AccessControlEntry',
    'create_permission', 'create_role', 'assign_role_to_user', 'has_permission',
    'check_access', 'get_user_permissions_summary', 'get_effective_permissions',
    'get_user_roles', 'add_acl_entry', 'remove_acl_entry', 'update_role',
    'delete_role', 'revoke_role_from_user', 'role_manager',
    
    # Certificate utils
    'CertificateGenerator', 'CertificateValidator', 'CertificateManager',
    'CertificateInfo', 'CertificateChain', 'CertificateType', 'CertificateStatus',
    'CertificateError', 'CertificateValidationError',
    'generate_self_signed_certificate', 'parse_certificate',
    'validate_certificate_chain', 'get_certificate_from_host',
    'save_certificate', 'load_certificate', 'create_pkcs12_bundle',
    'verify_certificate_signature', 'cert_manager',
    
    # Encryption utils
    'EncryptionUtils', 'HashUtils', 'PasswordUtils', 'CryptographicUtils',
    'secure_compare', 'generate_secure_random_bytes', 'mask_sensitive_data',
    
    # Hash utils
    'HashUtils', 'HashAlgorithm', 'KeyDerivationFunction', 'HashStrength',
    'HashResult', 'KeyDerivationResult',
    'basic_hash', 'hmac_hash', 'salted_hash', 'secure_password_hash',
    'verify_password', 'derive_key', 'hash_file', 'generate_salt',
    'constant_time_compare', 'hash_data_multiple', 'hash_utils',
    
    # Token utils
    'TokenManager', 'OAuth2TokenManager', 'RateLimiter',
    'TokenType', 'TokenAlgorithm', 'TokenInfo', 'TokenPayload',
    'TokenError', 'TokenExpiredError', 'TokenInvalidError',
    'generate_access_token', 'verify_access_token', 'generate_refresh_token',
    'refresh_tokens', 'revoke_token', 'generate_api_key', 'hash_api_key', 'verify_api_key',
    
    # Security metrics
    'SecurityMetricsCollector', 'SecurityDashboard',
    'SecurityEventType', 'SecurityLevel', 'SecurityEvent', 'SecurityMetrics',
    'record_security_event', 'get_security_metrics', 'get_user_risk_score',
    'get_ip_risk_score', 'generate_security_report', 'get_security_dashboard',
    'security_collector'
]