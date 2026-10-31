District boundary files for point-in-polygon (SPEC 6.6 P-GEO-5).

This folder is empty in the repository. tools/make_district_files.py builds three GeoJSON files here from the official NYC
Planning boundaries: State Senate, State Assembly and City Council districts. Each file records its source and the date it
was made.

The tool never downloads anything. It reads the three boundary files saved by hand into tools/data/districts/, named as
its SOURCES list says. The cloud session that wrote M05 could not reach the NYC Planning or NYC Open Data sites, so the
files were not saved and nothing here was built.

With no files here, a row placed by the reference file gets no districts, and the pre-run text says so. A row placed by
Geosupport takes its districts from Geosupport and never from these files.
