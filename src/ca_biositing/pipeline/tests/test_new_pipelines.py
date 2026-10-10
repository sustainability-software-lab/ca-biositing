"""
Quick test script to verify newly added infrastructure ETL pipelines are importable.
"""

newly_added = [
    "crude_oil_pipelines",
    "railways",
    "biodiesel_plants",
    "tomato_processors",
    "food_manufacturers_epa",
    "food_manufacturers_carb",
]

print("Testing newly added infrastructure ETL pipelines...")
print("=" * 70)

failed = []

for name in newly_added:
    print(f"\nTesting: {name}")
    try:
        # Test extract
        exec(f"from ca_biositing.pipeline.etl.extract import {name}")
        print(f"  ✓ Extract import OK")

        # Test transform
        exec(f"from ca_biositing.pipeline.etl.transform.infrastructure import {name}")
        print(f"  ✓ Transform import OK")

        # Test load
        exec(f"from ca_biositing.pipeline.etl.load.infrastructure import {name}")
        print(f"  ✓ Load import OK")

        # Test flow
        exec(f"from ca_biositing.pipeline.flows import {name}")
        print(f"  ✓ Flow import OK")

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed.append((name, str(e)))

print("\n" + "=" * 70)
if failed:
    print(f"FAILED: {len(failed)} pipeline(s)")
    for name, error in failed:
        print(f"  - {name}: {error}")
else:
    print(f"SUCCESS: All {len(newly_added)} newly added pipelines passed import tests!")
