import json
import sys
from pathlib import Path

# Assuming your TicketAlertResponse class and helper functions are imported
from ticketalertresponse import ticket_alert_response_from_dict, ticket_alert_response_to_dict

SCRATCH_FOLDER = Path.cwd() / "scratch"

def process_file(filename: str):
    input_path = SCRATCH_FOLDER / filename
    output_path = SCRATCH_FOLDER / f"copy_{filename}"

    # Read the input JSON file
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Convert JSON data to TicketAlertResponse object
    response = ticket_alert_response_from_dict(data)

    # Check url_id for each ResponseDatum
    print("\nChecking url_id values:")
    for item in response.response_data:
        print(f"ID: {item.id} -> URL ID: {item.url_id}")

    # Convert object back to dictionary and write to output file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ticket_alert_response_to_dict(response), f, indent=4)

    # Read both files again and compare
    with open(input_path, "r", encoding="utf-8") as f1, open(output_path, "r", encoding="utf-8") as f2:
        if json.load(f1) == json.load(f2):
            print("\nFiles are equivalent.")
        else:
            print("\nFiles are NOT equivalent.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>")
        sys.exit(1)

    process_file(sys.argv[1])
