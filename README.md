# VCard-Parser

# 📇 vCard Manager

Welcome! This project is a vCard management system written in C and Python, integrating C structs and logic with a dynamic Python-based terminal UI using `asciimatics`.

## 🚀 Overview

This project is a vCard management system that lets users load, validate, create, and edit .vcf contact files. It combines a C-based backend for vCard parsing with a Python terminal UI, allowing users to interact with contact data in a structured and accessible way. A MySQL database is used to store validated information, making it easy to run queries and manage contacts efficiently from the command line.

## 🧠 Functionality Highlights

- ✅ **vCard Validation & Parsing**
  - Written in C, the vCard parser dynamically creates and validates cards using a custom `Card` struct.
  - Cards are validated against standard rules, ensuring only correct vCards are saved or processed.

- 📁 **Loading `.vcf` Files**
  - The program scans a `cards/` folder at startup and automatically loads and validates all `.vcf` files.
  - Valid files are then optionally inserted into a **MySQL database**, extracting:
    - Contact name
    - Birthday (if properly formatted)
    - Anniversary (if present and valid)

- 📝 **Editing Contacts**
  - Users can edit contact names directly through the interface.
  - Changes are reflected both in the `.vcf` file and (when connected) in the MySQL database.

- 🗂️ **Database Integration**
  - Users can connect to a MySQL server to sync vCard files with a structured database.
  - Upon login, tables are created (`FILE`, `CONTACT`), and files are loaded if they don't already exist.
  - Supports advanced queries like:
    - Display all contacts
    - Find contacts born in June (sorted by age)

- 📊 **Dynamic Query View**
  - Query results are displayed in a clean table format.
  - After each query, a summary alert shows how many files and contacts exist in the DB.

- 💡 **Built-in Safeguards**
  - Prevents invalid edits (e.g., empty contact name or wrong file format)
  - UI elements and query buttons are only active when appropriate (e.g., only after DB login)

## 🖥️ Technologies Used

- **C** – For core card parsing and validation
- **Python 3** – For UI and DB handling
- **MySQL Connector (Python)** – For database communication
- **CTypes** – For calling C functions from Python


## 🗄️ Database Structure

### FILE Table
| Column         | Type         | Description                        |
|----------------|--------------|------------------------------------|
| file_id        | INT (PK)     | Unique identifier for each file    |
| file_name      | VARCHAR(60)  | Name of the `.vcf` file            |
| last_modified  | DATETIME     | Last modification timestamp        |
| creation_time  | DATETIME     | Time file was added to the DB      |

### CONTACT Table
| Column         | Type         | Description                                 |
|----------------|--------------|---------------------------------------------|
| contact_id     | INT (PK)     | Unique ID for each contact                  |
| name           | VARCHAR(256) | FN property value from vCard                |
| birthday       | DATETIME     | Parsed from BDAY property                   |
| anniversary    | DATETIME     | Parsed from ANNIVERSARY property            |
| file_id        | INT (FK)     | Reference to the `FILE` table (ON DELETE CASCADE) |

## Note

Source code is intentionally excluded to preserve academic integrity, as this project is part of a university course.
