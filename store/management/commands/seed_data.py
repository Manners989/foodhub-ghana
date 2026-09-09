from decimal import Decimal

from django.core.management.base import BaseCommand

from store.models import Category, FoodItem


CATEGORIES = [
    {'name': 'Local Dishes', 'icon': 'bi-egg-fried', 'order': 1},
    {'name': 'Rice Dishes', 'icon': 'bi-basket', 'order': 2},
    {'name': 'Grills & BBQ', 'icon': 'bi-fire', 'order': 3},
    {'name': 'Soups & Swallow', 'icon': 'bi-cup-hot', 'order': 4},
    {'name': 'Fast Food', 'icon': 'bi-bag', 'order': 5},
    {'name': 'Drinks & Smoothies', 'icon': 'bi-cup-straw', 'order': 6},
    {'name': 'Desserts', 'icon': 'bi-ice-cream', 'order': 7},
    {'name': 'Breakfast', 'icon': 'bi-sunrise', 'order': 8},
]

FOOD_ITEMS = [
    ('Jollof Rice Special', 'Rice Dishes', 35.00, None,
     'Smoky party-style jollof rice cooked with fresh tomatoes, peppers, and aromatic spices, served with fried plantain.',
     True, False, 1, 20, 'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=600&q=80'),
    ('Waakye Combo', 'Local Dishes', 30.00, 25.00,
     'Traditional rice and beans served with gari, spaghetti, boiled egg, fish, and shito.',
     True, False, 1, 25, 'https://images.unsplash.com/photo-1596797038530-2c107229654b?w=600&q=80'),
    ('Banku with Grilled Tilapia', 'Soups & Swallow', 45.00, None,
     'Fermented corn and cassava dough served with a whole grilled tilapia and spicy pepper sauce.',
     True, False, 3, 30, 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80'),
    ('Fufu with Light Soup', 'Soups & Swallow', 40.00, None,
     'Smooth pounded cassava and plantain fufu served in a spicy goat meat light soup.',
     True, False, 2, 35, 'https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80'),
    ('Grilled Chicken Skewers', 'Grills & BBQ', 38.00, None,
     'Char-grilled marinated chicken skewers served with jollof rice and coleslaw.',
     True, False, 2, 25, 'https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=600&q=80'),
    ('Beef Suya', 'Grills & BBQ', 28.00, None,
     'Thinly sliced spicy skewered beef, grilled over open flame and coated in suya spice.',
     True, False, 3, 15, 'https://images.unsplash.com/photo-1529006557810-274b9b2fc783?w=600&q=80'),
    ('Classic Beef Burger', 'Fast Food', 32.00, None,
     'Juicy beef patty, cheddar cheese, lettuce, and tomato in a toasted brioche bun, served with fries.',
     True, False, 1, 18, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80'),
    ('Margherita Pizza', 'Fast Food', 55.00, 45.00,
     'Wood-fired pizza topped with fresh mozzarella, basil, and San Marzano tomato sauce.',
     True, True, 0, 20, 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&q=80'),
    ('Vegetable Fried Rice', 'Rice Dishes', 28.00, None,
     'Wok-fried rice tossed with fresh garden vegetables, soy sauce, and scrambled egg.',
     True, True, 0, 18, 'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80'),
    ('Fresh Watermelon Smoothie', 'Drinks & Smoothies', 15.00, None,
     'Refreshing chilled watermelon blended smooth with a hint of mint and lime.',
     False, True, 0, 8, 'https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=600&q=80'),
    ('Sobolo (Hibiscus Drink)', 'Drinks & Smoothies', 10.00, None,
     'Chilled hibiscus tea infused with ginger, pineapple, and a touch of spice.',
     False, True, 0, 5, 'https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=600&q=80'),
    ('Chocolate Lava Cake', 'Desserts', 22.00, None,
     'Warm chocolate cake with a molten centre, served with a scoop of vanilla ice cream.',
     False, True, 0, 15, 'https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=600&q=80'),
    ('Ice Cream Sundae', 'Desserts', 18.00, None,
     'A trio of ice cream scoops topped with chocolate syrup, nuts, and a cherry.',
     False, True, 0, 5, 'https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?w=600&q=80'),
    ('Egg & Sausage Breakfast Plate', 'Breakfast', 24.00, None,
     'Scrambled eggs, grilled sausage, baked beans, and toasted bread to start your day right.',
     True, False, 0, 15, 'https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=600&q=80'),
    ('Hausa Koko with Koose', 'Breakfast', 15.00, None,
     'Spiced millet porridge served with deep-fried bean cakes — a Northern Ghanaian classic.',
     False, False, 1, 15, 'https://images.unsplash.com/photo-1495214783159-3503fd1b572d?w=600&q=80'),
    ('Kelewele (Spiced Plantain)', 'Local Dishes', 18.00, None,
     'Deep-fried ripe plantain cubes seasoned with ginger, pepper, and warm spices, tossed with roasted peanuts.',
     False, True, 2, 15, 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80'),
]


class Command(BaseCommand):
    help = 'Seed the database with sample categories and food items for FoodHub Ghana'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Delete existing categories/items before seeding')

    def handle(self, *args, **options):
        if options['flush']:
            FoodItem.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing categories and food items.'))

        cat_map = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.get_or_create(name=cat_data['name'], defaults=cat_data)
            cat_map[cat_data['name']] = cat
            if created:
                self.stdout.write(f"  + Category: {cat.name}")

        created_count = 0
        for (name, cat_name, price, discount, desc, featured, veg, spice, prep, image_url) in FOOD_ITEMS:
            if FoodItem.objects.filter(name=name).exists():
                continue
            item = FoodItem(
                category=cat_map[cat_name],
                name=name,
                description=desc,
                price=Decimal(str(price)),
                discount_price=Decimal(str(discount)) if discount else None,
                is_available=True,
                is_featured=featured,
                is_vegetarian=veg,
                spice_level=spice,
                prep_time_minutes=prep,
                image_url=image_url,
            )
            item.save()
            created_count += 1
            self.stdout.write(f"  + Food item: {item.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeding complete: {len(cat_map)} categories, {created_count} new food items created."
        ))
        self.stdout.write(
            "Sample items use hotlinked Unsplash photos for demo purposes. "
            "To use your own photos, upload an image in the admin panel — it will "
            "automatically take priority over the demo photo."
        )
