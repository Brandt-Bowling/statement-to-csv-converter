import re

text = """Account Information\n\nOutstanding Principal\nInterest Rate\n\n$298,492.41\n3.3750%\n\nnm —_—_= -\n"""

regex = r"outstanding\s+(?:balance|principal).*?(?P<amt>(?<=\$)\s*[0-9,]+(?:\.\d{2})?|[0-9]{1,3}(?:,[0-9]{3})+(?:\.\d{2})?|[0-9]+\.\d{2}(?!\d|\s*%))"
match = re.search(regex, text, re.IGNORECASE | re.DOTALL)
if match:
    print(f"Match: {match.group('amt')}")
else:
    print("No match")
