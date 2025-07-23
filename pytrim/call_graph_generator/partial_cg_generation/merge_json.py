import argparse
import json
import os


def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge JSON files into a single JSON list."
    )
    parser.add_argument(
        "-d",
        "--directory",
        required=True,
        help="Directory to search for partial call graph files",
    )
    parser.add_argument(
        "-json",
        "--json",
        required=True,
        help="Path to json file with resolved dependencies",
    )
    parser.add_argument("-o", "--output", required=True, help="Output JSON file name")
    parser.add_argument(
        "-project",
        "--project",
        action="store_true",
        help="True whenever we want to filter out project with failed cg, Fasle when we want to filter out projects with failed deps",
    )
    return parser.parse_args()


def merge_json_app(directory, output_file, result_dict):
    all_data = []
    # Walk through the directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if the file is a JSON file
            if file == "cg.json" and "apps" in root:
                parts = root.split(os.sep)
                key = parts[-2] + "/" + parts[-1]
                value = result_dict[key]
                all_data.append({key: value})

    # Write all data to a single JSON file
    with open(output_file, "w") as f:
        json.dump(all_data, f, indent=2)


def merge_json_dep(directory, output_file, result_dict):
    available_deps = set()
    # Walk through the directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if the file is a JSON file
            if file == "cg.json" and "app" not in root:
                parts = root.split(os.sep)
                key = parts[-2] + "/" + parts[-1]
                available_deps.add(key.replace("/", ":"))
    keys_to_remove = []
    for key, values in result_dict.items():
        if not all(value in available_deps for value in values):
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del result_dict[key]
    project_list = []
    for key, value in result_dict.items():
        project_list.append({key: value})
    # Write all data to a single JSON file
    with open(output_file, "w") as f:
        json.dump(project_list, f, indent=2)


def main():
    args = parse_args()
    file = open(args.json)
    data = json.load(file)
    result_dict = {}
    for json_str in data:
        data = json.loads(json.dumps(json_str))
        result_dict.update(data)
    if args.project:
        merge_json_app(args.directory, args.output, result_dict)
    else:
        merge_json_dep(args.directory, args.output, result_dict)


if __name__ == "__main__":
    main()
