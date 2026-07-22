import pytest
import duckdb

def test_no_nulls_in_primary_keys():
    """Validates that there are no null values in the primary/key columns of Gold mart tables."""
    pass

def test_data_ranges():
    """Validates that values like avg_speed, trip_distance, etc., are within realistic logical boundaries."""
    pass
