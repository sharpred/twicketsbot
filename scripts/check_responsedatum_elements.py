import json
from pathlib import Path
from typing import List
from ticketalertresponse import ResponseDatum  # Assuming your classes are in response_classes.py
from helpers import compare_json_files
SCRATCH_FOLDER = Path.cwd() / "scratch"

def test_response_datum_file(filename: str):
    file_path = SCRATCH_FOLDER / filename
    new_file_path = SCRATCH_FOLDER / f"new_{filename}"

    # Read JSON file
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Convert JSON to List[ResponseDatum]
    response_data: List[ResponseDatum] = [ResponseDatum.from_dict(item) for item in data]

    # Write back to a new file
    with open(new_file_path, "w", encoding="utf-8") as f:
        json.dump([item.to_dict() for item in response_data], f, indent=4)

    # Verify the files are identical
    files_match = compare_json_files(file_path, new_file_path)
    
    # Check url_id for each ResponseDatum
    for item in response_data:
        print(f"ID: {item.id}, URL ID: {item.url_id}")
        print(f"Single ticket {item.single_ticket}")
        print(f"Required ticket {item.is_required_ticket}")

if __name__ == "__main__":
    test_response_datum_file("main_event.json")
