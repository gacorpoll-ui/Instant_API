from jinja2 import Environment

def render_template(template_string: str, **kwargs) -> str:
    """
    Renders a Jinja2 template string with the provided keyword arguments.

    Args:
        template_string (str): The Jinja2 template as a string.
        **kwargs: Keyword arguments to be passed to the template.

    Returns:
        str: The rendered template as a string.

    Raises:
        ValueError: If the template string is empty or if any required key in kwargs is missing.
    """
    if not template_string.strip():
        raise ValueError("Template string cannot be empty.")
    
    # Validate that all required keys are present in kwargs
    # This example assumes 'name' and 'age' are required keys
    required_keys = {'name', 'age'}
    missing_keys = required_keys - kwargs.keys()
    if missing_keys:
        raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")

    env = Environment()
    template = env.from_string(template_string)
    return template.render(**kwargs)

# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)

    try:
        result = render_template("Hello, {{ name }}! You are {{ age }} years old.", name="Alice", age=30)
        print(result)
    except Exception as e:
        logging.error(f"An error occurred: {e}")