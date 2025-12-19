"""
API Middleware for ZTA-Finance
Security middleware for request processing
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import time

from config.logging import get_logger
from src.audit.audit_logger import AuditLogger, EventType, EventSeverity

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = f"req_{int(time.time() * 1000)}"
        request.state.request_id = request_id
        
        # Start time
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent", "")
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            }
        )
        
        # Add request ID to response
        response.headers["X-Request-ID"] = request_id
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, redis_client, rate_limit: int = 60):
        super().__init__(app)
        self.redis = redis_client
        self.rate_limit = rate_limit
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)
        
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        try:
            # Increment counter
            count = self.redis.incr(key)
            
            if count == 1:
                # Set expiry on first request (1 minute window)
                self.redis.expire(key, 60)
            
            # Check limit
            if count > self.rate_limit:
                logger.warning(
                    f"Rate limit exceeded",
                    extra={
                        "client_ip": client_ip,
                        "request_count": count,
                        "limit": self.rate_limit
                    }
                )
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate Limit Exceeded",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": 60
                    },
                    headers={
                        "Retry-After": "60",
                        "X-Rate-Limit-Limit": str(self.rate_limit),
                        "X-Rate-Limit-Remaining": "0"
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-Rate-Limit-Limit"] = str(self.rate_limit)
            response.headers["X-Rate-Limit-Remaining"] = str(self.rate_limit - count)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # Continue without rate limiting on error
            return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add context information to requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Add context to request state
        request.state.ip_address = request.client.host
        request.state.user_agent = request.headers.get("user-agent", "")
        request.state.timestamp = datetime.utcnow()
        
        # Extract additional headers
        request.state.device_id = request.headers.get("X-Device-ID")
        request.state.client_version = request.headers.get("X-Client-Version")
        request.state.platform = request.headers.get("X-Platform")
        
        response = await call_next(request)
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            # Let FastAPI handle HTTP exceptions
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(
                f"Unexpected error: {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred. Please try again later.",
                    "request_id": getattr(request.state, "request_id", None)
                }
            )


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with security considerations"""
    
    def __init__(
        self,
        app,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        allow_credentials: bool = True
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
    
    async def dispatch(self, request: Request, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = JSONResponse(content={})
            response.headers["Access-Control-Allow-Origin"] = self._get_origin(request)
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            
            response.headers["Access-Control-Max-Age"] = "600"
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = self._get_origin(request)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
    
    def _get_origin(self, request: Request) -> str:
        """Get allowed origin based on request"""
        origin = request.headers.get("origin")
        
        if "*" in self.allow_origins:
            return origin or "*"
        
        if origin in self.allow_origins:
            return origin
        
        return self.allow_origins[0] if self.allow_origins else "*"