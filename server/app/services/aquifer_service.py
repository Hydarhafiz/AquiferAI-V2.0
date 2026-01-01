# app/services/aquifer_service.py

import re
import json
import statistics
import math
from datetime import datetime
from typing import Dict, List, Any, Optional # Add Any and Optional
from uuid import UUID
from app.services.ollama_service import AI_CHATBOT_MODEL, GENERATE_CYPHER_MODEL, query_ollama_with_history
from app.core.neo4j import execute_cypher_query
from app.utils.debug_logger import log_query_debug
from app.utils.cypher_validator import validate_cypher
from app.services.risk_service import assess_risk, convert_permeability_to_md, convert_record_for_display
from app.utils.setup_prompt import ANALYSIS_SYSTEM, CYPHER_SYSTEM_PROMPT
import logging # Import the logging module

logger = logging.getLogger(__name__)

class QueryContext:
    def __init__(self):
        self.parameters = {}
        self.entities = {}

    def update(self, new_parameters: dict, new_entities: dict):
        # Update parameters with new values, don't overwrite existing ones with None
        for key, value in new_parameters.items():
            if value is not None:
                self.parameters[key] = value

        # Update entities
        self.entities.update(new_entities)

    def get_context(self):
        return {
            "parameters": self.parameters.copy(),
            "entities": self.entities.copy()
        }

def calculate_statistics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enhanced statistics with z-score calculation"""
    if not records:
        return {}

    # Normalize record keys: convert 'a.Porosity' to 'Porosity'
    normalized_records = []
    for record in records:
        normalized_record = {}
        for key, value in record.items():
            # Strip common prefixes (e.g., 'a.OBJECTID' -> 'OBJECTID')
            clean_key = key.split('.')[-1]
            normalized_record[clean_key] = value
        normalized_records.append(normalized_record)

    # Now, work with normalized_records
    # Get actual existing properties from the first normalized record (assuming consistent keys)
    if not normalized_records: return {} # Handle empty normalized_records after filtering
    existing_props = list(normalized_records[0].keys())

    stats = {}
    numerical_props = [prop for prop in [
        "Porosity", "Permeability", "Depth", "Thickness",
        "Recharge", "Lake_area", "Parameter_area"
    ] if prop in existing_props]

    for prop in numerical_props:
        values = [rec.get(prop) for rec in normalized_records if rec.get(prop) is not None]
        if not values:
            continue

        # IMPORTANT: Convert Permeability to mD for statistical calculations here
        if prop == "Permeability":
            values = [convert_permeability_to_md(v) for v in values] # Use the function from risk_service
            values = [v for v in values if v is not None] # Filter out Nones if any from conversion

        if not values: # Check again after conversion, if all became None
            continue

        # Basic statistics
        mean = statistics.mean(values)
        min_val = min(values)
        max_val = max(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0

        stats[prop] = {
            "count": len(values),
            "mean": mean,
            "min": min_val,
            "max": max_val,
            "std_dev": std_dev
        }

        # Percentiles
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        percentiles = {5: 0, 25: 0, 50: 0, 75: 0, 95: 0}
        for p_val in percentiles.keys(): # Renamed 'p' to 'p_val' to avoid conflict with 'prop'
            idx = max(0, min(n-1, int(n * p_val / 100)))
            percentiles[p_val] = sorted_vals[idx]

        stats[prop].update({f"p{p_val}": val for p_val, val in percentiles.items()})

        # Z-scores and outliers
        if std_dev > 0: # Use normalized_records length
            outliers = []
            for rec in normalized_records: # Iterate through normalized records
                # Need to convert permeability here too for outlier check if prop is Permeability
                value_for_z_score = rec.get(prop)
                if prop == "Permeability" and value_for_z_score is not None:
                    value_for_z_score = convert_permeability_to_md(value_for_z_score)

                if value_for_z_score is not None:
                    z = (value_for_z_score - mean) / std_dev
                    if abs(z) > 2.5:  # Significant outlier
                        outliers.append({
                            "OBJECTID": rec.get("OBJECTID"), # Assuming OBJECTID is also normalized
                            "value": rec[prop], # Keep original value here, or decide to show converted
                            "z_score": z
                        })
            if outliers:
                stats[prop]["outliers"] = outliers

    # Add risk assessment to statistics
    if normalized_records:
        stats["risk"] = {}
        for prop in ["Depth", "Porosity", "Permeability", "Thickness", "Recharge", "Lake_area"]:
            # Check if the property exists in the first record (or any record)
            if prop in normalized_records[0]:
                values_for_risk = [rec.get(prop) for rec in normalized_records if rec.get(prop) is not None]
                if values_for_risk:
                    risk_counts = {"low_risk": 0, "medium_risk": 0, "high_risk": 0}
                    for value in values_for_risk:
                        # Ensure assess_risk gets the raw value, it converts internally
                        risk_level, _ = assess_risk(prop, value)
                        if risk_level in risk_counts:
                            risk_counts[risk_level] += 1

                    # Changed to store counts instead of percentages
                    stats["risk"][prop] = {
                        "low_risk_count": risk_counts["low_risk"],
                        "medium_risk_count": risk_counts["medium_risk"],
                        "high_risk_count": risk_counts["high_risk"],
                        "total_aquifers_assessed": len(values_for_risk) # Add total for context
                    }

    return stats


async def generate_aquifer_summary(
    user_prompt: str,
    chat_history: Optional[List[Dict[str, str]]] = None # Now explicitly passed
) -> dict:
    """Core processing flow: Prompt → Cypher → Neo4j → AI Summary with Stats"""
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "user_prompt": user_prompt,
        "generated_cypher": None,
        "validation_result": None,
        "execution_result": None,
        "record_count": 0,
        "record_sample": [],
        "ai_response": None,
        "error": None,
        "statistics": None
    }

    if chat_history is None:
        chat_history = [] # Ensure it's an empty list if not provided

    records: List[Dict[str, Any]] = [] # Initialize records outside try for broader scope
    objectids: List[str] = [] # Initialize objectids outside try
    cypher_query: Optional[str] = None # Initialize cypher_query here

    try:
        # --- NEW LOGIC START ---
        # 1. First, attempt to get a Cypher query from the LLM, passing the full chat history
        # and explicitly using the Cypher generation model and its system prompt.
        llm_raw_response_for_cypher_attempt: str = await query_ollama_with_history(
            chat_history + [{"role": "user", "content": user_prompt}], # This is the full context for LLM
            model=GENERATE_CYPHER_MODEL,
            system_prompt=CYPHER_SYSTEM_PROMPT
        )
        debug_info["llm_raw_response_for_cypher_attempt"] = llm_raw_response_for_cypher_attempt

        # Attempt to extract Cypher query from the LLM's response
        cypher_match = re.search(r"```cypher\n(.*?)```", llm_raw_response_for_cypher_attempt, re.DOTALL)
        cypher_query = cypher_match.group(1).strip() if cypher_match else None
        debug_info["generated_cypher"] = cypher_query

        ai_response_content = "I could not process that request." # Default fallback, will be overwritten
        

        if cypher_query:
            logger.info(f"Potential Cypher query extracted: \n{cypher_query}")

            # Validate query safety
            is_valid, validation_msg = validate_cypher(cypher_query)
            debug_info["validation_result"] = validation_msg

            if not is_valid:
                logger.warning(f"Invalid Cypher generated: {validation_msg}")
                ai_response_content = f"Invalid query: {validation_msg}. Please rephrase your question."
                debug_info["ai_response"] = ai_response_content
                debug_info["error"] = "Invalid Cypher"
                return {
                    "ai_response": ai_response_content,
                    "error": "Invalid Cypher",
                    "cypher_queries": [cypher_query] if cypher_query else [], # <-- Change key to 'cypher_queries' and wrap in a list
                    "record_count": 0, # Ensure these are present
                    "statistics": {},
                    "objectids": []
                }

            logger.info(f"Validated Cypher:\n{cypher_query}")

            # Execute against Neo4j
            try:
                records = execute_cypher_query(cypher_query, {})
                debug_info["execution_result"] = f"Returned {len(records)} records"
                debug_info["record_count"] = len(records)
                debug_info["record_sample"] = records[:3]

                if not records:
                    ai_response_content = "No matching aquifers found."
                    debug_info["ai_response"] = ai_response_content
                    debug_info["error"] = "No results"
                    return {
                        "ai_response": ai_response_content,
                        "error": "No results",
                        "cypher_queries": [cypher_query] if cypher_query else [], # <-- Change key to 'cypher_queries' and wrap in a list
                        "record_count": 0, # Ensure these are present
                        "statistics": {},
                        "objectids": []
                    }
                
                # Extract OBJECTIDs
                for record in records:
                    objid = record.get("OBJECTID") or record.get("a.OBJECTID")
                    if objid is not None:
                        objectids.append(str(objid)) # Ensure objectids are strings

                # Determine query type (existing logic)
                is_single = len(records) == 1
                is_comparison = "compare" in user_prompt.lower() or " vs " in user_prompt.lower()
                is_filter = any(op in user_prompt.lower() for op in ["<", ">", "<=", ">=", "=", "filter", "where"])
                is_ranking = "top" in user_prompt.lower() or "rank" in user_prompt.lower()

                # Prepare records for AI analysis (existing logic)
                normalized_records_for_ai_prompt = []
                for record in records:
                    processed_record = {}
                    for key, value in record.items():
                        clean_key = key.split('.')[-1]
                        processed_record[clean_key] = value

                    for prop_name_for_risk in ["Depth", "Porosity", "Permeability", "Thickness", "Recharge", "Lake_area"]:
                        if prop_name_for_risk in processed_record and processed_record[prop_name_for_risk] is not None:
                            risk_level, _ = assess_risk(prop_name_for_risk, processed_record[prop_name_for_risk])
                            processed_record[f"{prop_name_for_risk}_risk"] = risk_level

                    final_record_for_ai = convert_record_for_display(processed_record)
                    normalized_records_for_ai_prompt.append(final_record_for_ai)

                # Calculate statistics (existing logic)
                stats = {"overall": {}, "by_basin": {}, "by_country": {}, "by_aquifer": {}}
                stats["overall"] = calculate_statistics(records)

                if is_single:
                    single_aquifer_record_display = normalized_records_for_ai_prompt[0]
                    stats["by_aquifer"] = {
                        single_aquifer_record_display.get("OBJECTID"): {
                            "properties": {
                                prop: value for prop, value in single_aquifer_record_display.items()
                                if isinstance(value, (int, float, str)) or prop.endswith('_risk')
                            }
                        }
                    }
                elif is_comparison:
                    if any("basin" in key.lower() for key in records[0].keys()) or any("matchedBasin" in key for key in records[0].keys()):
                        basin_groups = {}
                        for record in records:
                            basin = record.get("basin_name") or record.get("b.name") or record.get("matchedBasin.name")
                            if basin:
                                basin_groups.setdefault(basin, []).append(record)
                        for basin, basin_records in basin_groups.items():
                            stats["by_basin"][basin] = calculate_statistics(basin_records)

                    if any("country" in key.lower() for key in records[0].keys()) or any("matchedGeoNode" in key for key in records[0].keys()):
                        country_groups = {}
                        for record in records:
                            country = record.get("country_name") or record.get("c.name") or record.get("matchedGeoNode.name")
                            if country:
                                country_groups.setdefault(country, []).append(record)
                        for country, country_records in country_groups.items():
                            stats["by_country"][country] = calculate_statistics(country_records)

                if is_ranking:
                    ranked_props = []
                    if "recharge" in user_prompt.lower(): ranked_props.append("Recharge")
                    if "porosity" in user_prompt.lower(): ranked_props.append("Porosity")
                    if "permeability" in user_prompt.lower(): ranked_props.append("Permeability")
                    if "depth" in user_prompt.lower(): ranked_props.append("Depth")
                    if "thickness" in user_prompt.lower(): ranked_props.append("Thickness")

                    if not ranked_props:
                        ranked_props = ["Porosity", "Permeability", "Depth", "Thickness", "Recharge"]

                    stats["ranking"] = {}

                    normalized_records_for_ranking = []
                    for record in records:
                        normalized_record = {}
                        for key, value in record.items():
                            clean_key = key.split('.')[-1]
                            normalized_record[clean_key] = value
                        if "Permeability" in normalized_record and normalized_record["Permeability"] is not None:
                            normalized_record["Permeability"] = convert_permeability_to_md(normalized_record["Permeability"])
                        normalized_records_for_ranking.append(normalized_record)

                    for prop in ranked_props:
                        if any(prop in r for r in normalized_records_for_ranking):
                            is_top_ranking = "top" in user_prompt.lower() or "highest" in user_prompt.lower()
                            is_bottom_ranking = "bottom" in user_prompt.lower() or "lowest" in user_prompt.lower()

                            sorted_records = sorted(
                                [r for r in normalized_records_for_ranking if r.get(prop) is not None],
                                key=lambda x: x[prop],
                                reverse=is_top_ranking
                            )

                            limit = 10
                            top_results = []
                            bottom_results = []

                            if is_top_ranking:
                                top_results = sorted_records[:limit]
                            elif is_bottom_ranking:
                                bottom_results = sorted_records[-limit:]
                            else:
                                top_results = sorted_records[:limit]

                            stats["ranking"][prop] = {
                                "properties": [prop],
                                "top": [{"OBJECTID": r.get("OBJECTID"), prop: r[prop]} for r in top_results],
                                "bottom": [{"OBJECTID": r.get("OBJECTID"), prop: r[prop]} for r in bottom_results]
                            }

                if is_filter:
                    filter_stats = {}
                    normalized_records_for_filter = []
                    for record in records:
                        normalized_record = {}
                        for key, value in record.items():
                            clean_key = key.split('.')[-1]
                            normalized_record[clean_key] = value
                        if "Permeability" in normalized_record and normalized_record["Permeability"] is not None:
                            normalized_record["Permeability"] = convert_permeability_to_md(normalized_record["Permeability"])
                        normalized_records_for_filter.append(normalized_record)

                    if "depth" in user_prompt.lower():
                        depth_values = [r.get("Depth") for r in normalized_records_for_filter if r.get("Depth") is not None]
                        if depth_values:
                            filter_stats["Depth"] = {
                                "min": min(depth_values),
                                "max": max(depth_values),
                                "mean": statistics.mean(depth_values),
                                "count": len(depth_values)
                            }
                    if "permeability" in user_prompt.lower():
                        permeability_values = [r.get("Permeability") for r in normalized_records_for_filter if r.get("Permeability") is not None]
                        if permeability_values:
                            filter_stats["Permeability"] = {
                                "min": min(permeability_values),
                                "max": max(permeability_values),
                                "mean": statistics.mean(permeability_values),
                                "count": len(permeability_values)
                            }
                    stats["filter"] = filter_stats
                
                logger.debug(f"\n--- DEBUG: Statistics calculated and sent to AI ---\n{json.dumps(stats, indent=2)}\n----------------------------------------------------\n")
                debug_info["statistics"] = stats

                # Prepare data for final AI analysis (this is for the *second* LLM call)
                results_str = json.dumps(normalized_records_for_ai_prompt[:3], indent=2)

                ai_prompt_content = f"""
                    ### Geological Data Analysis Request
                    **User Query**: {user_prompt}
                    **Database Results** ({len(records)} records retrieved):
                    {results_str}

                    **Statistical Summary**:
                    {json.dumps(stats, indent=2)}

                    **Response Requirement**: 
                    - Answer directly based on query type
                    - Include ONLY relevant analysis
                    - Flag unsupported topics immediately
                """
                
                # Use the chat_history + the current prompt and data to get the final AI response
                ai_response_content = await query_ollama_with_history(
                    chat_history + [{"role": "user", "content": ai_prompt_content}],
                    model=AI_CHATBOT_MODEL, # Explicitly use the general chatbot model
                    system_prompt=ANALYSIS_SYSTEM # Pass the analysis system prompt here
                )
                debug_info["ai_response"] = ai_response_content

            except Exception as e:
                debug_info["error"] = f"Execution or processing failed: {str(e)}"
                logger.error(f"Execution or processing failed: {e}", exc_info=True)
                ai_response_content = f"Database query or data processing failed: {str(e)}. Please check the logs."
                debug_info["ai_response"] = ai_response_content
                
        else:
            # --- If no Cypher query was generated/extracted ---
            logger.info("No Cypher query detected. Returning LLM's direct conceptual response.")
            # Use the LLM's raw response directly as the AI response
            ai_response_content = llm_raw_response_for_cypher_attempt
            debug_info["ai_response"] = ai_response_content
            debug_info["statistics"] = {} # No stats if no DB interaction
            debug_info["objectids"] = [] # No objectids if no DB interaction

            # Add a check for "Invalid query" within the LLM's raw response itself
            # If the LLM explicitly said it can't answer, then use a generic message
            if "invalid query" in llm_raw_response_for_cypher_attempt.lower() or \
               "cannot process that request" in llm_raw_response_for_cypher_attempt.lower() or \
               "not found" in llm_raw_response_for_cypher_attempt.lower():
                ai_response_content = "I'm sorry, I couldn't process that request based on the available information or my current capabilities. Please try rephrasing or asking a different question."
                debug_info["ai_response"] = ai_response_content
                debug_info["error"] = "LLM indicated inability to answer conceptually."
        # --- NEW LOGIC END ---

        return {
            "cypher_queries": [cypher_query] if cypher_query else [], # <-- Change key to 'cypher_queries' and wrap in a list
            "record_count": len(records), # This will be 0 if no Cypher was executed
            "ai_response": ai_response_content,
            "statistics": debug_info.get("statistics", {}), # Ensure stats is returned even if empty
            "objectids": list(set(objectids)) # Ensure objectids is returned even if empty
        }

    except Exception as e:
        debug_info["error"] = f"Unexpected error in aquifer_summary: {str(e)}"
        logger.error(f"Unexpected error in aquifer_summary: {e}", exc_info=True)
        ai_response_content = "System error occurred. Please try again later."
        debug_info["ai_response"] = ai_response_content
        return {
            "ai_response": ai_response_content,
            "error": str(e)
        }
    finally:
        log_query_debug(debug_info)

