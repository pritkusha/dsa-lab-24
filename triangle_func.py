class IncorrectTriangleSides(Exception):
    pass

def get_triangle_type(a: int, b: int, c: int) -> str:
    if a <= 0 or b <= 0 or c <= 0 or a + b <= c or a + c <= b or b + c <= a:
        raise IncorrectTriangleSides("Некорректные длины сторон треугольника")
    if a == b == c:
        return "equilateral"
    elif a == b or a == c or b == c:
        return "isosceles"
    else:
        return "nonequilateral"
    