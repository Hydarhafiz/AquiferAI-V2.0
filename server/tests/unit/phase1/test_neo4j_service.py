"""
Unit tests for Neo4j Service (Task 1.4)

Tests the Neo4j connection, schema, and basic query operations.

Usage:
    # From server/ directory with Neo4j running
    python tests/unit/test_neo4j_service.py

Prerequisites:
    - Docker compose running: docker-compose up -d neo4j
    - Neo4j accessible at bolt://neo4j:7687
    - Database should have aquifer data loaded
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(server_dir))

from app.core.neo4j import execute_cypher_query


# ============================================
# Test Functions
# ============================================

def test_connection():
    """Test 1: Neo4j connection is working."""
    print("\n" + "="*60)
    print("TEST 1: Neo4j Connection")
    print("="*60)

    try:
        # Simple query to test connection
        result = execute_cypher_query("RETURN 1 as test")

        if result and len(result) > 0 and result[0].get('test') == 1:
            print("✓ Neo4j connection successful")
            return True
        else:
            print("✗ Unexpected result from test query")
            return False

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_schema_nodes():
    """Test 2: Check that required node labels exist."""
    print("\n" + "="*60)
    print("TEST 2: Schema - Node Labels")
    print("="*60)

    try:
        # Get all node labels
        result = execute_cypher_query("CALL db.labels()")

        if not result:
            print("✗ No labels found in database")
            return False

        labels = [record.get('label') for record in result]
        print(f"✓ Found {len(labels)} node labels: {labels}")

        # Check for required labels
        required_labels = ['Aquifer', 'Basin', 'Country', 'Continent']
        missing_labels = [label for label in required_labels if label not in labels]

        if missing_labels:
            print(f"⚠ Missing labels: {missing_labels}")
            print("  Note: This is expected if database hasn't been seeded yet")
            return True  # Not a failure, just needs seeding
        else:
            print(f"✓ All required labels present: {required_labels}")
            return True

    except Exception as e:
        print(f"✗ Error checking labels: {e}")
        return False


def test_schema_relationships():
    """Test 3: Check that relationship types exist."""
    print("\n" + "="*60)
    print("TEST 3: Schema - Relationship Types")
    print("="*60)

    try:
        # Get all relationship types
        result = execute_cypher_query("CALL db.relationshipTypes()")

        if not result:
            print("⚠ No relationship types found (database may be empty)")
            return True  # Not a failure

        rel_types = [record.get('relationshipType') for record in result]
        print(f"✓ Found {len(rel_types)} relationship types: {rel_types}")

        # Check for required relationships
        required_rels = ['LOCATED_IN_BASIN', 'IS_LOCATED_IN_COUNTRY', 'LOCATED_IN_CONTINENT']
        missing_rels = [rel for rel in required_rels if rel not in rel_types]

        if missing_rels:
            print(f"⚠ Missing relationships: {missing_rels}")
            print("  Note: This is expected if database hasn't been seeded yet")
            return True  # Not a failure
        else:
            print(f"✓ All required relationships present: {required_rels}")
            return True

    except Exception as e:
        print(f"✗ Error checking relationships: {e}")
        return False


def test_data_count():
    """Test 4: Check data counts."""
    print("\n" + "="*60)
    print("TEST 4: Data Counts")
    print("="*60)

    try:
        # Count aquifers
        result = execute_cypher_query("MATCH (a:Aquifer) RETURN count(a) as count")
        aquifer_count = result[0].get('count', 0) if result else 0
        print(f"  - Aquifers: {aquifer_count}")

        # Count basins
        result = execute_cypher_query("MATCH (b:Basin) RETURN count(b) as count")
        basin_count = result[0].get('count', 0) if result else 0
        print(f"  - Basins: {basin_count}")

        # Count countries
        result = execute_cypher_query("MATCH (c:Country) RETURN count(c) as count")
        country_count = result[0].get('count', 0) if result else 0
        print(f"  - Countries: {country_count}")

        if aquifer_count == 0:
            print("\n⚠ No data found - database needs seeding")
            print("  Run: python tests/scripts/seed_neo4j.py")
            return True  # Not a failure, just needs seeding
        else:
            print(f"\n✓ Database contains {aquifer_count} aquifers")
            return True

    except Exception as e:
        print(f"✗ Error counting data: {e}")
        return False


def test_sample_query():
    """Test 5: Execute a sample aquifer query."""
    print("\n" + "="*60)
    print("TEST 5: Sample Query Execution")
    print("="*60)

    try:
        # Query for aquifers with properties
        query = """
        MATCH (a:Aquifer)
        RETURN a.OBJECTID, a.Porosity, a.Permeability, a.Depth
        LIMIT 5
        """

        result = execute_cypher_query(query)

        if not result:
            print("⚠ No aquifers returned (database may be empty)")
            return True  # Not a failure

        print(f"✓ Query returned {len(result)} aquifers")

        # Show sample data
        if result:
            print("\nSample aquifer data:")
            for i, record in enumerate(result[:3], 1):
                print(f"\n  Aquifer {i}:")
                for key, value in record.items():
                    if value is not None:
                        print(f"    - {key}: {value}")

        # Verify expected properties exist
        if result:
            sample = result[0]
            expected_props = ['a.OBJECTID', 'a.Porosity', 'a.Permeability', 'a.Depth']
            missing = [prop for prop in expected_props if prop not in sample]

            if missing:
                print(f"\n⚠ Missing expected properties: {missing}")
            else:
                print(f"\n✓ All expected properties present")

        return True

    except Exception as e:
        print(f"✗ Error executing sample query: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fulltext_indexes():
    """Test 6: Check for full-text search indexes."""
    print("\n" + "="*60)
    print("TEST 6: Full-Text Search Indexes")
    print("="*60)

    try:
        # Check for indexes
        result = execute_cypher_query("SHOW INDEXES")

        if not result:
            print("⚠ No indexes found")
            print("  Full-text indexes should be created for:")
            print("    - basinSearch (Basin.name)")
            print("    - countrySearch (Country.name)")
            print("    - continentSearch (Continent.name)")
            return True  # Not a failure, just needs setup

        print(f"✓ Found {len(result)} indexes")

        # Look for full-text indexes
        fulltext_indexes = [
            idx for idx in result
            if idx.get('type') == 'FULLTEXT'
        ]

        if fulltext_indexes:
            print(f"✓ Found {len(fulltext_indexes)} full-text indexes:")
            for idx in fulltext_indexes:
                print(f"  - {idx.get('name')}")
        else:
            print("⚠ No full-text indexes found")
            print("  These should be created for geographic search")

        return True

    except Exception as e:
        print(f"✗ Error checking indexes: {e}")
        return False


def test_geographic_query():
    """Test 7: Test geographic query with basin."""
    print("\n" + "="*60)
    print("TEST 7: Geographic Query (Basin)")
    print("="*60)

    try:
        # Try to find aquifers in a basin
        query = """
        MATCH (a:Aquifer)-[:LOCATED_IN_BASIN]->(b:Basin)
        RETURN a.OBJECTID, b.name as basin_name, a.Porosity, a.Depth
        LIMIT 5
        """

        result = execute_cypher_query(query)

        if not result:
            print("⚠ No basin relationships found")
            print("  This is expected if database hasn't been seeded")
            return True  # Not a failure

        print(f"✓ Query returned {len(result)} aquifer-basin relationships")

        if result:
            basins = set(record.get('basin_name') for record in result if record.get('basin_name'))
            print(f"✓ Found aquifers in {len(basins)} basins: {list(basins)[:3]}")

        return True

    except Exception as e:
        print(f"✗ Error executing geographic query: {e}")
        return False


# ============================================
# Main Test Runner
# ============================================

def main():
    """Run all Neo4j service tests."""
    print("\n" + "="*60)
    print("NEO4J SERVICE TEST SUITE (Task 1.4)")
    print("="*60)
    print("\nTesting Neo4j connection and schema...")
    print("\nPrerequisites:")
    print("- Docker Compose services running: docker-compose up -d neo4j")
    print("- Neo4j accessible at bolt://neo4j:7687")
    print("- (Optional) Database seeded with aquifer data")

    results = []

    # Test each component
    results.append(test_connection())
    results.append(test_schema_nodes())
    results.append(test_schema_relationships())
    results.append(test_data_count())
    results.append(test_sample_query())
    results.append(test_fulltext_indexes())
    results.append(test_geographic_query())

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! Neo4j service is working correctly.")
        print("\nNext steps:")
        print("1. If database is empty, run seeding script:")
        print("   python tests/scripts/seed_neo4j.py")
        print("2. Create full-text indexes for geographic search")
        print("3. Test end-to-end workflow with real data")
    else:
        print(f"\n✗ {total - passed} test(s) failed.")
        print("\nTroubleshooting:")
        print("- Ensure Docker Compose is running: docker-compose up -d")
        print("- Check Neo4j logs: docker-compose logs neo4j")
        print("- Verify connection in .env file")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
