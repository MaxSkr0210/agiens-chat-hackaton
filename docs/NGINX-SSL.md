# Nginx и HTTPS (Let's Encrypt) для agiens-hackathon.online

- **agiens-hackathon.online** → фронтенд (Next.js)
- **server.agiens-hackathon.online** → бэкенд (FastAPI)

Сертификаты: бесплатный SSL от Let's Encrypt (certbot).

## Ошибка «pull rate limit» Docker Hub

Если при `docker compose up -d` появляется *You have reached your unauthenticated pull rate limit*:

1. Зарегистрируйтесь на [Docker Hub](https://hub.docker.com) (бесплатно).
2. На сервере выполните: `docker login` и введите логин/пароль.
3. Повторите: `docker compose up -d`.

После входа лимит выше (200 образов за 6 часов для бесплатного аккаунта).

## Требования

- Домен agiens-hackathon.online и поддомен server.agiens-hackathon.online должны указывать на IP сервера (A-записи).
- Порты 80 и 443 открыты на сервере.

## Первый запуск (получение сертификатов)

1. **Временно переключите nginx на HTTP-only конфиг** (без SSL), чтобы nginx запустился и certbot мог пройти проверку по HTTP:

   ```bash
   cp nginx/nginx-http-bootstrap.conf nginx/nginx.conf
   ```

2. **Запустите все сервисы**, включая nginx:

   ```bash
   docker compose up -d
   ```

3. **Получите сертификаты** (замените `your@email.com` на свой email):

   ```bash
   docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
     -d agiens-hackathon.online -d server.agiens-hackathon.online \
     --email your@email.com --agree-tos --no-eff-email
   ```

4. **Верните основной конфиг с SSL** и перезапустите nginx:

   ```bash
   git checkout nginx/nginx.conf
   # или вручную восстановите nginx.conf с блоками HTTPS
   docker compose restart nginx
   ```

После этого:
- https://agiens-hackathon.online — фронтенд
- https://server.agiens-hackathon.online — API бэкенда

## Продление сертификатов

Let's Encrypt выдаёт сертификаты на 90 дней. Продлевать можно вручную или по cron.

**Вручную:**

```bash
docker compose run --rm certbot renew
docker compose exec nginx nginx -s reload
```

**По cron** (раз в день проверка и продление при необходимости):

```bash
0 3 * * * cd /path/to/agiens && docker compose run --rm certbot renew --quiet && docker compose exec nginx nginx -s reload
```

## CORS и переменные окружения

Если фронтенд обращается к API по домену (например, `NEXT_PUBLIC_API_URL=https://server.agiens-hackathon.online`), добавьте в `.env` для бэкенда:

```env
CORS_ORIGINS=https://agiens-hackathon.online,https://www.agiens-hackathon.online
```

Если фронт и API на одном домене (запросы через Next.js proxy на тот же origin), CORS для этого домена не обязателен.

## Локальная разработка без nginx

Для локальной разработки nginx можно не поднимать: фронт на `http://localhost:3000`, бэкенд на `http://localhost:3001`. Запуск:

```bash
docker compose up -d postgres redis backend frontend
```

Чтобы поднять ещё и nginx (если домены указывают на localhost или для теста):

```bash
docker compose up -d
```
