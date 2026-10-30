# Cheat sheet: Matching columns

_One page. Built from `ui/help.json` by `tools/make_docs.py`._

## Match your columns
- **For:** The tool has to know which of your columns holds the first name, which the street, and so on. It guesses, and it checks its guess against the values in each column, because a column in the wrong place processes without complaint and produces confidently wrong results.
- **Do:** Look at each table. A warning under a field means the values do not look like that field, and it names the column that does. City and State can be left empty; the ZIP fills them. If a file leaves out a field entirely and every row shares one value, such as the program, set it under Fill a field for this source only.

## Does this column hold what the field expects?
- **For:** A column matched to the wrong field is the mistake with the worst consequence: it processes without complaint and produces confidently wrong results, such as apartment numbers as streets.
- **Do:** The tool reads a sample of each matched column and warns when the values do not look like the field, naming the column that does. It never blocks you, since you may have a reason.

## Which row holds the column names
- **For:** Files often begin with a title or a note above the real header. Read that way, the column names would be nonsense and every field would be missing.
- **Do:** Tick the row that holds the column names; rows above it are dropped. The tool flags a choice that looks wrong: a mostly empty row, a row of numbers, or no header chosen when one of the first rows plainly holds the names.

## Fill a field for this source only
- **For:** One file may leave a field out entirely, such as the program, while every row in it shares the same value. Typing it once here gives it to every row of that file.
- **Do:** Set it here and it fills only blanks, never replacing a value the file supplied. It applies to this table alone and is recorded in the audit log on every row it touched.
