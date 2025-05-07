# json-diff-checker

## Table of Contents

- [Description](#description)
- [Usage](#usage)
  - [Locally](#locally)
  - [Docker](#docker)
- [Example Usage](#example-usage)
- [Output Files](#output-files)
- [Contributions](#contributions)
- [License](#license)

## Description

This script compares JSON schema files between two directories, providing:
- Common schemas between both directories
- Unique schemas in each directory
- Detailed differences between versions of common schemas

It now generates two output files:
1. A text diff using `json-diff` for detailed line-by-line changes
2. A structured markdown report that better handles complex JSON schema structures like objects and arrays

## Usage

### Prerequisites

- Clone the repository:
    ```bash
    git clone https://github.com/idb_antonioalanis/json-diff-checker.git
    ```
- Navigate to the project directory:
    ```bash
    cd json-diff-checker
    ```

### Locally

1. Install Python 3.6 or higher:
    ```bash
    sudo apt update && \
    sudo apt install -y python3
    ```

2. Install `json-diff` via `npm`:
    ```bash
    npm install -g json-diff
    ```

3. Run the script:
    ```bash
    python3 json_diff_checker.py \
      --first_directory <first_directory> \
      --second_directory <second_directory> \
      --first_prefix <first_prefix> \
      --second_prefix <second_prefix> \
      [--output_file <output_filename>] \
      [--markdown_file <markdown_filename>]
    ```

**Parameters:**
- `--first_directory`: Path to directory with first version schemas
- `--second_directory`: Path to directory with second version schemas
- `--first_prefix`: File prefix for first directory files
- `--second_prefix`: File prefix for second directory files
- `--output_file`: Output filename for text diff (optional, default: `schema_comparison_results.txt`)
- `--markdown_file`: Output filename for markdown report (optional, default: `schema_changes_summary.md`)

### Docker

1. Make sure you have Docker installed on your machine. You can install it via `apt`:
    ```bash
    sudo apt update && \
    sudo apt install docker.io
    ```

2. Run the [build-and-run-image.sh](build-and-run-image.sh) script:
    ```bash
    ./build_and_run_image.sh \
      --first_directory <first_directory> \
      --second_directory <second_directory> \
      --first_prefix <first_prefix> \
      --second_prefix <second_prefix> \
      [--output_file <output_filename>] \
      [--markdown_file <markdown_filename>]
    ```

**Parameters:**
- `--first_directory`: Path to directory with first version schemas
- `--second_directory`: Path to directory with second version schemas
- `--first_prefix`: File prefix for first directory files
- `--second_prefix`: File prefix for second directory files
- `--output_file`: Output filename (optional, default: `schema_comparison_results.txt`)
- `--markdown_file`: Output filename for markdown report (optional, default: `schema_changes_summary.md`)

## Example Usage

Suppose you have two directories: `/v1` and `/v2` with the following files:

```
/v1
  ├── schema_user_v1.json
  ├── schema_product_v1.json
  └── schema_order_v1.json

/v2
  ├── schema_user_v2.json
  ├── schema_product_v2.json
  └── schema_payment_v2.json
```

Running the script with:
```bash
python3 json_diff_checker.py \
  --first_directory v1 \
  --second_directory v2 \
  --first_prefix schema_ \
  --second_prefix schema_ \
  --output_file comparison.txt \
  --markdown_file changes_summary.md
```

## Output Files

### Text Diff Output (comparison.txt)

```
2023-11-15 14:30:45

First directory - /v1 (prefix 'schema_')
Second directory - /v2 (prefix 'schema_')

Found the next 1 unique schemas in /v1.
  · order

Found the next 1 unique schemas in /v2.
  · payment

Found the next 2 matching schemas.
  · product
  · user

💠 Comparing schema 'product'...
    First directory file - schema_product_v1.json
    Second directory file - schema_product_v2.json
  {
+   "new_property": "value",
-   "removed_property": "old_value"
  }

-----------------------------------------------------------

💠 Comparing schema 'user'...
    First directory file - schema_user_v1.json
    Second directory file - schema_user_v2.json
  {
    "username": "string",
+   "email": "string",
    "password": "string"
  }
```

### Markdown Report (changes_summary.md)

```markdown
# JSON Schema Changes Summary

This document lists all the changes (new, removed, and modified fields) for each schema.

---

## **product**
### **New Fields**
- **new_property**

### **Removed Fields**
- **removed_property**

### **Modified Fields**
- None.

---

## **user**
### **New Fields**
- **email**

### **Removed Fields**
- None.

### **Modified Fields**
- None.

---
```

The markdown report provides a more structured view of the changes, making it easier to identify:
- New fields added in the newer schema version
- Removed fields that existed in the older schema version
- Modified fields where the type or structure has changed

The enhanced schema analysis now properly handles:
- Nested objects and their properties
- Array structures and their item definitions
- Type changes, including handling nullable types
- Common changes that are inherited by all schemas

## Contributions

To contribute to the project:
1. Fork the repository
2. Create a feature/fix branch (`git checkout -b feature/new-feature`)
3. Commit your changes following [Conventional Commits](https://www.conventionalcommits.org/) format
4. Push to your branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
