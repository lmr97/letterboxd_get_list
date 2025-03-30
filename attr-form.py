# This script transforms the list of valid attributes
# into HTML, formatted like I need for the webpage.

VALID_ATTRS  = []
with open("./valid-lb-attrs.txt", "r") as attr_file:
    VALID_ATTRS = attr_file.readlines()
VALID_ATTRS = [a.replace("\n", "") for a in VALID_ATTRS]

html_list = [
    "\n  </label>\n  <label>\n    <input type=\"checkbox\" id=\""+ a +"\"/>"+a.replace("-", " ") 
    for a in VALID_ATTRS
    ]
html_list = "".join(html_list)
html_list = html_list + "\n  </label>"

print(html_list)

# VALID_ATTRS = [a.replace("_", "-") for a in VALID_ATTRS]
# with open("./valid-lb-attrs-dash.txt", "w") as attr_file:
#     attr_file.readall #.write("\n".join(VALID_ATTRS_dash))