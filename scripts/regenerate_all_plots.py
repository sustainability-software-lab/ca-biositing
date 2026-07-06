import os
import subprocess
import sys
import glob

def regenerate_all_plots():
    # Configuration: directories to scan for analysis scripts
    analysis_dir = "analysis"
    categories = ["composition", "conversion", "geospatial", "metadata"]

    # Track results
    successes = []
    failures = []

    print(f"🚀 Starting regeneration of all plots in {analysis_dir}...")

    for category in categories:
        cat_path = os.path.join(analysis_dir, category)
        if not os.path.exists(cat_path):
            print(f"⚠️ Category directory not found: {cat_path}")
            continue

        print(f"\n📂 Processing category: {category.upper()}")

        # Find all .py files in the category directory
        scripts = glob.glob(os.path.join(cat_path, "*.py"))
        scripts.sort()

        for script in scripts:
            script_name = os.path.basename(script)
            print(f"  ▶️ Running {script_name}...")

            try:
                # Run the script using the current python executable
                # Use subprocess to isolate each script's execution
                result = subprocess.run(
                    [sys.executable, script],
                    check=True,
                    capture_output=True,
                    text=True
                )
                successes.append(script)
                print(f"  ✅ Success: {script_name}")
            except subprocess.CalledProcessError as e:
                failures.append((script, e.stderr))
                print(f"  ❌ Failed: {script_name}")
                print(f"     Error: {e.stderr.strip()}")

    # Summary
    print("\n" + "="*50)
    print("📊 REGENERATION SUMMARY")
    print("="*50)
    print(f"Total scripts attempted: {len(successes) + len(failures)}")
    print(f"Successfully ran:        {len(successes)}")
    print(f"Failed:                  {len(failures)}")

    if failures:
        print("\n❌ FAILURES:")
        for script, error in failures:
            print(f"  - {script}")

    print("="*50)

    # Run gallery update at the end if at least some plots were generated
    if successes:
        print("\n🖼️ Updating dashboard gallery...")
        try:
            subprocess.run([sys.executable, "scripts/generate_dashboard_gallery.py"], check=True)
            print("✨ Gallery updated successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to update gallery: {e}")

    if failures:
        sys.exit(1)

if __name__ == "__main__":
    regenerate_all_plots()
