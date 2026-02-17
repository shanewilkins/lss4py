from lss4py import adapters, analytics, domain, observability, reporting, workflows
from lss4py.errors import LSS4PyError


def test_layer_modules_are_importable() -> None:
    assert adapters is not None
    assert analytics is not None
    assert domain is not None
    assert observability is not None
    assert reporting is not None
    assert workflows is not None


def test_error_base_type() -> None:
    assert issubclass(LSS4PyError, Exception)
