"""LLM prompt templates for schema detection."""

# System prompt for schema detection
SCHEMA_DETECTOR_SYSTEM = """You are an expert data analyst that examines web page content and identifies structured data patterns.

Your job is to:
1. Analyze HTML/text content from a web page
2. Identify repeating data patterns (products, posts, listings, etc.)
3. Generate a JSON schema for each detected data collection
4. Suggest REST API endpoint names

You MUST respond with valid JSON only. No explanations outside JSON."""


# Auto-detect mode: AI finds all data patterns
AUTO_DETECT_PROMPT = """Analyze this web page content and identify ALL structured data collections.

**Page Title:** {title}
**URL:** {url}
**Data Hints:** {hints}

**Page Content:**
{content}

For each data collection found, provide:
- A descriptive name (snake_case, plural) for the API endpoint
- A description of what the data represents
- The JSON schema with field names, types, and examples
- How many items were found

Respond with this exact JSON structure:
{{
  "endpoints": [
    {{
      "name": "endpoint_name",
      "description": "What this data represents",
      "method": "GET",
      "item_count": 10,
      "schema": {{
        "type": "object",
        "properties": {{
          "field_name": {{
            "type": "string|number|boolean|array",
            "description": "What this field contains",
            "example": "example value"
          }}
        }}
      }},
      "sample_data": [
        {{"field_name": "actual value from page"}}
      ]
    }}
  ],
  "site_description": "Brief description of the website"
}}

Rules:
- Only include data that has 2+ items (repeating patterns)
- Use clean, descriptive field names (not CSS class names)
- Include 2-3 sample_data items from the actual page content
- Endpoint names should be RESTful (plural nouns, snake_case)
- Detect nested data where appropriate (e.g., comments with replies)"""


# Guided mode: User specifies what to extract
GUIDED_EXTRACT_PROMPT = """Extract the following data from this web page:

**User Request:** {user_query}
**Page Title:** {title}
**URL:** {url}

**Page Content:**
{content}

Based on the user's request, create an API endpoint that serves this data.

Respond with this exact JSON structure:
{{
  "endpoints": [
    {{
      "name": "endpoint_name",
      "description": "What this data represents",
      "method": "GET",
      "item_count": 0,
      "schema": {{
        "type": "object",
        "properties": {{
          "field_name": {{
            "type": "string|number|boolean|array",
            "description": "What this field contains",
            "example": "example value"
          }}
        }}
      }},
      "sample_data": [
        {{"field_name": "actual value from page"}}
      ]
    }}
  ],
  "site_description": "Brief description of the website"
}}

Rules:
- Focus on what the user requested, but include related useful fields
- Use clean, descriptive field names
- Include 2-3 actual sample_data items from the page
- If the user's request is vague, be comprehensive"""
