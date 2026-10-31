# Address data for Wholecount

This page is for the operator and for IT. Wholecount places addresses on the map and in districts in one of two ways: with Geosupport Desktop Edition, or with an address reference file you add. Without either, every row is still checked and counted, and every location reads "Counted, not mapped: no geocoder."

The session that wrote this page couldn't reach the NYC Planning or NYC Open Data sites. Every statement about those sites is marked **Unconfirmed**, and no web addresses are given until someone has read the pages.

## Geosupport Desktop Edition

- **What it is.** Geosupport is New York City's own address lookup. It turns a house number and street into a building's location, its ZIP and its districts. The desktop edition runs on one Windows computer with no network. It's published by NYC Planning (the Department of City Planning). **Unconfirmed:** the download page's current name and wording.
- **Getting it.** Download it from NYC Planning's Geosupport Desktop Edition page and run its installer. Your organization installs it, not Wholecount. **Unconfirmed:** the page address, the Windows versions it supports and how often releases come out.
- **How Wholecount finds it.** It looks in this order:
  1. the folder above the one the `GEOFILES` environment variable points at (Geosupport's installer sets `GEOFILES` to its data folder)
  2. `C:\Program Files\Geosupport Desktop Edition`
  3. `C:\Program Files (x86)\Geosupport Desktop Edition`

  `GEOFILES` set to an empty value turns Geosupport off for Wholecount. Wholecount then looks up one known address. If that lookup fails, it doesn't use Geosupport.
- **The release.** Wholecount reads the release, such as 25C, from the install folder's name. The top bar shows "Geosupport Desktop Edition 25C on this computer", and the audit log records the release with every run. When the folder name has no release in it, the release reads "unknown". A release more than a year old gets a note that district lines may have changed.
- **The installer's Geosupport page.** When Wholecount's installer can't find Geosupport, it shows one page that says so. Wholecount still installs and runs, and you can add Geosupport or a reference file later.

## An address reference file

Without Geosupport, Wholecount places an address only when it matches a row of a reference file exactly. None is bundled, because Wholecount ships no address data of its own.

- **Which file.** NYC Open Data publishes a dataset of address points for every building address in the city, from NYC Planning. **Unconfirmed:** the dataset's exact title, its page address and its column names.
- **The columns Wholecount reads.** Header names are matched without regard to case. The file needs a house number, a street, a latitude, a longitude, and a ZIP or a borough.

  | Wholecount needs | Header names it accepts |
  | --- | --- |
  | House number | `house_number`, `hnum`, `housenum` |
  | Street | `street`, `street_name`, `stname` |
  | ZIP | `zip`, `zipcode` |
  | Borough | `borough`, `boro` |
  | Latitude | `latitude` |
  | Longitude | `longitude` |

- **When the download uses other names.** Open the file in Excel, click each header cell that holds one of these facts, type the name from the table, and save it as CSV UTF-8 (comma delimited). Don't change any other cell. Plain CSV can turn accented letters into ones Wholecount can't read, and then the whole file is refused. If the download has no latitude and longitude columns, it can't be used as it is. **Unconfirmed:** whether the address points download has latitude and longitude columns or holds the location only as a map shape.
- **Exact matches only.** The match uses the house number, the street with its type and direction spelled out, and the ZIP or borough. Near matches are shown in Fix problems as suggestions for a person, and they never get coordinates or districts on their own.

## Where the file goes

- Wholecount reads the one `.csv` file in `%LOCALAPPDATA%\Wholecount\reference\`.
- You make that folder yourself. Wholecount writes nothing to disk until you ask it to.
- Put exactly one file there. With two or more, none is used, and the system check in the ledger footer reads "two files in the folder, none used".
- When the file is read, the system check shows its name and its number of rows. A file that can't be read shows "the file could not be read".
- The small sample file in Wholecount's example data is refused for your own files, even when you copy it into this folder. The system check then reads "sample file, practice only". It's used only for "Try example data", and everything from that run is marked PRACTICE.

## Data that ships with Wholecount

- **The NYC ZIP table.** `wholecount/engine/geo/data/nyc_zips.csv` lists every NYC ZIP with its borough, and each row names its source and the date it was read. The current source is the NYC Health ZIP table, read on 2026-10-31. `tools/make_zip_table.py` rebuilds it from the files in `tools/data/`, and `--check` reports any difference.
- **District files.** `tools/make_district_files.py` builds State Senate, State Assembly and City Council district files from NYC Planning's boundary downloads, saved by hand into `tools/data/districts/`. Those downloads haven't been saved yet, so no district files ship now. A row placed by the reference file then gets no districts, and the pre-run text says so. A row placed by Geosupport takes its districts from Geosupport.
