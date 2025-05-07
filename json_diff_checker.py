import os
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Any, Optional


def get_schema_names(files, prefix):
    return [
        file_name[len(prefix) :].replace("_schema.json", "")
        for file_name in files
        if file_name.startswith(prefix)
    ]


def find_common_schemas(first_directory, second_directory, first_prefix, second_prefix):
    if not first_directory.exists():
        raise FileNotFoundError(f"Directory '{first_directory}' not found.")
    if not second_directory.exists():
        raise FileNotFoundError(f"Directory '{second_directory}' not found.")

    first_directory_files = {
        file.name for file in first_directory.iterdir() if file.is_file()
    }
    second_directory_files = {
        file.name for file in second_directory.iterdir() if file.is_file()
    }

    first_directory_schema_names = set(
        get_schema_names(first_directory_files, first_prefix)
    )
    second_directory_schema_names = set(
        get_schema_names(second_directory_files, second_prefix)
    )

    common_schemas = first_directory_schema_names & second_directory_schema_names
    first_directory_unique_schemas = (
        first_directory_schema_names - second_directory_schema_names
    )
    second_directory_unique_schemas = (
        second_directory_schema_names - first_directory_schema_names
    )

    first_directory_file_mapping = {
        get_schema_names([file.name], first_prefix)[0]: file
        for file in first_directory.iterdir()
        if file.is_file() and file.name.startswith(first_prefix)
    }

    second_directory_file_mapping = {
        get_schema_names([file.name], second_prefix)[0]: file
        for file in second_directory.iterdir()
        if file.is_file() and file.name.startswith(second_prefix)
    }

    return (
        common_schemas,
        first_directory_unique_schemas,
        second_directory_unique_schemas,
        first_directory_file_mapping,
        second_directory_file_mapping,
    )


def compare(first_file, second_file):
    try:
        result = subprocess.run(
            ["json-diff", str(first_file), str(second_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as error:
        if error.returncode == 1:
            return error.stdout.strip()
        return error.stderr.strip()
    except FileNotFoundError:
        raise SystemExit(
            "'json-diff' tool not found. Please install it using 'npm install -g json-diff'."
        )


def write_to_file(file_path, content):
    with open(file_path, "a", encoding="utf-8") as file:
        file.write(content + "\n")


def load_json_schema(file_path: Path) -> Dict:
    """Load and parse a JSON schema file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in file: {file_path}")
    except Exception as e:
        raise IOError(f"Error reading schema file {file_path}: {str(e)}")


def extract_properties(schema: Dict, 
                       path: str = "", 
                       result: Optional[Dict[str, Dict]] = None) -> Dict[str, Dict]:
    """
    Recursively extract all properties from a JSON schema
    
    Args:
        schema: The JSON schema to analyze
        path: Current path in the schema (for nested properties)
        result: Dictionary to store results
        
    Returns:
        Dictionary mapping property paths to their details
    """
    if result is None:
        result = {}
    
    # Handle properties at current level
    if isinstance(schema, dict):
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                prop_path = f"{path}.{prop_name}" if path else prop_name
                
                # Store property details
                result[prop_path] = {
                    "type": get_schema_type(prop_schema),
                    "description": prop_schema.get("description", ""),
                    "required": is_required(schema, prop_name)
                }
                
                # Recursively process nested properties
                if "properties" in prop_schema:
                    extract_properties(prop_schema, prop_path, result)
                    
                # Handle array items with nested properties
                if prop_schema.get("type") == "array" and "items" in prop_schema:
                    if "properties" in prop_schema["items"]:
                        array_path = f"{prop_path}.ARRAY"
                        extract_properties(prop_schema["items"], array_path, result)
        
        # Handle additionalProperties with schema
        if "additionalProperties" in schema and isinstance(schema["additionalProperties"], dict):
            if "properties" in schema["additionalProperties"]:
                add_props_path = f"{path}.MAP" if path else "MAP"
                extract_properties(schema["additionalProperties"], add_props_path, result)
    
    return result


def get_schema_type(schema: Dict) -> str:
    """Extract type information from a schema property"""
    if "type" not in schema:
        return "object" if "properties" in schema else "unknown"
    
    schema_type = schema["type"]
    if isinstance(schema_type, list):
        return f"[\"{'\", \"'.join(schema_type)}\"]"
    return f"\"{schema_type}\""


def is_required(schema: Dict, property_name: str) -> bool:
    """Check if a property is required in the schema"""
    return property_name in schema.get("required", [])


def compare_schemas(first_schema: Dict, second_schema: Dict) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Compare two JSON schemas and identify added, removed, and modified properties
    
    Args:
        first_schema: First JSON schema
        second_schema: Second JSON schema
        
    Returns:
        Tuple containing (new_fields, removed_fields, modified_fields)
    """
    first_properties = extract_properties(first_schema)
    second_properties = extract_properties(second_schema)
    
    # Find new fields (in second but not in first)
    new_fields = []
    for path, details in second_properties.items():
        if path not in first_properties:
            new_fields.append({
                "name": path,
                "type": details["type"]
            })
    
    # Find removed fields (in first but not in second)
    removed_fields = []
    for path, details in first_properties.items():
        if path not in second_properties:
            removed_fields.append({
                "name": path,
                "type": details["type"]
            })
    
    # Find modified fields (in both but with different types)
    modified_fields = []
    for path, first_details in first_properties.items():
        if path in second_properties:
            second_details = second_properties[path]
            if first_details["type"] != second_details["type"]:
                modified_fields.append({
                    "name": path,
                    "change_type": "Type Change",
                    "old_value": first_details["type"],
                    "new_value": second_details["type"]
                })
    
    return new_fields, removed_fields, modified_fields


def generate_markdown_report(schema_changes: Dict[str, Dict]) -> str:
    """
    Generate a markdown report from the schema changes
    
    Args:
        schema_changes: Dictionary with schema names as keys and their changes as values
        
    Returns:
        Markdown formatted string
    """
    markdown = "# JSON Schema Changes Summary\n\n"
    markdown += "This document lists all the changes (new, removed, and modified fields) for each Datablock, including `Core_File`. Changes in description fields are omitted, as well as common changes inherited by all Datablocks (which are only the ones present in Core_File).\n\n---\n\n"
    
    for schema_name, changes in schema_changes.items():
        markdown += f"## **{schema_name}**\n"
        
        # New fields section
        markdown += "### **New Fields**\n"
        if changes["new_fields"]:
            for field in changes["new_fields"]:
                markdown += f"- **{field['name']}**\n"
        else:
            markdown += "- None.\n"
        
        markdown += "\n"
        
        # Removed fields section
        markdown += "### **Removed Fields**\n"
        if changes["removed_fields"]:
            for field in changes["removed_fields"]:
                markdown += f"- **{field['name']}**\n"
        else:
            markdown += "- None.\n"
        
        markdown += "\n"
        
        # Modified fields section
        markdown += "### **Modified Fields**\n"
        if changes["modified_fields"]:
            for field in changes["modified_fields"]:
                markdown += f"- **{field['name']}**:  \n"
                markdown += f"  - **{field['change_type']}**: `{field['old_value']}` → `{field['new_value']}`\n"
        else:
            markdown += "- None.\n"
        
        markdown += "\n---\n\n"
    
    return markdown


def main():
    parser = argparse.ArgumentParser(
        description="Compare JSON schemas between two directories"
    )
    parser.add_argument(
        "--first_directory",
        required=True,
        help="Path to first directory containing schemas",
    )
    parser.add_argument(
        "--second_directory",
        required=True,
        help="Path to second directory containing schemas",
    )
    parser.add_argument(
        "--first_prefix",
        required=True,
        help="File name prefix for schemas in first directory",
    )
    parser.add_argument(
        "--second_prefix",
        required=True,
        help="File name prefix for schemas in second directory",
    )
    parser.add_argument(
        "--output_file",
        default="schema_comparison_results.txt",
        help="Path for output results file",
    )
    parser.add_argument(
        "--markdown_file",
        default="schema_changes_summary.md",
        help="Path for markdown changes summary file",
    )

    arguments = parser.parse_args()

    output_file_path = Path(arguments.output_file)
    markdown_file_path = Path(arguments.markdown_file)
    
    # Clear existing files
    if output_file_path.exists():
        output_file_path.unlink()
    if markdown_file_path.exists():
        markdown_file_path.unlink()

    try:
        first_directory = Path(arguments.first_directory)
        second_directory = Path(arguments.second_directory)

        write_to_file(
            output_file_path,
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        )
        write_to_file(
            output_file_path,
            f"First directory - /{first_directory} (prefix '{arguments.first_prefix}')",
        )
        write_to_file(
            output_file_path,
            f"Second directory - /{second_directory} (prefix '{arguments.second_prefix}')\n",
        )

        (
            common_schemas,
            first_directory_unique_schemas,
            second_directory_unique_schemas,
            first_directory_file_mapping,
            second_directory_file_mapping,
        ) = find_common_schemas(
            first_directory,
            second_directory,
            arguments.first_prefix,
            arguments.second_prefix,
        )

        if first_directory_unique_schemas:
            message = f"Found the next {len(first_directory_unique_schemas)} unique schemas in /{first_directory}."
            write_to_file(output_file_path, message)
            schemas_list = "\n".join(
                [f"  · {schema}" for schema in sorted(first_directory_unique_schemas)]
            )
            write_to_file(output_file_path, schemas_list + "\n")

        if second_directory_unique_schemas:
            message = f"Found the next {len(second_directory_unique_schemas)} unique schemas in /{second_directory}."
            write_to_file(output_file_path, message)
            schemas_list = "\n".join(
                [f"  · {schema}" for schema in sorted(second_directory_unique_schemas)]
            )
            write_to_file(output_file_path, schemas_list + "\n")

        if not common_schemas:
            message = "No matching schemas found between the directories."
            write_to_file(output_file_path, message)
            print(message)
            return

        common_schemas = sorted(common_schemas)

        message = f"Found the next {len(common_schemas)} matching schemas."
        write_to_file(output_file_path, message)
        schemas_list = "\n".join([f"  · {schema}" for schema in common_schemas])
        write_to_file(output_file_path, schemas_list)

        # Dictionary to store schema changes for markdown generation
        schema_changes = {}
        common_changes = None  # Store common Core_File changes to exclude from others

        for index, schema_name in enumerate(common_schemas):
            first_file_path = first_directory_file_mapping[schema_name]
            second_file_path = second_directory_file_mapping[schema_name]

            header = f"💠 Comparing schema '{schema_name}'..."
            files_information = f"    First directory file - {os.path.basename(first_file_path)}\n    Second directory file - {os.path.basename(second_file_path)}"

            write_to_file(output_file_path, f"\n{header}\n{files_information}")

            # Generate classic text diff
            comparison_result = compare(first_file_path, second_file_path)
            if not comparison_result:
                write_to_file(output_file_path, "  Schemas are identical.")
            else:
                write_to_file(output_file_path, comparison_result)

            # Generate detailed schema comparison 
            try:
                first_schema = load_json_schema(first_file_path)
                second_schema = load_json_schema(second_file_path)
                
                new_fields, removed_fields, modified_fields = compare_schemas(first_schema, second_schema)
                
                schema_changes[schema_name] = {
                    "new_fields": new_fields,
                    "removed_fields": removed_fields,
                    "modified_fields": modified_fields
                }
                
                # Store Core_File changes to filter out common changes
                if schema_name == "Core_File":
                    common_changes = {
                        "modified": {field["name"] for field in modified_fields},
                        "new": {field["name"] for field in new_fields},
                        "removed": {field["name"] for field in removed_fields}
                    }
            except Exception as e:
                print(f"Error analyzing schema {schema_name}: {str(e)}")
                schema_changes[schema_name] = {
                    "new_fields": [],
                    "removed_fields": [],
                    "modified_fields": [{
                        "name": "ERROR",
                        "change_type": "Error",
                        "old_value": "",
                        "new_value": f"Failed to analyze: {str(e)}"
                    }]
                }
            
            if index < len(common_schemas) - 1:
                write_to_file(output_file_path, f"\n{'-' * 75}")

        # Filter out common changes from other schemas if Core_File was analyzed
        if common_changes:
            for schema_name, changes in schema_changes.items():
                if schema_name != "Core_File":
                    # Filter modified fields
                    changes["modified_fields"] = [
                        field for field in changes["modified_fields"] 
                        if field["name"] not in common_changes["modified"]
                    ]
                    
                    # Filter new fields
                    changes["new_fields"] = [
                        field for field in changes["new_fields"] 
                        if field["name"] not in common_changes["new"]
                    ]
                    
                    # Filter removed fields
                    changes["removed_fields"] = [
                        field for field in changes["removed_fields"] 
                        if field["name"] not in common_changes["removed"]
                    ]
        
        # Generate and save markdown report
        markdown_report = generate_markdown_report(schema_changes)
        with open(markdown_file_path, 'w', encoding='utf-8') as md_file:
            md_file.write(markdown_report)

        print(f"\nResults saved to '{output_file_path}'.")
        print(f"Markdown summary saved to '{markdown_file_path}'.")
    except Exception as error:
        error_message = str(error)
        print(error_message)
        write_to_file(output_file_path, error_message)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nComparison interrupted by user.")
