import pytest
from triangle_class import Triangle, IncorrectTriangleSides

def test_equilateral():
    t = Triangle(3, 3, 3)
    assert t.triangle_type() == "equilateral"
    assert t.perimeter() == 9

def test_isosceles():
    t = Triangle(5, 5, 8)
    assert t.triangle_type() == "isosceles"

def test_invalid_sides():
    with pytest.raises(IncorrectTriangleSides):
        Triangle(1, 1, 3)