from jinja2 import Environment  # ← cukup ini saja
import logging

# Setup basic configuration for logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def render_template(template_string: str, **kwargs) -> str:
    """
    Renders a Jinja2 template string with the provided context.

    Args:
        template_string (str): The Jinja2 template as a string.
        kwargs: Additional keyword arguments to pass to the template.

    Returns:
        str: The rendered template string.

    Raises:
        ValueError: If the template rendering fails.
    """
    try:
        # Create a Jinja2 environment with the provided template string
        env = Environment()
        template = env.from_string(template_string)
        
        # Render the template with the provided context
        return template.render(**kwargs)
    
    except Exception as e:
        logger.error(f"Failed to render template: {e}")
        raise ValueError("Template rendering failed") from e

# Example usage
if __name__ == "__main__":
    template = "Hello, {{ name }}!"
    try:
        result = render_template(template, name="World")
        print(result)
    except ValueError as e:
        print(e)