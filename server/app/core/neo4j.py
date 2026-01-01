import traceback
from neo4j import GraphDatabase
import os
import json
from neo4j.spatial import Point
from neo4j.graph import Node  # Import Node from the neo4j.graph module

class Neo4jDriver:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "neo4j://172.28.96.1:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "Hydarhakim@12")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        print(f"Connected to Neo4j at {self.uri}")

    def execute_query(self, query, parameters=None):
        """Execute a Cypher query with optional parameters"""
        with self.driver.session() as session:
            # Log the query being executed
            print(f"Executing Cypher: {query}")
            if parameters:
                print(f"With parameters: {json.dumps(parameters, indent=2)}")
            
            result = session.run(query, parameters=parameters or {})
            
            # Convert to list of dicts for better inspection
            records = [dict(record) for record in result]
            
            # Log result summary
            result_summary = {
                "result_count": len(records),
                "first_record": records[0] if records else None,
                "field_names": list(result.keys()) if records else []
            }
            print(f"Query returned {len(records)} records")
            
            return records

# Singleton instance
neo4j_driver = Neo4jDriver()

def execute_cypher_query(query: str, parameters=None):
    try:
        # Clean parameters - remove empty values
        clean_params = {}
        if parameters:
            for key, value in parameters.items():
                if value is not None and value != "":
                    clean_params[key] = value
        
        # Use the instance of Neo4jDriver to execute the query
        records = neo4j_driver.execute_query(query, clean_params)
        
        # Process spatial data
        processed_records = []
        for record in records:
            processed_record = {}
            for key, value in record.items():
                if isinstance(value, Node):
                    # Convert node to dictionary of properties
                    processed_record[key] = dict(value.items())
                
                elif isinstance(value, Point):
                    # Convert Neo4j point to GeoJSON-like structure
                    srid = value.srid
                    crs = "EPSG:4326" if srid == 4326 else f"SRID:{srid}"
                    
                    processed_record[key] = {
                        "type": "Point",
                        "coordinates": [value.x, value.y],
                        "crs": {
                            "name": crs,
                            "type": "name",
                            "properties": {"name": crs}
                        }
                    }
                elif isinstance(value, str) and ("POINT" in value or "POLYGON" in value or "MULTIPOLYGON" in value):
                    # Preserve WKT strings
                    processed_record[key] = value
                else:
                    processed_record[key] = value
            processed_records.append(processed_record)
        
        print(f"Processed {len(processed_records)} records")
        return processed_records
    except Exception as e:
        # Capture full error details
        error_info = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "query": query,
            "parameters": clean_params,
            "stack_trace": traceback.format_exc()
        }
        print(f"Neo4j Error: {json.dumps(error_info, indent=2)}")
        return []  # Return empty list instead of None
