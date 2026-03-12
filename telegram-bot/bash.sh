# Создайте файл .env с переменными
echo "BOT_TOKEN=8656415921:AAEHMziFqvWQVHPzmbkggbo5lIIxwvH772M" > .env
echo "ADMIN_IDS=123456789" >> .env

# Запустите контейнеры
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot

# Остановка
docker-compose down