# app/services/risk_service.py
MD_TO_M2 = 9.869233e-16  # 1 mD = 9.869233e-16 m²
RISK_THRESHOLDS = {
    "Depth": {
        "low_risk": (800, 2500),
        "medium_risk": (2500, float('inf')),
        "high_risk": (0, 800)
    },
    "Porosity": {
        "low_risk": (0.20, float('inf')),
        "medium_risk": (0.10, 0.20),
        "high_risk": (0, 0.10)
    },
    "Permeability": {
        "low_risk": (500, float('inf')),
        "medium_risk": (200, 500),
        "high_risk": (0, 200)
    },
    "Thickness": {
        "low_risk": (50, float('inf')),
        "medium_risk": (20, 50),
        "high_risk": (0, 20)
    },
    "Recharge": {
        "low_risk": (0, 0.2),
        "medium_risk": (0.2, 0.5),
        "high_risk": (0.5, float('inf'))
    },
    "Lake_area": {
        "low_risk": (0, 0.0001),
        "medium_risk": (0.0001, 10000),
        "high_risk": (10000, float('inf'))
    }
}
RISK_SOURCES = {
    "Permeability": "(Rasool et al., 2023), (Bentham & Kirby, 2005), (Chadwick et al., n.d.)",
    "Porosity": "(Bentham & Kirby, 2005), (Rasool et al., 2023), (Chadwick et al., n.d.)",
    "Depth": "(Bentham & Kirby, 2005), (Chadwick et al., n.d.), (Li et al., 2024)",
    "Thickness": "(Chadwick et al., n.d.), (Li et al., 2024), (Rasool et al., 2023)",
    "Recharge": "(Chadwick et al., n.d.), (Bentham & Kirby, 2005)",
    "Lake_area": "(Chadwick et al., n.d.), (Bentham & Kirby, 2005)"
}


def convert_permeability_to_md(permeability_log_m2: float) -> float:
    """
    Converts permeability from log10(m^2) to mD.
    Assumes permeability_log_m2 is the base-10 logarithm of permeability in square meters.
    """
    if permeability_log_m2 is None:
        return None
    # Ensure a non-negative value for the exponent in 10**value if it makes sense for your data
    # The negative value like -14.75 is typical for log10 of very small numbers (like permeability in m^2)
    permeability_m2 = 10**permeability_log_m2
    # 1 m^2 = 1 / 9.869233e-16 mD
    permeability_mD = permeability_m2 / 9.869233e-16
    return permeability_mD

def assess_risk(prop, value):
    """Classify risk level based on research thresholds"""
    if prop not in RISK_THRESHOLDS:
        return "unknown", ""
    
    # Special handling for permeability
    if prop == "Permeability":
        value_mD = convert_permeability_to_md(value)
        value = value_mD
    
    for risk_level, (min_val, max_val) in RISK_THRESHOLDS[prop].items():
        if min_val <= value <= max_val:
            return risk_level, RISK_SOURCES[prop]
    
    return "unknown", ""

def generate_risk_report(record):
    """Create structured risk assessment"""
    report = {}
    for prop in ["Depth", "Porosity", "Permeability", "Thickness", "Recharge", "Lake_area"]:
        if prop in record:
            value = record[prop]
            display_value = value
            unit = ""
            
            # Handle special conversions
            if prop == "Permeability":
                # Convert to mD for display
                display_value = convert_permeability_to_md(value)
                unit = "mD"
            elif prop == "Porosity":
                display_value = value * 100  # Convert to percentage
                unit = "%"
            elif prop in ["Depth", "Thickness"]:
                unit = "m"
            elif prop == "Recharge":
                unit = "m/yr"
            elif prop == "Lake_area":
                unit = "m²"
                
            risk_level, source = assess_risk(prop, value)
            report[prop] = {
                "value": display_value,
                "unit": unit,
                "risk": risk_level,
                "source": source
            }
    return report


def convert_record_for_display(record: dict) -> dict:
    display_record = record.copy() # Start with a copy to modify

    if "Permeability" in display_record and display_record["Permeability"] is not None:
        display_record["Permeability"] = convert_permeability_to_md(display_record["Permeability"])

    if "Porosity" in display_record and display_record["Porosity"] is not None:
        display_record["Porosity"] = display_record["Porosity"] * 100 # Convert to percentage

    # Add other conversions as needed (e.g., Lake_area if you need to adjust units for display)
    for key, value in record.items():
        if key.endswith('_risk'):
            display_record[key] = value # Explicitly ensure _risk fields are copied
            
    return display_record