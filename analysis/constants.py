REP_START_FRACTION = 0.10   # movement "start" = this fraction into the segment's own ROM
REP_END_FRACTION = 0.90     # movement "end"   = this fraction into the segment's own ROM
MIN_ROM_M = 0.05            # minimum excursion to count as a real turnaround (noise rejection)
DISPLAY_REP_COUNT = 15

# Refractory period after a confirmed turnaround. Reversals detected
# within this window of the previous turnaround are treated as sensor
# jitter or mechanical settling/bounce at the top or bottom of a rep,
# not a genuine direction change. Real concentric/eccentric phases run
# well over this even for very fast/explosive reps -- tune down only if
# you find it's suppressing genuinely fast turnarounds.
MIN_TURNAROUND_INTERVAL_S = 0.20