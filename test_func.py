import unittest
from triangle_func import get_triangle_type, IncorrectTriangleSides

class TestTriangleFunction(unittest.TestCase):
    def test_equilateral(self):
        self.assertEqual(get_triangle_type(3, 3, 3), "equilateral")
    
    def test_isosceles(self):
        self.assertEqual(get_triangle_type(5, 5, 8), "isosceles")
    
    def test_nonequilateral(self):
        self.assertEqual(get_triangle_type(6, 7, 8), "nonequilateral")
    
    def test_invalid_sides(self):
        with self.assertRaises(IncorrectTriangleSides):
            get_triangle_type(0, 1, 1)

if __name__ == '__main__':
    unittest.main()