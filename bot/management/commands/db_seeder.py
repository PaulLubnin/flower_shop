from django.core.management.base import BaseCommand
from bot.models import Florist, Flower
import random
import glob

class Command(BaseCommand):    
    def handle(self, *args, **options):
        db_seeder_florist()
        db_seeder_flower()

def db_seeder_florist():
    florist = Florist.objects.create(
        full_name = 'Алла Пугачева',
        chat_id = '1234493213'
    )

def db_seeder_flower():
    images = glob.glob("./media/*")
    flower_prices = [1000, 1250, 1500, 2000, 3500, 5500, 7500, 11000]
    flower_types = ['Розы', 'Гвоздики', 'Хризантема', 'Пионы', 'Альстромерии', 'Астра', 'Азалия', 'Лютик']
    flower_categories = ['День рождение', '8 марта', 'Свадьба', 'Рождение']
    for image_number, image_path in enumerate(images):
        flower = Flower.objects.create(
            title = f'Букет #{image_number}',
            description = f'Описание букета #{image_number}',
            type = random.choice(flower_types),
            category = random.choice(flower_categories),
            image = image_path,
            florist_id = 1,
            price = random.choice(flower_prices)
        )