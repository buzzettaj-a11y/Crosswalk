#!/usr/bin/env bash
# usage: a02_grep_canaries.sh file...   prints canary hits per file
CAN='Zebulon|Quillfeather|Marigold|Thistlewood|Ignatius|Wobblesworth|Philomena|Dingleberry|Barnaby|Fiddlesticks|Octavia|Pemberton|Leopold|Snodgrass|Wilhelmina|Grumblethorpe|Cornelius|Bumblefoot|Evergreen|Pomegranate|Kumquat|Zucchini|Rhubarb|Turnip|Parsnip|Radish|Beetroot|1961-03-14|ZORP|Brookln|Gotham'
for f in "$@"; do
  n=$(grep -ciE "$CAN" "$f")
  echo "== $f : $n line(s) with canary client values"
  grep -oiE "$CAN" "$f" | sort | uniq -c | sort -rn | head -8
done
