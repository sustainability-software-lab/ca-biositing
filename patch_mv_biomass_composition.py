import re

with open('src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py', 'r') as f:
    content = f.read()

# Replace qc_analysis_stats
old_qc = """    (
        func.coalesce(func.avg(case((all_measurements.c.parameter_name == "glucan", all_measurements.c.value))), 0) +
        func.coalesce(func.avg(case((all_measurements.c.parameter_name == "xylan", all_measurements.c.value))), 0) +
        func.coalesce(
            func.avg(case((all_measurements.c.parameter_name == "lignin", all_measurements.c.value))),
            func.avg(case((all_measurements.c.parameter_name == "lignin+", all_measurements.c.value)))
        )
    ).label("compositional_sum")
).group_by("""

new_qc = """    (
        func.coalesce(func.avg(case((all_measurements.c.parameter_name == "glucan", all_measurements.c.value))), 0) +
        func.coalesce(func.avg(case((all_measurements.c.parameter_name == "xylan", all_measurements.c.value))), 0) +
        func.coalesce(
            func.avg(case((all_measurements.c.parameter_name == "lignin", all_measurements.c.value))),
            func.avg(case((all_measurements.c.parameter_name == "lignin+", all_measurements.c.value)))
        )
    ).label("compositional_sum"),
    func.max(
        case(
            (and_(all_measurements.c.analysis_type == "icp", all_measurements.c.unit == "ppm"), all_measurements.c.value),
            else_=0
        )
    ).label("max_icp_ppm")
).group_by("""

content = content.replace(old_qc, new_qc)

# Replace where clause
old_where = """              # For all other analysis types: no filtering, include all
              all_measurements.c.analysis_type.notin_(["proximate", "compositional"])
          )
      )
  )\\"""

new_where = """              # For ICP: filter out experiments with any value > 500,000 ppm
              and_(
                  all_measurements.c.analysis_type == "icp",
                  or_(
                      qc_analysis_stats.c.max_icp_ppm == None,
                      qc_analysis_stats.c.max_icp_ppm <= 500000
                  )
              ),
              # For all other analysis types: no filtering, include all
              all_measurements.c.analysis_type.notin_(["proximate", "compositional", "icp"])
          )
      )
  )\\"""

content = content.replace(old_where, new_where)

with open('src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_composition.py', 'w') as f:
    f.write(content)

print("Done patching mv_biomass_composition.py")
