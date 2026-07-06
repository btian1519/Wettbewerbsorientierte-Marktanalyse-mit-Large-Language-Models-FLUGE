"""Shared, cross-cutting concerns: configuration, constants, logging and utilities.

This package must not depend on any other project package so that it can be
imported from anywhere (frontend, backend, database, ingestion) without creating
circular dependencies.
"""
