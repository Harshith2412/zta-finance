from typing import Dict, Any
from datetime import datetime, time
import ipaddress

from config.logging import get_logger

logger = get_logger(__name__)


class RiskAnalyzer:
    """Risk-based authentication and continuous verification"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
        # Risk factor weights
        self.risk_weights = {
            "unknown_device": 30,
            "unknown_location": 20,
            "unusual_time": 15,
            "high_transaction_amount": 25,
            "multiple_failed_attempts": 40,
            "geo_mismatch": 35,
            "tor_or_vpn": 50,
            "suspicious_ip": 30,
            "rapid_requests": 25,
            "device_change": 20
        }
    
    def calculate_request_risk(self, context: Dict[str, Any]) -> int:
        """
        Calculate risk score for a request
        
        Args:
            context: Request context containing:
                - device_id: Device identifier
                - device_trusted: Is device trusted
                - ip_address: Client IP
                - location: Geolocation data
                - user_id: User identifier
                - transaction_amount: Amount if financial transaction
                - previous_location: User's typical location
        
        Returns:
            Risk score (0-100)
        """
        
        risk_score = 0
        risk_factors = []
        
        # Device trust
        if not context.get("device_trusted", False):
            risk_score += self.risk_weights["unknown_device"]
            risk_factors.append("unknown_device")
        
        # Location analysis
        if self._is_unknown_location(context):
            risk_score += self.risk_weights["unknown_location"]
            risk_factors.append("unknown_location")
        
        # Time-based analysis
        if self._is_unusual_time():
            risk_score += self.risk_weights["unusual_time"]
            risk_factors.append("unusual_time")
        
        # Transaction amount
        transaction_amount = context.get("transaction_amount", 0)
        if transaction_amount > 10000:  # High value threshold
            risk_score += self.risk_weights["high_transaction_amount"]
            risk_factors.append("high_transaction_amount")
        
        # Failed login attempts
        user_id = context.get("user_id")
        if user_id and self._has_recent_failed_attempts(user_id):
            risk_score += self.risk_weights["multiple_failed_attempts"]
            risk_factors.append("multiple_failed_attempts")
        
        # Geographic mismatch
        if self._detect_geo_mismatch(context):
            risk_score += self.risk_weights["geo_mismatch"]
            risk_factors.append("geo_mismatch")
        
        # VPN/Tor detection
        if self._is_vpn_or_tor(context.get("ip_address")):
            risk_score += self.risk_weights["tor_or_vpn"]
            risk_factors.append("tor_or_vpn")
        
        # Rapid requests (velocity check)
        if user_id and self._detect_rapid_requests(user_id):
            risk_score += self.risk_weights["rapid_requests"]
            risk_factors.append("rapid_requests")
        
        # Cap at 100
        final_score = min(risk_score, 100)
        
        # Log risk assessment
        logger.info(
            f"Risk assessment - Score: {final_score}, "
            f"Factors: {', '.join(risk_factors) if risk_factors else 'none'}"
        )
        
        # Store risk assessment
        if user_id:
            self._store_risk_assessment(user_id, final_score, risk_factors)
        
        return final_score
    
    def _is_unknown_location(self, context: Dict[str, Any]) -> bool:
        """Check if request is from unknown location"""
        
        current_location = context.get("location")
        user_id = context.get("user_id")
        
        if not current_location or not user_id:
            return False
        
        # Get user's typical locations
        key = f"user_locations:{user_id}"
        known_locations = self.redis.smembers(key)
        
        if not known_locations:
            # First time - add to known locations
            location_str = f"{current_location.get('country')}:{current_location.get('city')}"
            self.redis.sadd(key, location_str)
            return True
        
        # Check if current location is known
        location_str = f"{current_location.get('country')}:{current_location.get('city')}"
        
        if location_str.encode() not in known_locations:
            # New location - add it but flag as unknown
            self.redis.sadd(key, location_str)
            return True
        
        return False
    
    def _is_unusual_time(self) -> bool:
        """Check if current time is unusual (outside business hours)"""
        
        current_time = datetime.utcnow().time()
        
        # Define unusual hours (e.g., 1 AM - 6 AM UTC)
        unusual_start = time(1, 0)
        unusual_end = time(6, 0)
        
        return unusual_start <= current_time <= unusual_end
    
    def _has_recent_failed_attempts(self, user_id: str) -> bool:
        """Check for recent failed login attempts"""
        
        key = f"failed_attempts:{user_id}"
        attempts = self.redis.get(key)
        
        return int(attempts or 0) >= 3
    
    def _detect_geo_mismatch(self, context: Dict[str, Any]) -> bool:
        """Detect impossible travel (geographically impossible rapid location change)"""
        
        user_id = context.get("user_id")
        current_location = context.get("location")
        
        if not user_id or not current_location:
            return False
        
        # Get last known location
        key = f"last_location:{user_id}"
        last_location_data = self.redis.get(key)
        
        if not last_location_data:
            # Store current location
            import json
            self.redis.setex(
                key,
                3600,  # 1 hour
                json.dumps({
                    "location": current_location,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            return False
        
        # Check if locations are vastly different within short time
        # (Simplified - in production, calculate actual distance and time)
        import json
        last_location = json.loads(last_location_data)
        
        if last_location["location"]["country"] != current_location.get("country"):
            last_time = datetime.fromisoformat(last_location["timestamp"])
            time_diff = (datetime.utcnow() - last_time).total_seconds() / 3600  # hours
            
            if time_diff < 6:  # Less than 6 hours for international travel
                return True
        
        return False
    
    def _is_vpn_or_tor(self, ip_address: str) -> bool:
        """Detect VPN or Tor usage (simplified)"""
        
        if not ip_address:
            return False
        
        # In production, integrate with threat intelligence API
        # This is a simplified check
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Check if it's a known datacenter IP range (VPN indicators)
            # This would typically use a threat intel database
            
            return False  # Placeholder
        except ValueError:
            return False
    
    def _detect_rapid_requests(self, user_id: str) -> bool:
        """Detect unusually rapid requests (velocity check)"""
        
        key = f"request_velocity:{user_id}"
        
        # Increment counter
        count = self.redis.incr(key)
        
        if count == 1:
            # Set expiry on first request (1 minute window)
            self.redis.expire(key, 60)
        
        # More than 30 requests per minute is suspicious
        return count > 30
    
    def _store_risk_assessment(self, user_id: str, risk_score: int, risk_factors: list):
        """Store risk assessment for analytics"""
        
        import json
        
        key = f"risk_history:{user_id}"
        
        assessment = {
            "score": risk_score,
            "factors": risk_factors,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to list (keep last 100 assessments)
        self.redis.lpush(key, json.dumps(assessment))
        self.redis.ltrim(key, 0, 99)
        self.redis.expire(key, 2592000)  # 30 days