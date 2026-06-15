import re

texts = [
    "Outstanding Principal $298,492.41",
    "Outstanding Principal$298,492.41",
    "Outstanding Principal 298,492.41",
    "Outstanding Principal \n $298,492.41",
    "Outstanding Principal\n$298,492.41"
]

regex = r"outstanding\s+(?:balance|principal).*?(?P<amt>(?<=\$)\s*[0-9,]+(?:\.\d{2})?|[0-9]{1,3}(?:,[0-9]{3})+(?:\.\d{2})?|[0-9]+\.\d{2}(?!\d|\s*%))"

for t in texts:
    match = re.search(regex, t, re.IGNORECASE | re.DOTALL)
    if match:
        print(f"Match: {match.group('amt')} for {repr(t)}")
    else:
        print(f"No match for {repr(t)}")
