"""
License and limitation checker for the Mega Watermark Bot
"""

import os
import json
from datetime import datetime, timedelta

class LicenseChecker:
    def __init__(self):
        self.limits_file = "usage_limits.json"
        self.load_limits()
    
    def load_limits(self):
        """Load usage limits from file"""
        if os.path.exists(self.limits_file):
            with open(self.limits_file, 'r') as f:
                self.limits = json.load(f)
        else:
            # Initialize with default limits for free version
            self.limits = {
                "daily_watermarks": 0,
                "max_daily_watermarks": 10,  # Free version limit
                "bulk_processes": 0,
                "max_bulk_processes": 2,     # Free version limit
                "last_reset": datetime.now().isoformat(),
                "total_files_processed": 0,
                "max_total_files": 100,      # Free version limit
                "license_type": "free"
            }
            self.save_limits()
    
    def save_limits(self):
        """Save usage limits to file"""
        with open(self.limits_file, 'w') as f:
            json.dump(self.limits, f, indent=2)
    
    def reset_daily_limits(self):
        """Reset daily limits if it's a new day"""
        last_reset = datetime.fromisoformat(self.limits["last_reset"])
        if datetime.now().date() > last_reset.date():
            self.limits["daily_watermarks"] = 0
            self.limits["bulk_processes"] = 0
            self.limits["last_reset"] = datetime.now().isoformat()
            self.save_limits()
    
    def check_watermark_limit(self):
        """Check if user can perform watermarking"""
        self.reset_daily_limits()
        
        if self.limits["daily_watermarks"] >= self.limits["max_daily_watermarks"]:
            return False, f"Daily watermark limit reached ({self.limits['max_daily_watermarks']}). Upgrade to full version for unlimited watermarks."
        
        return True, "OK"
    
    def check_bulk_process_limit(self):
        """Check if user can perform bulk processing"""
        self.reset_daily_limits()
        
        if self.limits["bulk_processes"] >= self.limits["max_bulk_processes"]:
            return False, f"Daily bulk process limit reached ({self.limits['max_bulk_processes']}). Upgrade to full version for unlimited processing."
        
        return True, "OK"
    
    def check_file_limit(self, file_count):
        """Check if user can process this many files"""
        if self.limits["total_files_processed"] + file_count > self.limits["max_total_files"]:
            return False, f"Total file limit would be exceeded. Upgrade to full version for unlimited files."
        
        return True, "OK"
    
    def increment_watermark(self):
        """Increment watermark counter"""
        self.limits["daily_watermarks"] += 1
        self.save_limits()
    
    def increment_bulk_process(self):
        """Increment bulk process counter"""
        self.limits["bulk_processes"] += 1
        self.save_limits()
    
    def increment_files(self, count):
        """Increment total files processed"""
        self.limits["total_files_processed"] += count
        self.save_limits()
    
    def upgrade_to_full(self, license_key=None):
        """Upgrade to full version (placeholder for license validation)"""
        # In a real implementation, you'd validate the license key here
        if license_key == "FULL_VERSION_KEY":  # Replace with real validation
            self.limits["license_type"] = "full"
            self.limits["max_daily_watermarks"] = 999999
            self.limits["max_bulk_processes"] = 999999
            self.limits["max_total_files"] = 999999
            self.save_limits()
            return True, "Successfully upgraded to full version!"
        else:
            return False, "Invalid license key. Contact developer for full version access."

# Global instance
license_checker = LicenseChecker()
