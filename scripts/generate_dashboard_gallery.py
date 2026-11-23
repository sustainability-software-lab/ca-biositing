#!/usr/bin/env python3
"""Generate the 5-product BioCirV dashboard gallery (index.html) and login portal (login.html)."""

from __future__ import annotations

import argparse
from datetime import datetime
import glob
import os
from pathlib import Path

DESCRIPTIONS: dict[str, str] = {
    "resource_analysis_dashboard.html": (
        "Product 1 (Characterization & AI Brief): Streamlined single-resource analytical & bioconversion dashboard "
        "with compact 2-card Executive AI Brief, 4 KPI cards, and 5 focused domain tabs across all active resources."
    ),
    "resource_qc_outlier_dashboard.html": (
        "Product 2 (Statistical QC & Lab Notes Audit): Dedicated replicate precision (RSD_within vs. RSD_between), "
        "3-test candidate outlier screening (Dixon's Q, RSD > 20%, >3×SD_pooled with <100 ppm / <0.5% trace cutoffs), "
        "mined bench notes audit trail, and anonymized CSV export."
    ),
    "resource_explorer_dashboard.html": (
        "Product 3 (Interactive Data Visualizer): High-DPI HTML5 Canvas visualizer with always-accessible "
        "Multi-Select Checklists (Resources, Parameters & Units, Samples, Methods/Preps), Compare By grouping selector, "
        "rectangular brush zoom, and filtered CSV/JSON/HTML slice export."
    ),
    "resource_audit_workbench.html": (
        "Product 4 (Resource QC & Data Audit Workbench): Interactive two-stage QC review workbench with Queue & Task "
        "Assignment Bar, side-by-side multi-view diagnostic plotter, replicate-level scope toggle, PostgreSQL Stage 1 "
        "ledger commits, BroadcastChannel cross-tab sync, and Admin-only Stage 2 Google Sheets write-back."
    ),
    "db_environment_drift_dashboard.html": (
        "Product 5 (Admin-Only Local vs. Staging vs. Production Database Drift Dashboard): 4-layer parity scorecard, "
        "data_portal & ca_biositing View Schema Guard, table & materialized view row deltas, Resource × Analysis-Type "
        "drift heatmap, lineage set-difference explorer, and parameter value shift (>5%) detector."
    ),
}


def render_login_html(timestamp_str: str) -> str:
    """Render the self-contained Portal Login & Dev Session Switcher HTML (login.html)."""
    return f"""<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BioCirV Portal Login — Google OAuth &amp; Role Session Manager</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <script src="https://accounts.google.com/gsi/client" async defer></script>
  <style>
    body {{
      background-color: #0b1120;
      color: #f8fafc;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    .login-hero {{
      background: linear-gradient(135deg, #00313C 0%, #0284c7 100%);
      padding: 2.5rem 1.5rem;
      border-bottom: 1px solid #1e293b;
    }}
    .auth-card {{
      background-color: #111827;
      border: 1px solid #1e293b;
      border-radius: 12px;
    }}
    .domain-pill {{
      display: inline-block;
      padding: 3px 10px;
      border-radius: 999px;
      background: #1e293b;
      border: 1px solid #334155;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      margin-right: 6px;
    }}
  </style>
</head>
<body>
  <header class="login-hero text-center">
    <h1 class="fw-bold mb-1">BioCirV Analytics &amp; QC Audit Portal Login</h1>
    <p class="mb-2 text-light opacity-90">
      Domain-Allowlisted Google Sign-In &amp; Role-Aware Session Access (Products 1–5)
    </p>
    <div>
      <span class="domain-pill">@lbl.gov</span>
      <span class="domain-pill">@ucdavis.edu</span>
      <span class="domain-pill">@beamcircular.org</span>
    </div>
  </header>

  <main class="container my-4 flex-grow-1" style="max-width: 920px;">
    <div class="row g-4">
      <div class="col-md-6">
        <div class="auth-card p-4 h-100 shadow">
          <h4 class="fw-bold mb-2">1. Google Identity Sign-In (Staging &amp; Production)</h4>
          <p class="text-secondary small mb-3">
            Sign in with your organizational Google account. Accounts in
            <code>@lbl.gov</code>, <code>@ucdavis.edu</code>, and <code>@beamcircular.org</code>
            receive <strong>analyst</strong> access to Products 1–4; emails listed in
            <code>DASHBOARD_ADMIN_EMAILS</code> receive <strong>admin</strong> access (unlocking
            Stage 2 Google Sheets write-back and Product 5 DB Drift Audit).
          </p>

          <div class="mb-3 p-3 rounded bg-dark border border-secondary text-center">
            <div class="small fw-semibold text-info mb-2">Sign in with Google Workspace</div>
            <div id="google-gsi-button" class="d-flex justify-content-center my-2"></div>
            <div id="google-gsi-status" class="small text-secondary">
              Loading Google Sign-In configuration...
            </div>
          </div>

          <details class="mb-3">
            <summary class="small text-secondary" style="cursor: pointer;">
              Advanced: Paste Google OIDC ID Token Manually (<code>POST /v1/qc/auth/google</code>)
            </summary>
            <form id="google-token-form" class="mt-2">
              <label for="input-google-id-token" class="form-label small fw-semibold">
                Google ID Token / Credential
              </label>
              <input
                type="password"
                id="input-google-id-token"
                class="form-control form-control-sm mb-2"
                placeholder="Paste Google ID token..."
              />
              <button type="submit" class="btn btn-info text-dark fw-bold w-100" id="btn-google-login">
                🔐 Verify Google ID Token
              </button>
            </form>
          </details>

          <hr class="border-secondary" />

          <h5 class="fw-bold mb-2">Current Portal Session (<code>GET /v1/qc/auth/me</code>)</h5>
          <div class="p-3 rounded bg-dark border border-secondary small mb-3" id="session-status-box">
            <div><strong>Status:</strong> <span id="session-auth-state">Checking...</span></div>
            <div><strong>Email:</strong> <code id="session-user-email">unauthenticated</code></div>
            <div><strong>Role:</strong> <span class="badge bg-info text-dark" id="session-user-role">none</span></div>
            <div><strong>Assigned Open QC Items:</strong> <span id="session-assigned-count">0</span></div>
          </div>

          <div class="d-flex gap-2">
            <a href="index.html" class="btn btn-outline-light btn-sm flex-grow-1">
              ← Open 5-Product Gallery
            </a>
            <a href="metadata/resource_audit_workbench.html" class="btn btn-primary btn-sm flex-grow-1">
              Open Product 4 Workbench →
            </a>
            <button type="button" class="btn btn-outline-danger btn-sm" id="btn-logout">
              Sign Out
            </button>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="auth-card p-4 h-100 shadow">
          <h4 class="fw-bold mb-2">2. Localhost Dev Session Switcher</h4>
          <p class="text-secondary small mb-3">
            When running locally on <code>localhost</code> / <code>127.0.0.1</code>, switch between
            <strong>Analyst</strong> and <strong>Admin</strong> personas via
            <code>POST /v1/qc/auth/dev-login</code> to test role-gated UI controls.
          </p>

          <div class="d-grid gap-2 mb-3">
            <button
              type="button"
              class="btn btn-outline-info text-start"
              data-dev-email="analyst@lbl.gov"
              data-dev-name="BioCIRV QC Analyst"
              data-dev-role="analyst"
            >
              👤 <strong>Sign in as Analyst</strong> (<code>analyst@lbl.gov</code>)
              <div class="small text-secondary">
                Access Products 1–4 • Stage 1 DB commits • Stage 2 GSheet &amp; Product 5 locked
              </div>
            </button>

            <button
              type="button"
              class="btn btn-outline-warning text-start"
              data-dev-email="admin@lbl.gov"
              data-dev-name="BioCIRV QC Lead Admin"
              data-dev-role="admin"
            >
              🛡️ <strong>Sign in as Admin</strong> (<code>admin@lbl.gov</code>)
              <div class="small text-secondary">
                Full Access Products 1–5 • Stage 2 Google Sheets Write-Back unlocked
              </div>
            </button>
          </div>

          <form id="dev-login-form">
            <div class="mb-2">
              <label for="input-dev-email" class="form-label small fw-semibold">Custom Allowlisted Email</label>
              <input
                type="email"
                id="input-dev-email"
                class="form-control form-control-sm"
                value="analyst@lbl.gov"
                required
              />
            </div>
            <div class="mb-3">
              <label for="input-dev-name" class="form-label small fw-semibold">Display Name</label>
              <input
                type="text"
                id="input-dev-name"
                class="form-control form-control-sm"
                value="BioCIRV Analyst"
              />
            </div>
            <button type="submit" class="btn btn-light text-dark fw-bold w-100" id="btn-dev-login-submit">
              ⚡ Activate Dev Session (<code>POST /v1/qc/auth/dev-login</code>)
            </button>
          </form>

          <div id="login-feedback" class="alert alert-info mt-3 py-2 small" style="display: none;"></div>
        </div>
      </div>
    </div>
  </main>

  <footer class="py-3 bg-dark border-top border-secondary text-center text-secondary small">
    BioCirV Portal Auth • Generated {timestamp_str}
  </footer>

  <script>
    (function () {{
      "use strict";

      function getNextRedirectTarget() {{
        try {{
          var params = new URLSearchParams(window.location.search);
          var next = params.get("next");
          if (next && next.startsWith("/") && !next.startsWith("//")) {{
            return next;
          }}
        }} catch (e) {{}}
        return null;
      }}

      function showFeedback(msg, isErr) {{
        var el = document.getElementById("login-feedback");
        if (!el) return;
        el.style.display = "block";
        el.className = "alert mt-3 py-2 small " + (isErr ? "alert-danger" : "alert-success");
        el.textContent = msg;
      }}

      function refreshMe() {{
        fetch("/v1/qc/auth/me", {{ credentials: "same-origin" }})
          .then(function (r) {{ return r.ok ? r.json() : null; }})
          .then(function (data) {{
            if (!data) {{
              document.getElementById("session-auth-state").textContent = "Not Signed In";
              return;
            }}
            document.getElementById("session-auth-state").textContent =
              data.authenticated ? "Authenticated (" + (data.auth_mode || "cookie") + ")" : "Unauthenticated";
            document.getElementById("session-user-email").textContent = data.email || "anonymous";
            document.getElementById("session-user-role").textContent = data.role || "analyst";
            document.getElementById("session-assigned-count").textContent = String(data.assigned_open_count || 0);
          }})
          .catch(function () {{
            document.getElementById("session-auth-state").textContent = "Offline / Static Preview";
          }});
      }}

      function verifyGoogleIdToken(tok) {{
        if (!tok) {{
          showFeedback("Missing Google ID token.", true);
          return;
        }}
        fetch("/v1/qc/auth/google", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          credentials: "same-origin",
          body: JSON.stringify({{ id_token: tok, credential: tok }})
        }})
          .then(function (r) {{ return r.json(); }})
          .then(function (res) {{
            if (res && res.authenticated) {{
              showFeedback("Google OAuth verified for " + res.email + " (" + res.role + ")", false);
              refreshMe();
              var nextUrl = getNextRedirectTarget() || "/v1/dashboards/index.html";
              setTimeout(function () {{
                window.location.replace(nextUrl);
              }}, 350);
            }} else {{
              showFeedback((res && res.detail) || "Google token verification failed.", true);
            }}
          }})
          .catch(function () {{
            showFeedback("Could not reach /v1/qc/auth/google endpoint.", true);
          }});
      }}

      function initGoogleSignInButton() {{
        var statusEl = document.getElementById("google-gsi-status");
        var btnContainer = document.getElementById("google-gsi-button");
        fetch("/v1/qc/auth/config", {{ credentials: "same-origin" }})
          .then(function (r) {{ return r.ok ? r.json() : null; }})
          .then(function (cfg) {{
            var clientId = cfg && cfg.google_client_id ? String(cfg.google_client_id).trim() : "";
            if (!clientId) {{
              if (statusEl) {{
                statusEl.textContent = "GOOGLE_CLIENT_ID not configured on this server (use Localhost Dev Switcher or manual token).";
              }}
              return;
            }}
            var attempts = 0;
            var timer = setInterval(function () {{
              attempts += 1;
              if (window.google && window.google.accounts && window.google.accounts.id) {{
                clearInterval(timer);
                window.google.accounts.id.initialize({{
                  client_id: clientId,
                  callback: function (response) {{
                    if (response && response.credential) {{
                      verifyGoogleIdToken(response.credential);
                    }}
                  }}
                }});
                if (btnContainer) {{
                  window.google.accounts.id.renderButton(btnContainer, {{
                    theme: "filled_blue",
                    size: "large",
                    text: "signin_with",
                    shape: "pill",
                    width: 280
                  }});
                }}
                if (statusEl) {{
                  statusEl.textContent = "Click 'Sign in with Google' using your @lbl.gov, @ucdavis.edu, or @beamcircular.org account.";
                }}
              }} else if (attempts > 40) {{
                clearInterval(timer);
                if (statusEl) {{
                  statusEl.textContent = "Google Identity script blocked or unavailable. Use manual token below.";
                }}
              }}
            }}, 150);
          }})
          .catch(function () {{
            if (statusEl) {{
              statusEl.textContent = "Static preview mode (no backend /v1/qc/auth/config).";
            }}
          }});
      }}

      var devBtns = document.querySelectorAll("[data-dev-email]");
      for (var i = 0; i < devBtns.length; i++) {{
        devBtns[i].addEventListener("click", function (ev) {{
          var btn = ev.currentTarget;
          var email = btn.getAttribute("data-dev-email");
          var name = btn.getAttribute("data-dev-name");
          document.getElementById("input-dev-email").value = email;
          document.getElementById("input-dev-name").value = name;
          submitDevLogin(email, name);
        }});
      }}

      function submitDevLogin(email, name) {{
        fetch("/v1/qc/auth/dev-login", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          credentials: "same-origin",
          body: JSON.stringify({{ email: email, name: name }})
        }})
          .then(function (r) {{ return r.json().then(function (d) {{ return {{ ok: r.ok, data: d }}; }}); }})
          .then(function (res) {{
            if (!res.ok) {{
              showFeedback((res.data && res.data.detail) || "Dev login disabled on this host.", true);
              return;
            }}
            showFeedback("Active session set to " + (res.data.email || email) + " (" + (res.data.role || "analyst") + ")", false);
            refreshMe();
            var nextUrl = getNextRedirectTarget() || "/v1/dashboards/index.html";
            setTimeout(function () {{ window.location.replace(nextUrl); }}, 350);
          }})
          .catch(function () {{
            showFeedback("Local preview session set to " + email, false);
          }});
      }}

      var devForm = document.getElementById("dev-login-form");
      if (devForm) {{
        devForm.addEventListener("submit", function (ev) {{
          ev.preventDefault();
          submitDevLogin(
            document.getElementById("input-dev-email").value,
            document.getElementById("input-dev-name").value
          );
        }});
      }}

      var googleForm = document.getElementById("google-token-form");
      if (googleForm) {{
        googleForm.addEventListener("submit", function (ev) {{
          ev.preventDefault();
          var tok = document.getElementById("input-google-id-token").value.trim();
          verifyGoogleIdToken(tok);
        }});
      }}

      var logoutBtn = document.getElementById("btn-logout");
      if (logoutBtn) {{
        logoutBtn.addEventListener("click", function () {{
          fetch("/v1/qc/auth/logout", {{ method: "POST", credentials: "same-origin" }})
            .finally(function () {{
              showFeedback("Signed out of portal session.", false);
              refreshMe();
            }});
        }});
      }}

      initGoogleSignInButton();
      refreshMe();
    }})();
  </script>
</body>
</html>
"""


def generate_gallery(base_dir: str = ".", output_dir: str | None = None) -> tuple[str, str]:
    """Generate both index.html (5-product gallery) and login.html inside target_dir."""
    target_dir = output_dir if output_dir is not None else os.path.join(base_dir, "exports/plots")
    output_file = os.path.join(target_dir, "index.html")
    login_file = os.path.join(target_dir, "login.html")
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    categories = ["metadata", "audit", "conversion", "composition", "geospatial", "lineage"]
    sections_html: list[str] = []

    for category in categories:
        cat_dir = os.path.join(target_dir, category)
        if not os.path.exists(cat_dir):
            continue

        html_files = sorted(glob.glob(os.path.join(cat_dir, "*.html")))
        if not html_files:
            continue

        category_title = category.replace("_", " ").title()
        dashboard_items: list[str] = []

        for file_path in html_files:
            file_name = os.path.basename(file_path)
            if (
                "monolith" in file_name
                or "pretreatment_variance" in file_name
                or "resource_quick_widget" in file_name
            ):
                continue
            rel_path = os.path.join(category, file_name)
            title = file_name.replace(".html", "").replace("_", " ").title()
            desc = DESCRIPTIONS.get(file_name, "Interactive BioCirV analysis visualization.")
            is_admin_drift = file_name == "db_environment_drift_dashboard.html"
            admin_attr = ' data-admin-only="true"' if is_admin_drift else ""

            dashboard_items.append(f"""
                <div class="col"{admin_attr}>
                    <div class="card h-100 shadow-sm">
                        <div class="card-body d-flex flex-column">
                            <h5 class="card-title fw-bold">{title}</h5>
                            <p class="card-text text-muted small flex-grow-1">{desc}</p>
                            <a href="{rel_path}" class="btn btn-primary w-100 mt-2" target="_blank">View Dashboard</a>
                        </div>
                        <div class="card-footer text-muted small font-monospace">
                            {category}/{file_name}
                        </div>
                    </div>
                </div>
            """)

        if not dashboard_items:
            continue

        items_html = "\n".join(dashboard_items)
        sections_html.append(f"""
            <div class="category-section mb-5">
                <h2 class="border-bottom border-secondary pb-2 mb-4 fw-bold">{category_title}</h2>
                <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
                    {items_html}
                </div>
            </div>
        """)

    all_sections_html = "\n".join(sections_html)

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BioCirV — 5-Product Modular Analytics, QC Audit &amp; Drift Suite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #0b1120;
            color: #f8fafc;
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
        .hero {{
            background: linear-gradient(135deg, #00313C 0%, #00B5E2 100%);
            color: white;
            padding: 3rem 2rem;
            margin-bottom: 2rem;
        }}
        .category-section h2 {{
            color: #38bdf8;
            letter-spacing: -0.025em;
        }}
        .card {{
            background-color: #111827;
            border: 1px solid #1e293b;
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.35) !important;
        }}
        .btn-primary {{
            background-color: #00B5E2;
            border-color: #00B5E2;
            color: #0f172a;
            font-weight: 600;
        }}
        .btn-primary:hover {{
            background-color: #0094b8;
            border-color: #0094b8;
            color: #0f172a;
        }}
        .admin-locked-overlay {{
            border: 1px dashed #64748b;
            background: rgba(15, 23, 42, 0.75);
        }}
    </style>
</head>
<body>

<div class="hero text-center">
    <div class="container d-flex flex-wrap justify-content-between align-items-center mb-3">
        <div class="text-start">
            <span class="badge bg-dark border border-info text-info px-3 py-2" id="gallery-user-pill">
                👤 Session: <strong id="gallery-user-email">analyst@lbl.gov</strong>
                (<span id="gallery-user-role">analyst</span>)
            </span>
        </div>
        <div class="d-flex gap-2">
            <a href="login.html" class="btn btn-sm btn-light fw-bold text-dark" id="link-gallery-login">
                🔐 Portal Login / Switch Role
            </a>
            <button type="button" class="btn btn-sm btn-outline-light" id="btn-gallery-toggle-role">
                ⇄ Preview Admin/Analyst Role
            </button>
            <button type="button" class="btn btn-sm btn-warning fw-bold text-dark" id="btn-open-bug-modal">
                🐛 Report a Bug
            </button>
        </div>
    </div>
    <h1 class="display-5 fw-bold">BioCirV 5-Product Analytics, QC Audit &amp; Drift Suite</h1>
    <p class="lead mb-0">BioCirV Bioeconomy Analytics · Two-Stage QC Ledger &amp; Reproducible Agent-Skill Suite</p>
    <div class="mt-3">
        <span class="badge bg-light text-dark px-3 py-2">Updated: {timestamp_str}</span>
    </div>
</div>

<div class="container mb-4">
  <div class="card shadow-sm border-0" style="background: linear-gradient(135deg, #0f172a 0%, #0369a1 100%); color: white;">
    <div class="card-body p-4">
      <div class="row align-items-center g-3">
        <div class="col-lg-8">
          <span class="badge bg-info text-dark fw-bold mb-2">5-PRODUCT MODULAR RESOURCE, QC WORKBENCH &amp; DRIFT SUITE</span>
          <h3 class="fw-bold mb-1">BioCirV Feedstock Characterization, Statistical QC, Explorer, Audit Workbench &amp; Drift Suite</h3>
          <p class="mb-2 text-light opacity-90 small">
            Explore all <strong>127 cataloged resources</strong> (45 with active lab records), <strong>147 field samples</strong>,
            <strong>384 prepared samples</strong>, and <strong>11,974 observations</strong> across our 5-product architecture:
            <strong>Product 1 (Characterization &amp; AI Brief)</strong>,
            <strong>Product 2 (Statistical QC &amp; Lab Notes Audit)</strong>,
            <strong>Product 3 (Interactive Data Visualizer)</strong>,
            <strong>Product 4 (Interactive Resource QC &amp; Data Audit Workbench)</strong>, and
            <strong>Product 5 (Admin-Only Local vs. Staging vs. Prod DB Drift Dashboard)</strong>.
          </p>
          <div class="d-flex flex-wrap gap-2 mt-3">
            <a href="metadata/resource_analysis_dashboard.html" class="btn btn-sm btn-info text-dark fw-bold" target="_blank">📊 1. Characterization &amp; AI Brief</a>
            <a href="metadata/resource_qc_outlier_dashboard.html" class="btn btn-sm btn-warning text-dark fw-bold" target="_blank">🔬 2. Statistical QC &amp; Outlier Audit</a>
            <a href="metadata/resource_explorer_dashboard.html" class="btn btn-sm btn-light text-dark fw-bold" target="_blank">⚖️ 3. Interactive Data Visualizer</a>
            <a href="metadata/resource_audit_workbench.html" class="btn btn-sm btn-success text-white fw-bold" target="_blank" id="hero-link-product4">
              🛡️ 4. QC Audit Workbench
              <span class="badge bg-warning text-dark ms-1" id="badge-my-assigned-reviews">My Assigned Reviews (0)</span>
            </a>
            <a
              href="audit/db_environment_drift_dashboard.html"
              class="btn btn-sm btn-outline-light fw-bold"
              target="_blank"
              id="hero-link-product5"
              data-admin-only="true"
            >
              🔄 5. DB Environment Drift Audit (Admin)
            </a>
          </div>
        </div>
        <div class="col-lg-4 text-lg-end d-flex flex-column gap-2">
          <a href="metadata/resource_analysis_dashboard.html" class="btn btn-primary fw-bold px-4 py-2 shadow" target="_blank">
            Open Product 1: Characterization &rarr;
          </a>
          <a href="metadata/resource_audit_workbench.html" class="btn btn-success fw-bold px-3 py-2 shadow" target="_blank">
            Open Product 4: QC Audit Workbench &rarr;
          </a>
          <a href="metadata/resource_explorer_dashboard.html" class="btn btn-outline-info text-white fw-semibold px-3 py-2" target="_blank">
            Open Product 3: Interactive Data Visualizer &rarr;
          </a>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="container mb-5" id="suite-product-cards">
  <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
    <div class="col" id="product-card-1">
      <div class="card h-100 shadow-sm">
        <div class="card-body d-flex flex-column">
          <span class="badge bg-info text-dark align-self-start mb-2">Product 1</span>
          <h5 class="card-title fw-bold">Resource Characterization &amp; AI Brief</h5>
          <p class="card-text text-muted small flex-grow-1">{DESCRIPTIONS["resource_analysis_dashboard.html"]}</p>
          <a href="metadata/resource_analysis_dashboard.html" class="btn btn-primary w-100 mt-2">Open Product 1</a>
        </div>
      </div>
    </div>

    <div class="col" id="product-card-2">
      <div class="card h-100 shadow-sm">
        <div class="card-body d-flex flex-column">
          <span class="badge bg-warning text-dark align-self-start mb-2">Product 2</span>
          <h5 class="card-title fw-bold">Statistical QC &amp; Lab Notes Audit</h5>
          <p class="card-text text-muted small flex-grow-1">{DESCRIPTIONS["resource_qc_outlier_dashboard.html"]}</p>
          <a href="metadata/resource_qc_outlier_dashboard.html" class="btn btn-primary w-100 mt-2">Open Product 2</a>
        </div>
      </div>
    </div>

    <div class="col" id="product-card-3">
      <div class="card h-100 shadow-sm">
        <div class="card-body d-flex flex-column">
          <span class="badge bg-light text-dark align-self-start mb-2">Product 3</span>
          <h5 class="card-title fw-bold">Interactive Data Visualizer</h5>
          <p class="card-text text-muted small flex-grow-1">{DESCRIPTIONS["resource_explorer_dashboard.html"]}</p>
          <a href="metadata/resource_explorer_dashboard.html" class="btn btn-primary w-100 mt-2">Open Product 3</a>
        </div>
      </div>
    </div>

    <div class="col" id="product-card-4">
      <div class="card h-100 shadow-sm border-success">
        <div class="card-body d-flex flex-column">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-success">Product 4</span>
            <span class="badge bg-warning text-dark" id="card4-assigned-reviews-badge">My Assigned Reviews (0)</span>
          </div>
          <h5 class="card-title fw-bold">Resource QC &amp; Data Audit Workbench</h5>
          <p class="card-text text-muted small flex-grow-1">{DESCRIPTIONS["resource_audit_workbench.html"]}</p>
          <a href="metadata/resource_audit_workbench.html" class="btn btn-success w-100 mt-2 fw-bold">
            Open Product 4 Workbench
          </a>
        </div>
      </div>
    </div>

    <div class="col" id="product-card-5-drift" data-admin-only="true">
      <div class="card h-100 shadow-sm" id="product-card-5-inner">
        <div class="card-body d-flex flex-column">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-secondary">Product 5 • Admin Only</span>
            <span class="badge bg-danger" id="product5-lock-badge">🔒 Admin Role Required</span>
          </div>
          <h5 class="card-title fw-bold">DB Environment Drift Dashboard</h5>
          <p class="card-text text-muted small flex-grow-1">{DESCRIPTIONS["db_environment_drift_dashboard.html"]}</p>
          <a
            href="audit/db_environment_drift_dashboard.html"
            class="btn btn-primary w-100 mt-2"
            id="btn-open-product5"
          >
            Open Product 5 Drift Audit
          </a>
          <div class="small text-warning mt-2" id="product5-analyst-notice">
            Restricted to <code>admin</code> role. Switch to an Admin account on <a href="login.html" class="text-info">login.html</a>.
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="container mb-5">
    {all_sections_html}
</div>

<footer class="py-4 bg-dark border-top border-secondary mt-auto">
    <div class="container text-center text-secondary">
        <p class="mb-0">BioCirV Analysis Hub · Powered by Reproducible Agent Skills (<code>pixi run refresh-dashboards</code> &amp; <code>pixi run db-drift-compare</code>)</p>
    </div>
</footer>

<style>
  .hidden {{ display: none !important; }}
  .gallery-bug-backdrop {{
    position: fixed;
    inset: 0;
    z-index: 1050;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.72);
    padding: 16px;
  }}
  .gallery-bug-card {{
    background: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 14px;
    max-width: 540px;
    width: 100%;
    padding: 20px;
    box-shadow: 0 20px 45px rgba(0, 0, 0, 0.55);
  }}
</style>

<!-- Pre-populated GitHub Bug Report Modal -->
<div id="modal-report-bug" class="gallery-bug-backdrop hidden" role="dialog" aria-modal="true">
  <div class="gallery-bug-card">
    <div class="d-flex justify-content-between align-items-start border-bottom border-secondary pb-2 mb-3">
      <div>
        <h5 class="fw-bold mb-1">🐛 Report a Dashboard or Data QC Issue</h5>
        <p class="small text-secondary mb-0">Automatically attaches your active portal page and role context to a GitHub Issue.</p>
      </div>
      <button id="btn-close-bug-modal" type="button" class="btn btn-sm btn-outline-light">✕</button>
    </div>
    <div class="mb-2">
      <label class="form-label small fw-bold mb-1">Issue Summary Title</label>
      <input id="bug-modal-title" type="text" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="e.g., Broken dashboard link or unexpected metric" />
    </div>
    <div class="mb-2">
      <label class="form-label small fw-bold mb-1">Issue Category</label>
      <select id="bug-modal-category" class="form-select form-select-sm bg-dark text-light border-secondary">
        <option value="UI / Chart Rendering Bug">UI / Chart Rendering Bug</option>
        <option value="Statistical Outlier / Suspect Value">Statistical Outlier / Suspect Value</option>
        <option value="Unit / Basis Normalization Issue">Unit / Basis Normalization Issue</option>
        <option value="Missing Metadata / Provenance Gap">Missing Metadata / Provenance Gap</option>
        <option value="Feature / Export Request">Feature / Export Request</option>
      </select>
    </div>
    <div class="mb-2">
      <label class="form-label small fw-bold mb-1">What happened / Steps to reproduce</label>
      <textarea id="bug-modal-desc" rows="3" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="Describe the unexpected behavior or missing data..."></textarea>
    </div>
    <div class="mb-2">
      <label class="form-label small fw-bold mb-1">Expected behavior (optional)</label>
      <textarea id="bug-modal-expected" rows="2" class="form-control form-control-sm bg-dark text-light border-secondary" placeholder="What should be displayed?"></textarea>
    </div>
    <div class="p-2 rounded bg-dark border border-secondary small font-monospace text-secondary mb-2">
      <div class="fw-bold text-light">Auto-Captured Diagnostic Context:</div>
      <div id="bug-modal-diagnostics" style="white-space: pre-wrap;">Loading current view state...</div>
    </div>
    <div id="bug-modal-status" class="hidden small font-monospace p-2 rounded border border-secondary mb-2"></div>
    <div class="d-flex justify-content-end gap-2 border-top border-secondary pt-2">
      <button id="btn-cancel-bug-modal" type="button" class="btn btn-sm btn-outline-light">Cancel</button>
      <button id="btn-submit-github-api" type="button" class="btn btn-sm btn-warning fw-bold text-dark">🚀 Submit Issue</button>
      <button id="btn-submit-github-url" type="button" class="btn btn-sm btn-warning fw-bold text-dark hidden" style="display:none;">↗ Open Pre-Filled GitHub Issue</button>
    </div>
  </div>
</div>

<script>
  (function () {{
    "use strict";

    var galleryState = {{
      email: "analyst@lbl.gov",
      role: "analyst",
      assignedOpenCount: 0
    }};

    function applyGalleryRoleUI() {{
      var isAdmin = galleryState.role === "admin";
      var emailEl = document.getElementById("gallery-user-email");
      var roleEl = document.getElementById("gallery-user-role");
      if (emailEl) emailEl.textContent = galleryState.email;
      if (roleEl) roleEl.textContent = galleryState.role;

      var badgeText = "My Assigned Reviews (" + String(galleryState.assignedOpenCount || 0) + ")";
      var b1 = document.getElementById("badge-my-assigned-reviews");
      var b2 = document.getElementById("card4-assigned-reviews-badge");
      if (b1) b1.textContent = badgeText;
      if (b2) b2.textContent = badgeText;

      // Role-aware gating for Product 5 (Admin-only DB Environment Drift Dashboard)
      var heroLink5 = document.getElementById("hero-link-product5");
      var btnOpen5 = document.getElementById("btn-open-product5");
      var lockBadge5 = document.getElementById("product5-lock-badge");
      var notice5 = document.getElementById("product5-analyst-notice");
      var card5 = document.getElementById("product-card-5-drift");

      if (heroLink5) {{
        heroLink5.style.display = isAdmin ? "inline-block" : "none";
      }}
      if (btnOpen5) {{
        btnOpen5.style.display = isAdmin ? "inline-block" : "none";
      }}
      if (lockBadge5) {{
        lockBadge5.textContent = isAdmin ? "🔓 Admin Unlocked" : "🔒 Admin Role Required";
        lockBadge5.className = "badge " + (isAdmin ? "bg-success" : "bg-danger");
      }}
      if (notice5) {{
        notice5.style.display = isAdmin ? "none" : "block";
      }}
      if (card5) {{
        card5.setAttribute("data-role-state", isAdmin ? "unlocked" : "locked");
      }}
    }}

    function fetchPortalSession() {{
      fetch("/v1/qc/auth/me", {{ credentials: "same-origin" }})
        .then(function (r) {{ return r.ok ? r.json() : null; }})
        .then(function (data) {{
          if (data && data.email) {{
            galleryState.email = data.email;
            galleryState.role = data.role || "analyst";
            if (typeof data.assigned_open_count === "number") {{
              galleryState.assignedOpenCount = data.assigned_open_count;
            }}
          }}
          applyGalleryRoleUI();
        }})
        .catch(function () {{
          applyGalleryRoleUI();
        }});
    }}

    if (typeof window !== "undefined" && "BroadcastChannel" in window) {{
      try {{
        var bc = new BroadcastChannel("biocirv_qc_decisions");
        bc.onmessage = function () {{
          fetchPortalSession();
        }};
      }} catch (e) {{}}
    }}

    var toggleBtn = document.getElementById("btn-gallery-toggle-role");
    if (toggleBtn) {{
      toggleBtn.addEventListener("click", function () {{
        if (galleryState.role === "admin") {{
          galleryState.role = "analyst";
          galleryState.email = "analyst@lbl.gov";
        }} else {{
          galleryState.role = "admin";
          galleryState.email = "admin@lbl.gov";
        }}
        applyGalleryRoleUI();
      }});
    }}

    applyGalleryRoleUI();
    fetchPortalSession();

    var bugModal = document.getElementById("modal-report-bug");
    var openBugBtn = document.getElementById("btn-open-bug-modal");
    function getBugDiagnosticsObject() {{
      return {{
        page: "BioCirV 5-Product Portal Gallery",
        resource: "all",
        domainTab: "portal_gallery (" + (galleryState.role || "analyst") + ")",
        qcFilter: "pass",
        queryString: window.location.search || "(none)"
      }};
    }}
    function buildGitHubBugIssueUrl(opts) {{
      var repoUrl = "https://github.com/uw-ssec/ca-biositing/issues/new";
      var title = (opts.title || "").trim() || ("[Dashboard Bug] " + (opts.category || "Issue") + " on " + (opts.page || "Portal Gallery"));
      var bodyLines = [
        "### Dashboard Bug / Data QC Report",
        "",
        "- **Category:** " + (opts.category || "UI / Chart Rendering Bug"),
        "- **Dashboard Page:** " + (opts.page || "BioCirV 5-Product Portal Gallery"),
        "- **Active Resource:** `" + (opts.resource || "all") + "`",
        "- **Active Tab / Role:** `" + (opts.domainTab || "portal_gallery") + "`",
        "- **URL Query State:** `" + (opts.queryString || "(none)") + "`",
        "- **Timestamp (UTC):** `" + new Date().toISOString() + "`",
        "",
        "### Observed Behavior / Steps to Reproduce",
        opts.description || "_Please describe what happened..._",
        "",
        "### Expected Behavior",
        opts.expectedBehavior || "_Optional: describe what you expected to see._"
      ];
      var params = new URLSearchParams();
      params.set("title", title);
      params.set("body", bodyLines.join("\\n"));
      params.set("labels", "bug,dashboard");
      return repoUrl + "?" + params.toString();
    }}
    if (openBugBtn && bugModal) {{
      openBugBtn.addEventListener("click", function () {{
        var diag = getBugDiagnosticsObject();
        var diagEl = document.getElementById("bug-modal-diagnostics");
        if (diagEl) {{
          diagEl.textContent =
            "Page: " + diag.page +
            "\\nRole: " + galleryState.role + " (" + galleryState.email + ")" +
            "\\nQuery: " + diag.queryString;
        }}
        var statusEl = document.getElementById("bug-modal-status");
        if (statusEl) statusEl.classList.add("hidden");
        bugModal.classList.remove("hidden");
      }});
    }}
    ["btn-close-bug-modal", "btn-cancel-bug-modal"].forEach(function (id) {{
      var el = document.getElementById(id);
      if (el && bugModal) {{
        el.addEventListener("click", function () {{
          bugModal.classList.add("hidden");
        }});
      }}
    }});
    var submitUrlBtn = document.getElementById("btn-submit-github-url");
    if (submitUrlBtn) {{
      submitUrlBtn.addEventListener("click", function () {{
        var diag = getBugDiagnosticsObject();
        var issueUrl = buildGitHubBugIssueUrl({{
          title: (document.getElementById("bug-modal-title") || {{}}).value || "",
          category: (document.getElementById("bug-modal-category") || {{}}).value || "UI / Chart Rendering Bug",
          description: (document.getElementById("bug-modal-desc") || {{}}).value || "",
          expectedBehavior: (document.getElementById("bug-modal-expected") || {{}}).value || "",
          page: diag.page,
          resource: diag.resource,
          domainTab: diag.domainTab,
          qcFilter: diag.qcFilter,
          queryString: diag.queryString
        }});
        window.open(issueUrl, "_blank", "noopener");
        if (bugModal) bugModal.classList.add("hidden");
      }});
    }}
    var submitApiBtn = document.getElementById("btn-submit-github-api");
    if (submitApiBtn) {{
      submitApiBtn.addEventListener("click", async function () {{
        var diag = getBugDiagnosticsObject();
        var payload = {{
          title: (document.getElementById("bug-modal-title") || {{}}).value || "BioCirV Dashboard Bug Report",
          category: (document.getElementById("bug-modal-category") || {{}}).value || "UI / Chart Rendering Bug",
          description: (document.getElementById("bug-modal-desc") || {{}}).value || "",
          expected_behavior: (document.getElementById("bug-modal-expected") || {{}}).value || "",
          page: diag.page,
          resource: diag.resource,
          domain_tab: diag.domainTab,
          qc_filter: diag.qcFilter,
          query_string: diag.queryString,
          create_via_api: true
        }};
        var statusEl = document.getElementById("bug-modal-status");
        if (statusEl) {{
          statusEl.textContent = "⏳ Submitting issue via /v1/qc/github-issue...";
          statusEl.classList.remove("hidden");
        }}
        try {{
          var apiBase = window.BIOCIRV_API_BASE || "http://localhost:8000";
          var resp = await fetch(apiBase + "/v1/qc/github-issue", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify(payload)
          }});
          if (resp.ok) {{
            var data = await resp.json();
            if (data.created_via_api) {{
              if (statusEl) {{
                statusEl.textContent = "✓ GitHub Issue #" + (data.issue_number ?? "") + " created & recorded in PostgreSQL QC Ledger (ID #" + (data.decision_id ?? "") + ")!";
                statusEl.classList.remove("hidden");
              }}
              return;
            }}
            if (data.persisted) {{
              if (statusEl) {{
                statusEl.textContent = "✓ Issue recorded in PostgreSQL QC Ledger (ID #" + (data.decision_id ?? "") + ").";
                statusEl.classList.remove("hidden");
              }}
              return;
            }}
            if (data.issue_url) {{
              window.open(data.issue_url, "_blank", "noopener");
              if (bugModal) bugModal.classList.add("hidden");
              return;
            }}
          }}
        }} catch (_err) {{}}
        var fallbackUrl = buildGitHubBugIssueUrl({{
          title: payload.title,
          category: payload.category,
          description: payload.description,
          expectedBehavior: payload.expected_behavior,
          page: diag.page,
          resource: diag.resource,
          domainTab: diag.domainTab,
          qcFilter: diag.qcFilter,
          queryString: diag.queryString
        }});
        window.open(fallbackUrl, "_blank", "noopener");
        if (bugModal) bugModal.classList.add("hidden");
      }});
    }}
  }})();
</script>
</body>
</html>
"""

    os.makedirs(target_dir, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as handle:
        handle.write(html_content)
    with open(login_file, "w", encoding="utf-8") as handle:
        handle.write(render_login_html(timestamp_str))

    print(f"Gallery generated at {output_file}")
    print(f"Portal login generated at {login_file}")
    return output_file, login_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate BioCirV 5-Product Gallery (index.html) and Login Portal (login.html)."
    )
    parser.add_argument("--base-dir", default=".", help="Base repository directory")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Explicit output directory for index.html and login.html (overrides --base-dir/exports/plots)",
    )
    args = parser.parse_args(argv)
    generate_gallery(base_dir=args.base_dir, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
