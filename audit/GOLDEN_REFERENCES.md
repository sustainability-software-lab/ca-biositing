# Golden References in the Auditor

Golden References are "frozen" snapshots of database records used as a baseline
for data quality analysis. They prevent "reference drift" by ensuring your
Auditor always compares new data against a known-good standard, rather than just
the current (and potentially changing) population stats.

## How it Works

1. **Storage**: References are stored in `audit/references/`.
2. **Naming Convention**: `YYYYMMDD_target_name.csv`.
3. **Lookup Logic**: The `AuditorAgent` searches for files matching
   `*_target_name.csv`. It sorts them and picks the **latest** date. If no dated
   file is found, it looks for a legacy `target_name.csv`.
4. **Fallback**: If no CSV exists at all, the Auditor falls back to generating a
   baseline from the database using the target's `population_sql`.
5. **Schema Guard**: When a Golden Reference is used, the Auditor enables
   "Schema Guard," which strictly validates column names, types, and null counts
   against the frozen baseline.

## Freezing a New Reference

To capture the current state of the database as a new Golden Reference:

```bash
# Freeze a specific target
pixi run audit-freeze proximate

# Freeze ALL registered targets
pixi run audit-freeze all
```

This will create a new CSV in `audit/references/` with today's date prefix.

## Best Practices

- **Clean Baselines**: Only freeze a reference when you are confident the
  production data is "clean" and represents the desired state.
- **Version Control**: Always commit your Golden Reference CSVs to Git. This
  ensures consistency across development, staging, and production environments.
- **Regular Updates**: Refresh references after major data migrations or when
  the "ground truth" of your bioeconomy analysis fundamentally changes.
