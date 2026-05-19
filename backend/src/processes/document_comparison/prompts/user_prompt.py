impact_analysis_prompt = """
Version A
-----------------------
{first_version}
----------------------------
 
 
Version B
-----------------------------
{second_version}
---------------------------
"""

section_added_or_removed_prompt = '''
Here is the section and its content which is added or removed from version 1 to version 2 of a clinical trial protocol.

## {added_or_removed} ##

## Section ##
{section_name}
## Content ##
{content}
'''