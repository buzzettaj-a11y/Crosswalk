"""The output files and their columns (SPEC 9.1, C-26). OUTPUT_COLUMNS is the one list the chips and the headers read."""
from enum import Enum


class FileId(Enum):
    FINAL_CLEAN_MAPPED = "Final_Clean_Mapped"
    UNIQUE_CLIENTS = "Unique_Clients"
    UNIQUE_CLIENTS_BY_PROGRAM = "Unique_Clients_By_Program"
    MANUAL_REVIEW_NEEDED = "Manual_Review_Needed"
    SET_ASIDE_RECORDS = "Set_Aside_Records"
    MAP_COUNTS = "Map_Counts"
    MAP_POINTS = "Map_Points"
    DATA_QUALITY_REPORT = "Data_Quality_Report"
    INTERNAL_AUDIT_LOG = "Internal_Audit_Log"
    SHAREABLE_AUDIT_LOG = "Shareable_Audit_Log"


TABLE_FILES = (FileId.FINAL_CLEAN_MAPPED, FileId.UNIQUE_CLIENTS, FileId.UNIQUE_CLIENTS_BY_PROGRAM, FileId.MANUAL_REVIEW_NEEDED,
               FileId.SET_ASIDE_RECORDS, FileId.MAP_COUNTS, FileId.MAP_POINTS, FileId.DATA_QUALITY_REPORT)
LOG_FILES = (FileId.INTERNAL_AUDIT_LOG, FileId.SHAREABLE_AUDIT_LOG)
NAME_FIELDS = ("First_Name", "Middle_Initial", "Last_Name")
ADDRESS_FIELDS = ("Address_1", "Address_2", "City", "State", "Zip")
DISTRICT_COLUMNS = ("Senate_District", "Assembly_District", "Council_District")
PRACTICE_COLUMN = "PRACTICE"


def clean_columns(fields, practice, exact_coordinates):
    cols = list(fields) + ["Count_Status", "Location_Status", "Location_Confidence"]
    if not practice:
        cols += list(DISTRICT_COLUMNS)
    if exact_coordinates:
        cols += ["Latitude", "Longitude"]
    return cols + ["Source_File", "Source_Row", "Record_Key", "Duplicate_In_File", "Possible_Duplicate_Of"]


def unique_columns(fields):
    person = [f for f in NAME_FIELDS + ADDRESS_FIELDS if f in fields]
    dob = ["Date_of_Birth"] if "Date_of_Birth" in fields else []
    return ["Master_ID"] + person + dob + ["Programs", "Systems", "Source_Records", "Match_Confidence"]


def output_columns(file_id, view, settings):
    """The header of one file, before any column is switched off."""
    if file_id == FileId.FINAL_CLEAN_MAPPED:
        cols = clean_columns(view.fields, view.practice, settings.exact_coordinates)
    elif file_id == FileId.UNIQUE_CLIENTS:
        cols = unique_columns(view.fields)
    elif file_id == FileId.UNIQUE_CLIENTS_BY_PROGRAM:
        cols = ["Master_ID", "Program", "Source_Records"]
    elif file_id == FileId.MANUAL_REVIEW_NEEDED:
        from wholecount.engine.outputs.review_file import review_columns
        cols = review_columns(view)
    elif file_id == FileId.SET_ASIDE_RECORDS:
        cols = ["Record_Key", "Source_File", "Source_Row", "Reason", "Kept_Record_Key"]
    elif file_id == FileId.MAP_COUNTS:
        cols = ["Program", "District_Type", "District", "Count"]
    elif file_id == FileId.MAP_POINTS:
        cols = ["Program", "Latitude", "Longitude"]
    elif file_id == FileId.DATA_QUALITY_REPORT:
        cols = (["Source_File", "Table", "Rows_Received", "Counted", "Not_Counted_Yet", "Set_Aside", "Mapped", "Counted_Not_Mapped"]
                + [f"Problem_{p}" for p in view.problem_ids] + ["Invisible_Characters_Removed", "Encoding"])
    else:
        raise ValueError(file_id)
    return ([PRACTICE_COLUMN] if view.practice else []) + cols


def chip_columns(file_id, view, settings):
    """The columns Download shows chips for, which are exactly the written header (OUT-1)."""
    off = settings.columns_off.get(file_id, frozenset())
    return [c for c in output_columns(file_id, view, settings) if c not in off or c == PRACTICE_COLUMN]
