# src/backend/utils/cypher_validator.py

import re

ALLOWED_PATTERNS = [
    r"MATCH\s+\(?\w+:?Aquifer\)?", # CHANGE: From [a-z] to \w+
    r"MATCH\s+\(\w+:?Basin\)?",    # Consider changing this as well for consistency
    r"RETURN\s+\w+\.OBJECTID",     # CHANGE: From a\.OBJECTID to \w+\.OBJECTID
    r"-\[:\w+_PROPERTY\]->",
    r"-\[:LOCATED_IN_BASIN\]->",
    r"-\[:PART_OF\]->",
    r"-\[:IS_LOCATED_IN_COUNTRY\]->",
    r"-\[:LOCATED_IN_CONTINENT\]->",
    r"WHERE\s+\w+\.(value|name)",  # CHANGE: From \w\.(value|name) to \w+\.(value|name)
    r"ORDER BY\s+\w+\.value",      # CHANGE: From \w\.value to \w+\.value
    r"LIMIT \d+",
    r"CALL db\.index\.fulltext\.queryNodes"
]

BLOCKED_PATTERNS = [
    r"[Cc][Rr][Ee][Aa][Tt][Ee]",
    r"[Dd][Ee][Ll][Ee][Tt][Ee]",
    r"[Ss][Ee][Tt]",
    r"[Mm][Ee][Rr][Gg][Ee]",
    r";\s*;",
    r"apoc\.",
    r"admin",
    r"RETURN\s*\{",  # Block map projections in RETURN
    r"WITH\s*\{",    # Block map projections in WITH
]

PROPERTY_NODES = {"depth", "lakearea", "permeability", "porosity", "recharge", "thickness"}

def validate_cypher(query: str) -> tuple:
    """Enhanced validation with detailed feedback"""
    if not query:
        return False, "Empty query generated"
    
    query_lower = query.lower()
    
    # Block dangerous operations
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, query_lower):
            return False, f"Blocked pattern detected: {pattern}"
    
    # Must access Aquifer node (more flexible pattern)
    aquifer_patterns = [
        r"match\s*\(\w+:?aquifer\)",  # CHANGE: From [a-z] to \w+
        r"match\s*\(\w+:?aquifer\s*\{",  # CHANGE: From [a-z] to \w+
        r"call\s+.*match\s*\(\w+:?aquifer\)",  # CHANGE: From [a-z] to \w+
        r"with\s+.*match\s*\(\w+:?aquifer\)"  # CHANGE: From [a-z] to \w+
    ]
    
    if not any(re.search(pattern, query_lower) for pattern in aquifer_patterns):
        return False, "Aquifer node not accessed"
    
    # Must include RETURN clause
    if "return" not in query_lower:
        return False, "Missing RETURN clause"
    
    # This specific regex for OBJECTID comparison in basin matching seems overly strict and possibly problematic.
    # The example query for OBJECTID comparison for a1 and a2 uses "OBJECTID: "123"" not "[b-z].OBJECTID"
    # Revisit this rule carefully. If it's intended to block dynamic OBJECTID comparisons in basin matching,
    # it might still catch valid queries depending on the LLM's output.
    # For now, let's just make it allow for \w+
    if re.search(r"MATCH\s*\(\w+:Aquifer\)-\w*:LOCATED_IN_BASIN\w*->\s*\(\w+:Basin\)\s*WHERE\s+\w+\.OBJECTID", query, re.IGNORECASE):
        # This rule needs careful review. If its intent is to prevent filtering a BASIN by its OBJECTID (which Basins don't have usually), it's fine.
        # But if it's broadly trying to prevent OBJECTID comparisons in the context of basins, it might be too restrictive.
        # Given the new example query uses `a1.OBJECTID` and `a2.OBJECTID`, this specific pattern likely isn't the direct cause
        # of the current comparison query failing validation, *unless* the regex `[b-z]` was problematic as well.
        # Let's update `[b-z]` to `\w+` for consistency, but keep the core logic if it serves a specific security purpose.
        return False, "OBJECTID comparison prohibited in basin matching" # Still, double check if this rule is truly needed for valid use cases.
    
    # Check for comparison queries
    comparison_keywords = ["compare", "versus", "vs", "different", "both", "multiple"]
    if any(term in query.lower() for term in comparison_keywords):
        # Your specific comparison validation rules.
        # The query you provided does *not* use UNWIND.
        # So, the "Comparison queries require UNWIND pattern" rule is failing it.
        # The LLM is generating direct MATCHes for specific OBJECTIDs, which is fine for direct comparisons.
        # You need to decide if UNWIND is *always* required for *all* comparison queries, or just for dynamic/unknown lists of entities.
        # For "Compare aquifer ID 123 and aquifer 456", UNWIND is not strictly necessary and the generated query is efficient.
        
        # Option 1: Remove or relax the UNWIND requirement for specific ID comparisons
        # If the LLM produces direct matches for explicit IDs (like your example), then UNWIND is not needed.
        # If UNWIND is ONLY for comparing *lists* of dynamic entities, then this rule is too broad.
        # I'd suggest relaxing this for now, or making it conditional.
        if "UNWIND" not in query and not re.search(r"OBJECTID:\s*\"?\d+\"?", query): # Add a condition for direct OBJECTID matches
             # This means if it contains UNWIND OR it directly queries OBJECTIDs
             # This is a bit complex for a single regex. Easier to remove if not strictly needed.
             pass # Removed the UNWIND requirement for now to allow your working query
        # else:
        #    return False, "Comparison queries require UNWIND pattern" # Keep this line if you want UNWIND for all comparisons

        # The generated query has only one RETURN statement, so this should pass
        if query.count("RETURN") > 1:
            return False, "Comparison queries must have single RETURN"
            
        # The generated query does not include "term_type".
        # This rule is designed for your UNWIND comparison example:
        # "RETURN comparison_term, term_type, OBJECTID, Porosity, Permeability, ..."
        # For a direct comparison like 'aquifer 123 and 456', there's no 'term_type' as they are both Aquifers.
        # You need to make this rule conditional or remove it for specific ID comparisons.
        if "term_type" not in query:
            # If your comparison queries are always expected to come from a UNWINDed list
            # where you distinguish between 'basin', 'country', 'continent', etc., then this rule makes sense.
            # For a direct comparison of two Aquifer OBJECTIDs, 'term_type' is irrelevant.
            # So, for now, I'll comment out this check for direct OBJECTID comparisons.
            pass # Removed the term_type requirement for now
            
    return True, "Validation passed"