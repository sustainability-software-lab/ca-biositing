#!/usr/bin/env python3
"""
Database reset orchestrator for ca-biositing.

Implements a standardized, repeatable reset process for local, staging, and
production environments. Handles schema wipes, migrations, ownership transfers,
and permission management.

Usage:
    python scripts/db_reset.py --env staging
    python scripts/db_reset.py --env production --force
    python scripts/db_reset.py --env local --dry-run
"""

import argparse
import logging
import sys
import os
import re
from pathlib import Path
from typing import Dict, Any, Union
from datetime import datetime

import psycopg2
import yaml
from jinja2 import Template

class DatabaseResetOrchestrator:
    """Orchestrates database reset across multiple phases."""

    def __init__(self, env: str, config_path: str, dry_run: bool = False, force: bool = False):
        self.env = env
        self.dry_run = dry_run
        self.force = force
        self.config = self._load_config(config_path)
        if env not in self.config['environments']:
            raise ValueError(f"Environment '{env}' not found in configuration")
        self.env_config = self.config['environments'][env]
        self.logger = self._setup_logging()
        self.conn = None

    def _setup_logging(self) -> logging.Logger:
        """Configure logging to file and console."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # File handler
        log_dir = Path("logs") / "db_reset"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / f"reset_{self.env}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        fh.setLevel(logging.DEBUG)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _expand_env_vars(self, obj: Any) -> Any:
        """
        Recursively expand environment variables in config.
        Supports ${VAR} and ${VAR:-default} syntax.
        Handles one level of nested expansion like ${VAR:-${OTHER_VAR}}.
        """
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(v) for v in obj]
        elif isinstance(obj, str):
            # Match ${VAR} or ${VAR:-default}
            # The inner part ((?:[^{}]|\{[^{}]*\})*) matches non-braces OR balanced single-level braces
            pattern = re.compile(r'\${(\w+)(?::-((?:[^{}]|\{[^{}]*\})*))?}')

            def replace(match):
                var_name = match.group(1)
                default_value = match.group(2)
                value = os.getenv(var_name)
                if value is not None:
                    return value

                if default_value is not None:
                    # Recursive expansion for the default value
                    return pattern.sub(replace, default_value)

                raise ValueError(f"Environment variable {var_name} not set and no default provided")

            # If the entire string is just one variable, we might want to preserve types (like int for port)
            single_match = pattern.fullmatch(obj)
            if single_match:
                val = replace(single_match)
                # Try to convert to int if it looks like one
                try:
                    if isinstance(val, str) and val.isdigit():
                        return int(val)
                except (AttributeError, ValueError):
                    pass
                return val

            return pattern.sub(replace, obj)
        return obj

    def connect(self):
        """Establish database connection as postgres user."""
        config = self._expand_env_vars(self.env_config)

        # Clean up connection parameters
        host = str(config['host']).strip()
        port = int(config['port'])
        database = str(config['database']).strip()
        user = str(config['postgres_user']).strip()
        password = str(config['postgres_password']).strip() # CRITICAL: Strip newlines/whitespace

        try:
            self.logger.info(f"Attempting connection to {host}:{port}...")
            self.logger.info(f"User: {user}, Database: {database}")

            # Debug: Check if password was actually loaded
            if not password:
                self.logger.warning("Connection password is empty!")
            else:
                self.logger.debug(f"Password loaded (length: {len(password)})")
                # HEX DEBUG: Log the characters to find hidden ones
                # hex_debug = " ".join([hex(ord(c)) for c in password])
                # self.logger.debug(f"Password Hex: {hex_debug}")

            try:
                self.conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password
                )
            except psycopg2.Error as e:
                # If connecting to the app database fails, try connecting to 'postgres' database
                if database != 'postgres':
                    self.logger.info(f"Primary connection failed, attempting fallback to 'postgres' database...")
                    self.conn = psycopg2.connect(
                        host=host,
                        port=port,
                        database='postgres',
                        user=user,
                        password=password
                    )
                else:
                    raise e

            self.logger.info(f"Connected to {self.env} database server")
        except psycopg2.Error as e:
            self.logger.error(f"Failed to connect to database server: {e}")
            raise

    def validate_connection(self):
        """Validate database is accessible."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT version()")
                self.logger.info(f"Database version: {cur.fetchone()[0]}")
        except psycopg2.Error as e:
            self.logger.error(f"Connection validation failed: {e}")
            raise

    def prompt_confirmation(self):
        """Prompt user to confirm reset before proceeding."""
        if self.force or self.dry_run:
            return True

        if not self.env_config.get('prompt_for_confirmation', True):
            return True

        # Expand vars for display
        config = self._expand_env_vars(self.env_config)

        message = f"""
╔════════════════════════════════════════════════════════════════════╗
║                    ⚠️  DATABASE RESET CONFIRMATION  ⚠️             ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  Environment: {self.env.upper():>40}             ║
║  Host:        {str(config['host']):>40}             ║
║  Database:    {str(config['database']):>40}             ║
║                                                                    ║
║  Action: DROP ALL SCHEMAS AND REBUILD                             ║
║                                                                    ║
║  This will:                                                        ║
║    • Drop schemas: public, ca_biositing, data_portal              ║
║    • Recreate public schema and extensions                        ║
║    • Transfer ownership to {str(config['biocirv_user']):<31} ║
║    • Grant read-only access to {str(config['biocirv_readonly']):<27} ║
║                                                                    ║
║  All data will be PERMANENTLY DELETED.                            ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
"""
        print(message)
        response = input("Type 'yes' to confirm reset: ").strip().lower()

        if response != 'yes':
            self.logger.info("Reset cancelled by user")
            return False

        return True

    def execute_phase(self, phase_num: int, sql_file: str):
        """Execute a single phase of the reset."""
        sql_path = Path(__file__).parent / "sql" / sql_file

        if not sql_path.exists():
            raise FileNotFoundError(f"SQL script not found: {sql_path}")

        with open(sql_path) as f:
            sql = f.read()

        # Expand env vars for the template context
        context = self._expand_env_vars(self.env_config)

        # Add global config to context for list-based operations
        context['schemas'] = self.config.get('schemas', [])
        context['extensions'] = self.config.get('extensions', [])

        # Template the SQL
        template = Template(sql)
        rendered_sql = template.render(**context)

        if self.dry_run:
            self.logger.info(f"DRY RUN: Phase {phase_num} - {sql_file}")
            self.logger.debug(f"SQL that would be executed:\n{rendered_sql}")
            return

        try:
            with self.conn.cursor() as cur:
                self.logger.info(f"Executing Phase {phase_num}: {sql_file}")
                # Ensure we are operating on the correct database if we used fallback
                # Note: Cloud SQL doesn't support CROSS-DATABASE queries, so we must be on the right DB.
                # The SQL scripts themselves should be schema-qualified.
                cur.execute(rendered_sql)

                # Log any notices from PostgreSQL
                if self.conn.notices:
                    for notice in self.conn.notices:
                        self.logger.info(f"PG NOTICE: {notice.strip()}")
                    del self.conn.notices[:]

                self.conn.commit()
                self.logger.info(f"Phase {phase_num} completed successfully")
        except psycopg2.Error as e:
            if self.conn:
                self.conn.rollback()
            self.logger.error(f"Phase {phase_num} failed: {e}")
            raise

    def reset(self):
        """Execute the complete reset process."""
        try:
            # Phase 0: Validation
            self.logger.info(f"Starting database reset for {self.env} environment")

            if not self.dry_run:
                self.connect()
                self.validate_connection()

            # Phase 0.5: Confirmation
            if not self.prompt_confirmation():
                sys.exit(1)

            # Phase 1: Wipe schemas
            self.execute_phase(1, "db_reset_wipe.sql")

            # Phase 2: Transfer ownership
            self.execute_phase(2, "db_reset_ownership.sql")

            # Phase 3: Grant read-only access
            self.execute_phase(3, "db_reset_readonly.sql")

            if self.dry_run:
                self.logger.info("✅ Dry run completed successfully")
            else:
                self.logger.info("✅ Database reset completed successfully")
                self.logger.info("Next steps: Run 'pixi run migrate' to apply migrations, then 'pixi run run-etl' to trigger ETL")

        except Exception as e:
            self.logger.error(f"❌ Database reset failed: {e}")
            if not self.dry_run:
                raise
        finally:
            if self.conn:
                self.conn.close()

def main():
    parser = argparse.ArgumentParser(
        description="Standardized database reset for ca-biositing"
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["local", "staging", "production"],
        help="Target environment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview reset without executing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--config",
        default="resources/config/db_reset.yaml",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    # Ensure we are in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    try:
        orchestrator = DatabaseResetOrchestrator(
            env=args.env,
            config_path=args.config,
            dry_run=args.dry_run,
            force=args.force
        )
        orchestrator.reset()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
