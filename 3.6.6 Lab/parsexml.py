import xml.etree.ElementTree as ET
import re

xml = ET.parse("3.6.6 Lab/myfile.xml")
root = xml.getroot()

ns = re.match(r'{.*}', root.tag).group(0)
editconf = root.find(f"{ns}edit-config")
defop = editconf.find(f"{ns}default-operation")
testop = editconf.find(f"{ns}test-option")

print(f"The default-operation contains: {defop.text}")
print(f"The test-option contains: {testop.text}")
