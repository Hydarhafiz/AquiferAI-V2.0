"""
Neo4j Seeding Script for AquiferAI V2.0

This script populates the Neo4j database with sample aquifer data
that matches the actual schema used in the application.

Usage:
    # From server/ directory
    python tests/scripts/seed_neo4j.py

    # Or specify custom connection
    python tests/scripts/seed_neo4j.py --uri bolt://localhost:7687 --user neo4j --password yourpassword

Prerequisites:
    - Neo4j running and accessible
    - Python dependencies installed (neo4j driver)
"""

import argparse
import random
import sys
import asyncio
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(server_dir))

from app.core.neo4j import execute_cypher_query


# ============================================
# Sample Data
# ============================================

CONTINENTS = [
    {"name": "South America"},
    {"name": "North America"},
    {"name": "Oceania"},
    {"name": "Africa"},
    {"name": "Asia"},
]

COUNTRIES = [
    {"name": "Brazil", "continent": "South America"},
    {"name": "Argentina", "continent": "South America"},
    {"name": "Chile", "continent": "South America"},
    {"name": "United States", "continent": "North America"},
    {"name": "Canada", "continent": "North America"},
    {"name": "Australia", "continent": "Oceania"},
    {"name": "South Africa", "continent": "Africa"},
    {"name": "China", "continent": "Asia"},
    {"name": "India", "continent": "Asia"},
]

BASINS = [
    {"name": "Amazon Basin", "country": "Brazil"},
    {"name": "Parnaiba Basin", "country": "Brazil"},
    {"name": "Santos Basin", "country": "Brazil"},
    {"name": "Parana Basin", "country": "Brazil"},
    {"name": "Chaco-Parana Basin", "country": "Argentina"},
    {"name": "Neuquen Basin", "country": "Argentina"},
    {"name": "Central Valley Basin", "country": "Chile"},
    {"name": "Permian Basin", "country": "United States"},
    {"name": "Gulf Coast Basin", "country": "United States"},
    {"name": "Williston Basin", "country": "United States"},
    {"name": "Illinois Basin", "country": "United States"},
    {"name": "Western Canada Sedimentary Basin", "country": "Canada"},
    {"name": "Great Artesian Basin", "country": "Australia"},
    {"name": "Karoo Basin", "country": "South Africa"},
    {"name": "Songliao Basin", "country": "China"},
    {"name": "Krishna-Godavari Basin", "country": "India"},
]

AQUIFER_TYPES = [
    "Sandstone",
    "Carbonate",
    "Mixed Clastic",
    "Volcanic",
    "Fractured Basement",
]


# ============================================
# Data Generation Functions
# ============================================

def generate_aquifer_properties(basin_name: str, index: int) -> dict:
    """
    Generate realistic aquifer properties matching the actual schema.

    Properties match those in app/utils/setup_prompt.py:
    - OBJECTID, AquiferHydrogeologicClassification, Basin, Boundary_coordinates,
    - Cluster, Continent, Country, Depth, Lake_area, Location,
    - Parameter_area, Parameter_shape, Permeability, Porosity, Recharge, Thickness
    """

    # Get basin info
    basin_info = next((b for b in BASINS if b["name"] == basin_name), BASINS[0])
    country_name = basin_info["country"]
    country_info = next((c for c in COUNTRIES if c["name"] == country_name), COUNTRIES[0])
    continent_name = country_info["continent"]

    # Generate coordinates based on country (rough approximations)
    coord_ranges = {
        "Brazil": (-35, -5, -75, -35),
        "Argentina": (-55, -22, -73, -53),
        "Chile": (-56, -17, -76, -66),
        "United States": (25, 49, -125, -66),
        "Canada": (42, 83, -141, -52),
        "Australia": (-44, -10, 113, 154),
        "South Africa": (-35, -22, 16, 33),
        "China": (18, 54, 73, 135),
        "India": (8, 37, 68, 97),
    }

    lat_min, lat_max, lon_min, lon_max = coord_ranges.get(
        country_name, (-30, 30, -120, 120)
    )

    latitude = round(random.uniform(lat_min, lat_max), 4)
    longitude = round(random.uniform(lon_min, lon_max), 4)

    # Generate realistic property values
    depth = round(random.uniform(500, 3500), 1)  # meters
    porosity = round(random.uniform(0.05, 0.35), 3)  # fraction
    permeability = round(random.uniform(-14, -10), 3)  # log10(m²)
    thickness = round(random.uniform(50, 500), 1)  # meters
    recharge = round(random.uniform(0, 500), 1)  # mm/year
    lake_area = round(random.uniform(0, 10000), 1)  # km²
    parameter_area = round(random.uniform(1000, 100000), 1)  # km²

    # Generate boundary coordinates (simplified polygon)
    boundary_coords = f"POLYGON(({longitude} {latitude}, {longitude+0.5} {latitude}, {longitude+0.5} {latitude+0.5}, {longitude} {latitude+0.5}, {longitude} {latitude}))"

    # Generate location as WKT Point
    location = f"POINT({longitude} {latitude})"

    return {
        "OBJECTID": f"{basin_name[:3].upper()}-{index:04d}",
        "AquiferHydrogeologicClassification": random.choice(AQUIFER_TYPES),
        "Basin": basin_name,
        "Boundary_coordinates": boundary_coords,
        "Cluster": random.randint(0, 5),
        "Continent": continent_name,
        "Country": country_name,
        "Depth": depth,
        "Lake_area": lake_area,
        "Location": location,
        "Parameter_area": parameter_area,
        "Parameter_shape": round(random.uniform(1.0, 2.5), 2),  # Shape factor
        "Permeability": permeability,
        "Porosity": porosity,
        "Recharge": recharge,
        "Thickness": thickness,
    }


# ============================================
# Seeding Functions
# ============================================

async def clear_database():
    """Clear all existing data from the database."""
    print("\n🗑️  Clearing existing data...")
    await execute_cypher_query("MATCH (n) DETACH DELETE n")
    print("✓ Database cleared")


async def create_indexes():
    """Create indexes for performance and full-text search."""
    print("\n📊 Creating indexes...")

    # Regular indexes for common queries
    indexes = [
        "CREATE INDEX aquifer_objectid IF NOT EXISTS FOR (a:Aquifer) ON (a.OBJECTID)",
        "CREATE INDEX aquifer_porosity IF NOT EXISTS FOR (a:Aquifer) ON (a.Porosity)",
        "CREATE INDEX aquifer_depth IF NOT EXISTS FOR (a:Aquifer) ON (a.Depth)",
        "CREATE INDEX basin_name IF NOT EXISTS FOR (b:Basin) ON (b.name)",
        "CREATE INDEX country_name IF NOT EXISTS FOR (c:Country) ON (c.name)",
        "CREATE INDEX continent_name IF NOT EXISTS FOR (c:Continent) ON (c.name)",
    ]

    for index_query in indexes:
        try:
            await execute_cypher_query(index_query)
            print(f"  ✓ {index_query.split('FOR')[1].split('IF')[0].strip()}")
        except Exception as e:
            print(f"  ⚠ {e}")

    # Full-text indexes for geographic search
    fulltext_indexes = [
        "CREATE FULLTEXT INDEX basinSearch IF NOT EXISTS FOR (b:Basin) ON EACH [b.name]",
        "CREATE FULLTEXT INDEX countrySearch IF NOT EXISTS FOR (c:Country) ON EACH [c.name]",
        "CREATE FULLTEXT INDEX continentSearch IF NOT EXISTS FOR (c:Continent) ON EACH [c.name]",
    ]

    for ft_query in fulltext_indexes:
        try:
            await execute_cypher_query(ft_query)
            print(f"  ✓ Full-text: {ft_query.split('INDEX')[1].split('IF')[0].strip()}")
        except Exception as e:
            print(f"  ⚠ {e}")

    print("✓ Indexes created")


async def create_geographic_hierarchy():
    """Create Continents, Countries, and Basins."""
    print("\n🌍 Creating geographic hierarchy...")

    # Create Continents
    for continent in CONTINENTS:
        await execute_cypher_query(
            "CREATE (c:Continent {name: $name})",
            {"name": continent["name"]}
        )
    print(f"  ✓ Created {len(CONTINENTS)} continents")

    # Create Countries and link to Continents
    for country in COUNTRIES:
        await execute_cypher_query(
            """
            MATCH (continent:Continent {name: $continent_name})
            CREATE (c:Country {name: $country_name})
            CREATE (c)-[:LOCATED_IN_CONTINENT]->(continent)
            """,
            {"country_name": country["name"], "continent_name": country["continent"]}
        )
    print(f"  ✓ Created {len(COUNTRIES)} countries")

    # Create Basins and link to Countries
    for basin in BASINS:
        await execute_cypher_query(
            """
            MATCH (country:Country {name: $country_name})
            CREATE (b:Basin {name: $basin_name})
            CREATE (b)-[:IS_LOCATED_IN_COUNTRY]->(country)
            """,
            {"basin_name": basin["name"], "country_name": basin["country"]}
        )
    print(f"  ✓ Created {len(BASINS)} basins")


async def create_aquifers(num_aquifers_per_basin: int = 10):
    """Create aquifers with realistic properties."""
    print(f"\n💧 Creating aquifers ({num_aquifers_per_basin} per basin)...")

    total_created = 0

    for basin in BASINS:
        basin_name = basin["name"]

        for i in range(1, num_aquifers_per_basin + 1):
            props = generate_aquifer_properties(basin_name, i)

            # Add basin_name to props for the query
            props_with_basin = {**props, "basin_name": basin_name}

            # Create aquifer and link to basin
            await execute_cypher_query(
                """
                MATCH (b:Basin {name: $basin_name})
                CREATE (a:Aquifer {
                    OBJECTID: $OBJECTID,
                    AquiferHydrogeologicClassification: $AquiferHydrogeologicClassification,
                    Basin: $Basin,
                    Boundary_coordinates: $Boundary_coordinates,
                    Cluster: $Cluster,
                    Continent: $Continent,
                    Country: $Country,
                    Depth: $Depth,
                    Lake_area: $Lake_area,
                    Location: $Location,
                    Parameter_area: $Parameter_area,
                    Parameter_shape: $Parameter_shape,
                    Permeability: $Permeability,
                    Porosity: $Porosity,
                    Recharge: $Recharge,
                    Thickness: $Thickness
                })
                CREATE (a)-[:LOCATED_IN_BASIN]->(b)
                """,
                props_with_basin
            )

            total_created += 1

            if total_created % 20 == 0:
                print(f"  Created {total_created} aquifers...")

    print(f"✓ Created {total_created} aquifers total")


async def verify_data():
    """Verify that data was created correctly."""
    print("\n✅ Verifying data...")

    # Count nodes
    result = await execute_cypher_query("MATCH (a:Aquifer) RETURN count(a) as count")
    aquifer_count = result[0]["count"] if result else 0

    result = await execute_cypher_query("MATCH (b:Basin) RETURN count(b) as count")
    basin_count = result[0]["count"] if result else 0

    result = await execute_cypher_query("MATCH (c:Country) RETURN count(c) as count")
    country_count = result[0]["count"] if result else 0

    result = await execute_cypher_query("MATCH (c:Continent) RETURN count(c) as count")
    continent_count = result[0]["count"] if result else 0

    print(f"  - Continents: {continent_count}")
    print(f"  - Countries: {country_count}")
    print(f"  - Basins: {basin_count}")
    print(f"  - Aquifers: {aquifer_count}")

    # Sample query
    result = await execute_cypher_query(
        """
        MATCH (a:Aquifer)-[:LOCATED_IN_BASIN]->(b:Basin)-[:IS_LOCATED_IN_COUNTRY]->(c:Country)
        RETURN a.OBJECTID, a.Porosity, a.Depth, b.name as basin, c.name as country
        LIMIT 3
        """
    )

    if result:
        print("\n  Sample aquifers:")
        for record in result:
            print(f"    - {record['a.OBJECTID']}: Porosity={record['a.Porosity']:.3f}, "
                  f"Depth={record['a.Depth']:.1f}m, Basin={record['basin']}, Country={record['country']}")

    print("\n✓ Data verification complete")


# ============================================
# Main Function
# ============================================

async def main():
    """Main seeding function."""
    print("="*60)
    print("NEO4J DATABASE SEEDING SCRIPT")
    print("="*60)
    print("\nThis will populate the database with sample aquifer data.")

    parser = argparse.ArgumentParser(description="Seed Neo4j with aquifer data")
    parser.add_argument("--aquifers-per-basin", type=int, default=10,
                        help="Number of aquifers to create per basin (default: 10)")
    parser.add_argument("--skip-clear", action="store_true",
                        help="Skip clearing existing data")

    args = parser.parse_args()

    try:
        # Step 1: Clear database (optional)
        if not args.skip_clear:
            await clear_database()
        else:
            print("\n⚠️  Skipping database clear (--skip-clear flag)")

        # Step 2: Create indexes
        await create_indexes()

        # Step 3: Create geographic hierarchy
        await create_geographic_hierarchy()

        # Step 4: Create aquifers
        await create_aquifers(num_aquifers_per_basin=args.aquifers_per_basin)

        # Step 5: Verify
        await verify_data()

        print("\n" + "="*60)
        print("✅ SEEDING COMPLETE!")
        print("="*60)
        print(f"\nCreated {len(BASINS) * args.aquifers_per_basin} aquifers across {len(BASINS)} basins")
        print("\nNext steps:")
        print("1. Test the connection: python tests/unit/test_neo4j_service.py")
        print("2. Run agent tests: python tests/unit/test_agents.py")
        print("3. Start the API server and test queries")

        return True

    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
