"""Birth Rate is pulled in pep.py, not here.

CDC WONDER's own API documentation states plainly: "In keeping with the vital
statistics policy for public data sharing, only national data are available for
query by the API. Queries for mortality and births statistics from the National
Vital Statistics System cannot limit or group results by any location field" —
county-level natality is simply not obtainable through CDC WONDER's programmatic
API, by policy, regardless of how the XML query is built. The web UI can show
county data to a human (with small counts suppressed), but that's not scriptable
without browser automation against a tool that's explicitly trying to prevent
exactly that kind of access.

The Census Population Estimates Program's county components-of-change file (see
mmi.sources.pep) already includes full-coverage, unsuppressed county birth counts
and a crude birth rate — sourced from the same underlying NCHS vital statistics —
so it's used there instead. This module is kept only so a future source swap has
a place to land if a better birth-specific source turns up.
"""
