
vendor_search = """
Vendor Name: {vendor_name}
Vendor Category: {vendor_category}
Question Category: {question_category}
Question: {query}
Answer: {answer}

Search Results:
{search_context}
"""

capability_user_prompt = """Extract vendor capabilities for {vendor_name} based on the following JSON data: {input_data}"""

positive_news_user_prompt = """Extract vendor Postive news for {vendor_name} in {start} and {end} based on the following JSON data: {input_data}"""

negative_news_user_prompt = """Extract vendor negative news for {vendor_name} in {start} and {end} based on the following JSON data: {input_data}"""
