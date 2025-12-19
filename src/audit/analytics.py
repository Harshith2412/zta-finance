"""
Security Analytics
Analyze audit logs for security insights and anomalies
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

from config.logging import get_logger

logger = get_logger(__name__)


class SecurityAnalytics:
    """Analyze security events and detect anomalies"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def analyze_failed_authentications(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze failed authentication attempts"""
        
        # In production, query from audit logs
        analysis = {
            "total_failures": 0,
            "unique_users": 0,
            "unique_ips": 0,
            "top_users": [],
            "top_ips": [],
            "time_distribution": {}
        }
        
        logger.info("Failed authentication analysis completed")
        return analysis
    
    def detect_brute_force_attempts(
        self,
        threshold: int = 10,
        time_window_minutes: int = 15
    ) -> List[Dict[str, Any]]:
        """Detect potential brute force attacks"""
        
        # In production, analyze Redis or audit logs
        attempts = []
        
        # Check for rapid failed attempts
        pattern = "failed_attempts:*"
        for key in self.redis.scan_iter(match=pattern):
            count = int(self.redis.get(key) or 0)
            
            if count >= threshold:
                username = key.decode().split(':')[1] if isinstance(key, bytes) else key.split(':')[1]
                attempts.append({
                    "username": username,
                    "failed_count": count,
                    "severity": "high" if count > 20 else "medium",
                    "detected_at": datetime.utcnow().isoformat()
                })
        
        if attempts:
            logger.warning(f"Detected {len(attempts)} potential brute force attempts")
        
        return attempts
    
    def analyze_high_risk_transactions(
        self,
        risk_threshold: int = 70
    ) -> List[Dict[str, Any]]:
        """Identify high-risk transactions"""
        
        # In production, query from audit logs
        high_risk_transactions = []
        
        logger.info("High-risk transaction analysis completed")
        return high_risk_transactions
    
    def get_security_score(self, user_id: str) -> Dict[str, Any]:
        """Calculate overall security score for a user"""
        
        score = 100  # Start with perfect score
        factors = {}
        
        # Check MFA status
        # In production, query from database
        factors["mfa_enabled"] = True
        if not factors["mfa_enabled"]:
            score -= 20
        
        # Check recent failed attempts
        key = f"failed_attempts:{user_id}"
        failed_attempts = int(self.redis.get(key) or 0)
        factors["recent_failed_attempts"] = failed_attempts
        
        if failed_attempts > 0:
            score -= min(failed_attempts * 5, 30)
        
        # Check device trust
        # Would check average trust score of user's devices
        factors["trusted_devices"] = 1
        
        # Check recent security events
        factors["recent_security_events"] = 0
        
        return {
            "user_id": user_id,
            "security_score": max(score, 0),
            "risk_level": "low" if score >= 80 else "medium" if score >= 60 else "high",
            "factors": factors,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_user_activity_pattern(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze user's typical activity patterns"""
        
        # In production, analyze audit logs
        pattern = {
            "user_id": user_id,
            "typical_login_hours": [8, 9, 10, 17, 18, 19],
            "typical_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "typical_locations": ["US", "GB"],
            "average_transactions_per_day": 3.5,
            "typical_transaction_amounts": {
                "min": 10.00,
                "max": 1000.00,
                "average": 250.00
            }
        }
        
        return pattern
    
    def detect_anomalies(self, user_id: str, current_activity: Dict[str, Any]) -> List[str]:
        """Detect anomalous behavior"""
        
        anomalies = []
        
        # Get user's typical pattern
        pattern = self.get_user_activity_pattern(user_id)
        
        # Check time of day
        current_hour = datetime.utcnow().hour
        if current_hour not in pattern["typical_login_hours"]:
            anomalies.append("unusual_time")
        
        # Check transaction amount
        if "amount" in current_activity:
            amount = current_activity["amount"]
            if amount > pattern["typical_transaction_amounts"]["max"] * 2:
                anomalies.append("unusual_amount")
        
        # Check location
        if "location" in current_activity:
            location = current_activity["location"]
            if location not in pattern["typical_locations"]:
                anomalies.append("unusual_location")
        
        if anomalies:
            logger.warning(f"Anomalies detected for user {user_id}: {', '.join(anomalies)}")
        
        return anomalies
    
    def generate_security_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_authentications": 0,
                "failed_authentications": 0,
                "successful_authentications": 0,
                "unique_users": 0,
                "total_transactions": 0,
                "high_risk_transactions": 0,
                "security_incidents": 0
            },
            "top_risks": [],
            "recommendations": []
        }
        
        # Add recommendations based on findings
        if report["summary"]["failed_authentications"] > 100:
            report["recommendations"].append({
                "priority": "high",
                "recommendation": "Implement additional rate limiting",
                "reason": "High number of failed authentication attempts detected"
            })
        
        logger.info("Security report generated")
        return report
    
    def get_real_time_threats(self) -> List[Dict[str, Any]]:
        """Get currently active threats"""
        
        threats = []
        
        # Check for brute force attempts
        brute_force = self.detect_brute_force_attempts()
        threats.extend([
            {
                "type": "brute_force",
                "severity": attempt["severity"],
                "target": attempt["username"],
                "detected_at": attempt["detected_at"]
            }
            for attempt in brute_force
        ])
        
        # Check for account lockouts
        # Would check recent lockouts from Redis
        
        return threats
    
    def get_user_risk_timeline(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get historical risk scores for a user"""
        
        # In production, retrieve from stored risk assessments
        key = f"risk_history:{user_id}"
        history_data = self.redis.lrange(key, 0, -1)
        
        timeline = []
        for data in history_data:
            assessment = json.loads(data)
            timeline.append({
                "timestamp": assessment["timestamp"],
                "risk_score": assessment["score"],
                "factors": assessment["factors"]
            })
        
        return timeline