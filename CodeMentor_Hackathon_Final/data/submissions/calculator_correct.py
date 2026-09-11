def calculate(a, b, operation):
    """Apply a supported arithmetic operation to two numbers."""
    if operation == "+":
        return a + b
    if operation == "-":
        return a - b
    if operation == "*":
        return a * b
    if operation == "/":
        if b == 0:
            raise ValueError("Division by zero is not allowed")
        return a / b
    raise ValueError(f"Unsupported operation: {operation}")
