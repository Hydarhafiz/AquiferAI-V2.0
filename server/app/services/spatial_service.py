# src/backend/services/spatial_service.py
import json
import re
from app.core.neo4j import execute_cypher_query
from geojson import FeatureCollection, Feature, Point, Polygon, MultiPolygon
from app.services.risk_service import assess_risk, convert_permeability_to_md

def convert_to_geojson(records, properties_requested):
    """Convert database records to GeoJSON with proper coordinate handling and add risk properties."""
    features = []
    print(f"Converting {len(records)} records to GeoJSON")

    for record in records:
        props = {}
        original_numerical_values = {} # To store raw values for risk assessment

        for prop_key_with_alias in record.keys():
            prop_name = prop_key_with_alias.split('.')[-1]
            value = record.get(prop_key_with_alias)
            props[prop_name] = value
            if prop_name in ["Porosity", "Permeability", "Depth", "Thickness", "Recharge", "Lake_area"]:
                original_numerical_values[prop_name] = value

        for prop_name, raw_value in original_numerical_values.items():
            if raw_value is not None:
                risk_level, _ = assess_risk(prop_name, raw_value)
                props[f"{prop_name}_risk"] = risk_level

        obj_id = props.get("OBJECTID")

        location = props.get("Location")
        if location and isinstance(location, dict) and 'coordinates' in location:
            coords = location['coordinates']
            if isinstance(coords, list) and len(coords) >= 2:
                try:
                    # GeoJSON is [longitude, latitude]
                    # Neo4j point is typically {latitude: ..., longitude: ...} or [lon, lat]
                    # Assuming coords[0] is longitude and coords[1] is latitude based on the error: '(-68...' which is longitude
                    geometry = Point((coords[0], coords[1])) # Ensure order is lon, lat
                    feature = Feature(geometry=geometry, properties=props, id=obj_id)
                    features.append(feature)
                    continue
                except Exception as e:
                    print(f"Error creating point feature for OBJECTID {obj_id} (Location: {location}): {e}")

        boundary = props.get("Boundary_coordinates")
        if boundary and isinstance(boundary, str):
            try:
                if boundary.startswith("MULTIPOLYGON"):
                    multi_poly_coords = []
                    # Find all polygon strings like '((x y, x y,...), (x y,...))'
                    # Use a non-greedy regex to match balanced parentheses for each polygon
                    # This regex is a bit tricky, aiming for content between outer (())
                    # The general format is MULTIPOLYGON(((ring)),((ring)))
                    
                    # More robust parsing for MULTIPOLYGON:
                    # Extract the content inside MULTIPOLYGON (...)
                    multi_poly_content_match = re.match(r'MULTIPOLYGON\s*\((.*)\)', boundary)
                    if multi_poly_content_match:
                        multi_poly_content = multi_poly_content_match.group(1)
                        # Split by ')), ((' to get individual polygon parts
                        polygon_parts = re.findall(r'\(\((.*?)\)\)', multi_poly_content)

                        for polygon_part in polygon_parts:
                            polygon_coords = []
                            # Each polygon_part can have multiple rings, separated by '), ('
                            ring_strs = re.findall(r'\((.*?)\)', f"({polygon_part})")
                            for ring_str in ring_strs:
                                # Now, split each ring string by ', ' to get individual "x y" pairs
                                point_strs = ring_str.split(',')
                                ring_coords = []
                                for point_str in point_strs:
                                    parts = point_str.strip().split()
                                    if len(parts) == 2:
                                        try:
                                            ring_coords.append([float(parts[0]), float(parts[1])])
                                        except ValueError as ve:
                                            print(f"Inner point conversion error for OBJECTID {obj_id} in MULTIPOLYGON: '{point_str}' -> {ve}")
                                            raise # Re-raise to catch in outer try-except
                                    else:
                                        print(f"Warning: Unexpected point format in MULTIPOLYGON for OBJECTID {obj_id}: '{point_str}'")
                                if ring_coords:
                                    polygon_coords.append(ring_coords)
                            if polygon_coords:
                                multi_poly_coords.append(polygon_coords)

                    if multi_poly_coords:
                        geometry = MultiPolygon(multi_poly_coords)
                        features.append(Feature(geometry=geometry, properties=props, id=obj_id))
                    else:
                        print(f"Warning: Could not parse MULTIPOLYGON coordinates for OBJECTID {obj_id}: {boundary}")

                elif boundary.startswith("POLYGON"):
                    # This POLYGON parsing logic seems mostly correct for a single polygon with inner rings.
                    # The regex for POLYGON also needs to be careful not to include outer parentheses if the WKT is like POLYGON((...))
                    # It relies on splitting `((` and `))`, which is specific. Let's make it more robust.

                    # Extract content inside POLYGON(...)
                    poly_content_match = re.match(r'POLYGON\s*\((.*)\)', boundary)
                    if poly_content_match:
                        poly_content = poly_content_match.group(1)
                        rings = []
                        # Find all ring strings like '(x y, x y, ...)'
                        ring_strs = re.findall(r'\((.*?)\)', poly_content)
                        for ring_str in ring_strs:
                            ring_coords = []
                            # Split each ring string by ', ' to get individual "x y" pairs
                            point_strs = ring_str.split(',')
                            for point_str in point_strs:
                                parts = point_str.strip().split()
                                if len(parts) == 2:
                                    try:
                                        ring_coords.append([float(parts[0]), float(parts[1])])
                                    except ValueError as ve:
                                        print(f"Inner point conversion error for OBJECTID {obj_id} in POLYGON: '{point_str}' -> {ve}")
                                        raise # Re-raise to catch in outer try-except
                                else:
                                    print(f"Warning: Unexpected point format in POLYGON for OBJECTID {obj_id}: '{point_str}'")
                            if ring_coords:
                                rings.append(ring_coords)
                        
                        if rings:
                            geometry = Polygon(rings)
                            features.append(Feature(geometry=geometry, properties=props, id=obj_id))
                        else:
                            print(f"Warning: Could not parse POLYGON coordinates for OBJECTID {obj_id}: {boundary}")
                    else:
                        print(f"Warning: Could not match POLYGON content for OBJECTID {obj_id}: {boundary}")

            except Exception as e:
                print(f"Error parsing boundary for OBJECTID {obj_id}: {boundary}\nError: {e}")

    print(f"Created {len(features)} GeoJSON features")
    return FeatureCollection(features)

def get_aquifer_spatial_data(objectids: list = None, basin: str = None, properties: list = None):
    # Build Cypher query with aliases
    query = ""
    params = {}
    where_clauses = []

    # Handle basin query
    if basin:
        query = """
        CALL db.index.fulltext.queryNodes("basinSearch", $basin)
        YIELD node AS b, score
        WITH b, score ORDER BY score DESC LIMIT 1
        MATCH (a)-[:LOCATED_IN_BASIN]->(b)
        """
        params["basin"] = basin
    else:
        query = "MATCH (a:Aquifer)\n"

    # Add OBJECTID filtering
    if objectids:
        # CONVERT EACH OBJECTID TO A STRING FOR THE IN CLAUSE
        # Assuming objectids are passed as a list of integers from the request
        string_objectids = [str(oid) for oid in objectids]
        where_clauses.append(f"a.OBJECTID IN $objectids_param") # Use a parameter for safety and correctness
        params["objectids_param"] = string_objectids # Add the list of strings to parameters

    # Add WHERE clause if needed
    if where_clauses:
        query += "WHERE " + " AND ".join(where_clauses) + "\n"

    # Define a default set of properties to always include for spatial representation
    core_properties_for_spatial = [
        "OBJECTID", "Location", "Boundary_coordinates", # Add Boundary_coordinates here explicitly
        "Porosity", "Permeability", "Depth", "Thickness", "Recharge", "Lake_area"
    ]

    # Combine requested properties with core properties, ensuring no duplicates.
    all_properties_to_fetch = list(set(core_properties_for_spatial + (properties if properties else [])))

    return_props = []
    for prop in all_properties_to_fetch:
        return_props.append(f"a.{prop} AS `{prop}`")

    query += f"RETURN {', '.join(return_props)}"

    print(f"Executing spatial query:\n{query}")
    print(f"With parameters: {params}")

    # Execute query
    results = execute_cypher_query(query, params)
    print(f"Retrieved {len(results)} records from database")

    geojson = convert_to_geojson(results, properties or [])
    return geojson
