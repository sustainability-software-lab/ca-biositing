"""
Extract tasks for CARB food processing facilities Google Sheet.
"""

from .factory import create_extractor

GSHEET_NAME = "food_manufacturers_and_processors_carb"
WORKSHEET_ALL_FACILITIES = "all facilities"
WORKSHEET_GEOCODER_TEST_SET = "test set for geocoder"

extract_all_facilities = create_extractor(
    GSHEET_NAME,
    WORKSHEET_ALL_FACILITIES,
    task_name="extract_food_processing_facilities_all",
)

extract_geocoder_test_set = create_extractor(
    GSHEET_NAME,
    WORKSHEET_GEOCODER_TEST_SET,
    task_name="extract_food_processing_facilities_geocoder_test_set",
)

__all__ = [
    "extract_all_facilities",
    "extract_geocoder_test_set",
]
