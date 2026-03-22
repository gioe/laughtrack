"""
Centralized database connection management for the entire project.

This module provides centralized database connection management using the singleton
ConfigManager pattern. All database connections should go through this module
to ensure consistency and proper resource management.
"""

import time
from contextlib import contextmanager
from typing import Generator

import psycopg2

from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.foundation.infrastructure.logger.logger import Logger

_CONNECT_RETRY_DELAYS = [1, 2, 4]  # seconds between attempts; total max wait ~7s


def create_connection(autocommit: bool = True) -> psycopg2.extensions.connection:
    """
    Create a database connection using the singleton ConfigManager.

    Retries up to 3 times on OperationalError (e.g. Neon auto-suspend wakeup)
    with exponential backoff (1s, 2s, 4s).

    Args:
        autocommit: Whether to enable autocommit mode (default: True)

    Returns:
        psycopg2 database connection

    Raises:
        ValueError: If database configuration is not found
        psycopg2.Error: If connection fails after all retries

    Example:
        with create_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM shows")
                results = cursor.fetchall()
    """
    try:
        db_config = ConfigManager.get_database_configuration()

        if not db_config or not all(db_config.get(key) for key in ["name", "user", "host", "password", "port"]):
            raise ValueError("Database configuration not found or incomplete")

        last_error: psycopg2.OperationalError | None = None
        for attempt, delay in enumerate([0] + _CONNECT_RETRY_DELAYS, start=1):
            if delay:
                Logger.warn(f"DB connection attempt {attempt} failed ({last_error}); retrying in {delay}s")
                time.sleep(delay)
            try:
                conn = psycopg2.connect(
                    database=db_config["name"],
                    user=db_config["user"],
                    host=db_config["host"],
                    password=db_config["password"],
                    port=db_config["port"],
                )
                if autocommit:
                    conn.autocommit = True
                Logger.info("Database connection created successfully")
                return conn
            except psycopg2.OperationalError as e:
                last_error = e

        Logger.error(f"Failed to create database connection: {str(last_error)}")
        raise last_error  # type: ignore[misc]

    except (psycopg2.Error, ValueError):
        raise
    except Exception as e:
        Logger.error(f"Unexpected error creating database connection: {str(e)}")
        raise


def create_connection_with_transaction() -> psycopg2.extensions.connection:
    """
    Create a database connection with autocommit disabled for transaction management.

    Returns:
        psycopg2 database connection with autocommit=False

    Example:
        with create_connection_with_transaction() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("INSERT INTO shows ...")
                    cursor.execute("INSERT INTO tickets ...")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    """
    return create_connection(autocommit=False)


@contextmanager
def get_connection(autocommit: bool = True) -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager for database connections with automatic cleanup.

    Args:
        autocommit: Whether to enable autocommit mode (default: True)

    Yields:
        psycopg2 database connection

    Example:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM shows")
                results = cursor.fetchall()
    """
    conn = None
    try:
        conn = create_connection(autocommit=autocommit)
        yield conn
    finally:
        if conn:
            conn.close()
            Logger.info("Database connection closed")


@contextmanager
def get_transaction() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager for database transactions with automatic rollback on error.

    Yields:
        psycopg2 database connection with transaction management

    Example:
        with get_transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO shows ...")
                cursor.execute("INSERT INTO tickets ...")
            # Automatic commit on success, rollback on exception
    """
    conn = None
    try:
        conn = create_connection(autocommit=False)
        yield conn
        conn.commit()
        Logger.info("Transaction committed successfully")
    except Exception as e:
        if conn:
            conn.rollback()
            Logger.error(f"Transaction rolled back due to error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
