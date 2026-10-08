import unittest
from scrape import parse_menu_html, make_markdown, make_html

SAMPLE = """<html><h1>Menu for Thursday, October 8, 2026</h1><div id="mdining-items">
<h3><a>Breakfast</a></h3><div class="course-hijax"><ul class="courses_wrapper"><li><h4>Toast</h4><ul class="items">
<li class="allergen-egg"><span class="item-name">Scrambled Eggs</span></li>
<div class="nutrition"><table class="nutrition-facts"><tr class="serving-size"><td>Serving Size 1 cup</td></tr><tr class="portion-calories"><td>Calories 180</td></tr><tr><td>Protein 12g</td><td>24%</td></tr></table></div>
</ul></li></ul></div>
<h3><a>Lunch</a></h3><div class="course-hijax"><ul class="courses_wrapper"><li><h4>Wildfire</h4><ul class="items"><li><span class="item-name">Grilled Chicken</span></li></ul></li></ul></div>
<h3><a>Dinner</a></h3><div class="course-hijax"><ul class="courses_wrapper"><li><h4>Smoke</h4><ul class="items"><li><span class="item-name">Roast Beef</span></li></ul></li></ul></div>
</div></html>"""

class MenuTests(unittest.TestCase):
    def test_three_meals(self):
        result = parse_menu_html(SAMPLE, "2026-10-08")
        self.assertEqual(list(result["meals"]), ["Breakfast", "Lunch", "Dinner"])
        self.assertEqual(result["meals"]["Breakfast"][0]["name"], "Scrambled Eggs")
        self.assertEqual(result["meals"]["Breakfast"][0]["allergens"], ["egg"])
        self.assertIn("Grilled Chicken", make_markdown(result))
        self.assertIn("Roast Beef", make_html(result))
    def test_wrong_date(self):
        with self.assertRaisesRegex(ValueError, "Wrong menu date"):
            parse_menu_html(SAMPLE, "2026-10-09")
    def test_blocked_page(self):
        with self.assertRaises(ValueError):
            parse_menu_html("<html>Cloudflare</html>", "2026-10-08")
    def test_empty_menu(self):
        with self.assertRaises(ValueError):
            parse_menu_html("<h1>Menu for Thursday, October 8, 2026</h1><div id='mdining-items'></div>", "2026-10-08")

if __name__ == "__main__":
    unittest.main()
