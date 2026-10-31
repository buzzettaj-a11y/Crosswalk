"""One RowInput per decision reason that standardizing can raise, and the reason it triggers (M04). M08 reuses this."""
from tests.support.std import row_input
from wholecount.engine.schema import FieldType, default_schema
from wholecount.engine.standardize.model import AddressText, ReasonRef

COUNTING_SCHEMA = default_schema().add_custom("Score", type=FieldType.WHOLE_NUMBER, required=True, needed_to_count=True, max_length=3)

# reason ID -> (RowInput, schema or None)
PROBLEM_ROWS = {
    "name_missing": (row_input(First_Name=""), None),
    "no_identifier": (row_input(Client_ID=""), None),
    "needed_field_failed": (row_input(Score="x"), COUNTING_SCHEMA),
    "address_part_missing": (row_input(Address_1=""), None),
    "zip_not_valid": (row_input(Zip="1120"), None),
    "zip_unicode_digits": (row_input(Zip="１１２０１"), None),
    "city_not_recognized": (row_input(City="Yonkers", Zip="10001"), None),
    "city_zip_disagree": (row_input(City="Queens", Zip="11201"), None),
    "state_not_recognized": (row_input(State="Narnia"), None),
    "state_zip_disagree": (row_input(State="NJ"), None),
    "address_incomplete": (row_input(State="", Zip=""), None),
    "address_text_disagrees": (row_input(address_text=AddressText(city="Queens")), None),
    "units_differ": (row_input(Address_1="123 Main St Apt 2A", Address_2="Apt 3B"), None),
    "address_extra_text": (row_input(Address_1="123 Main St Apt 2A", Address_2="c/o Jane Doe"), None),
    "placeholder_in_value": (row_input(Address_1="Unknown"), None),
    "name_may_be_placeholder": (row_input(First_Name="Na"), None),
    "digits_in_name": (row_input(First_Name="J0hn"), None),
    "unreadable_character": (row_input(Last_Name="Pe�a"), None),
    "date_not_readable": (row_input(Date_of_Birth="soon"), None),
    "date_impossible": (row_input(Date_of_Birth="02/31/1990"), None),
    "date_order_unclear": (row_input(Date_of_Birth="03/04/1990"), "unclear"),
    "date_both_ways": (row_input(Date_of_Birth="03/04/1990"), "both_ways"),
    "date_two_digit_year": (row_input(Date_of_Birth="1/2/80"), None),
    "date_excel_number": (row_input(Date_of_Birth="32874"), None),
    "dob_out_of_range": (row_input(Date_of_Birth="2030-01-01"), None),
    "dob_age_over_115": (row_input(Date_of_Birth="1900-01-01"), None),
    "value_wrong_type": (row_input(Score="x"), COUNTING_SCHEMA),
    "value_too_long": (row_input(Score="1234"), COUNTING_SCHEMA),
    "required_field_blank": (row_input(Score=""), default_schema().add_custom("Score", required=True)),
    "name_order_unclear": (row_input(step_reasons=[ReasonRef("name_order_unclear", "First_Name")]), None),
    "name_extra_tokens": (row_input(step_reasons=[ReasonRef("name_extra_tokens", "First_Name")]), None),
}
