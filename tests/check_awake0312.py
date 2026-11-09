"""Native X11 regression, executed under an isolated Xvfb server."""
import json
from astroall.awake import display_state
one=display_state(True)
two=display_state(True)
assert one['screen_kept_on'] and two['screen_kept_on'],(one,two)
print(json.dumps(two))
