import click


class ConsoleError(click.ClickException):
    """Raised when an error occurs and script exectuion should halt."""

    pass
