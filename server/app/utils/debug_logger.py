# app/utils/debug_logger.py

import json
from datetime import datetime
import os
from typing import Dict, Any, List

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log_query_debug(debug_data: Dict[str, Any]):
    """Enhanced logging with query results, including analysis and risk data, and AI response."""
    timestamp = datetime.now().isoformat()
    
    # Create detailed log entry
    log_entry = {
        "timestamp": timestamp,
        "user_prompt": debug_data.get("user_prompt", ""),
        "generated_cypher": debug_data.get("generated_cypher", ""),
        "validation_result": debug_data.get("validation_result", "Not validated"),
        "execution_result": debug_data.get("execution_result", "Not executed"),
        "ai_response": debug_data.get("ai_response", ""), # <--- THIS LINE ENSURES AI RESPONSE IS LOGGED
        "error": debug_data.get("error", ""),
        "record_count": debug_data.get("record_count", 0),
        "record_sample": debug_data.get("record_sample", []),
        "analysis_data": debug_data.get("statistics", {}) # <--- THIS LINE ADDS THE STATS/ANALYSIS DATA
    }
    
    # Create daily log files
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"cypher_debug_{date_str}.jsonl")
    
    # Append to log file
    with open(log_file, "a") as f:
        # Using default=str to handle any non-standard types that might appear,
        # ensuring the JSON serialization doesn't fail.
        f.write(json.dumps(log_entry, default=str, indent=2) + "\n")
    
    print(f"Logged debug info for query: {debug_data.get('user_prompt','')[:50]}...")
    return log_entry