# ElevenLabs за VPN (сервер в РФ, всё в Docker Compose)

Чтобы голос (STT/TTS) работал с сервера в России, трафик к ElevenLabs должен идти через VPN. Ниже — что сделать по шагам.

## 1. На хосте: VPN + HTTP-прокси

На **самом сервере** (не в контейнере) должно быть:

- **VPN** (WireGuard, OpenVPN и т.п.), чтобы исходящий трафик в интернет шёл через него.
- **HTTP-прокси**, который слушает на хосте и отправляет запросы через этот VPN.

Почему HTTP-прокси: бэкенд в Docker умеет только HTTP-прокси (`ELEVENLABS_HTTP_PROXY`). Если VPN даёт только SOCKS5 — на хосте поднимаем HTTP-прокси поверх SOCKS.

### Xray (VLESS/Reality): какой порт HTTP, какой SOCKS5

У вас xray слушает на **10808** и **10809**. Тип каждого порта задаётся в конфиге:

```bash
cat ~/vless-reality-vision.json | grep -E '"protocol"|"port"'
```

- **`"protocol": "http"`** — это HTTP-прокси, его можно использовать в `ELEVENLABS_HTTP_PROXY`.
- **`"protocol": "socks"`** — это SOCKS5; для бэкенда нужен HTTP-прокси поверх него (Privoxy, см. вариант B).

Часто в xray: один порт (например 10808) — SOCKS5, второй (10809) — HTTP. Посмотрите в `inbounds` в вашем JSON, у какого порта `"protocol": "http"`.

**Важно:** оба порта слушают на **127.0.0.1**. Из контейнера Docker до `127.0.0.1` хоста по такому адресу не достучаться. Нужно одно из двух:

1. **Переназначить inbound в xray на 0.0.0.0** (только для HTTP-порта, не для SOCKS, чтобы не светить SOCKS наружу): в конфиге у нужного inbound поменять `"listen": "127.0.0.1"` на `"listen": "0.0.0.0"`, перезапустить xray. Тогда в `.env` указать `ELEVENLABS_HTTP_PROXY=http://host.docker.internal:10809` (порт подставьте свой).
2. **Оставить 127.0.0.1 и поднять Privoxy** на 0.0.0.0:8118, в Privoxy указать `forward-socks5 / 127.0.0.1:10808 .` (или ваш SOCKS-порт). Тогда в `.env` указать `ELEVENLABS_HTTP_PROXY=http://host.docker.internal:8118`.

### Вариант A: VPN уже даёт HTTP-прокси

Если ваш VPN поднимает HTTP-прокси на хосте (например на порту 1080 или 8080):

- Запомните адрес и порт, например `127.0.0.1:1080`.
- Прокси должен слушать на **0.0.0.0** (или быть доступен по IP хоста из Docker). Иначе из контейнера до `127.0.0.1` хоста не достучаться. В `.env` используйте `http://host.docker.internal:ПОРТ`.

### Вариант B: VPN даёт только SOCKS5 (например 127.0.0.1:1080)

Поставьте на хост **Privoxy** — он сделает из SOCKS5 HTTP-прокси:

```bash
sudo apt update && sudo apt install -y privoxy
```

Настройте Privoxy использовать ваш SOCKS5 (порт **10808** — типичный для xray; если у вас другой — подставьте свой):

```bash
# 1) Слушать на всех интерфейсах, чтобы контейнер достучался
sudo sed -i 's/^listen-address.*/listen-address  0.0.0.0:8118/' /etc/privoxy/config

# 2) Добавить forward только если такой строки ещё нет (порт 10808 — SOCKS xray)
grep -q 'forward-socks5' /etc/privoxy/config || echo 'forward-socks5 / 127.0.0.1:10808 .' | sudo tee -a /etc/privoxy/config

# 3) Перезапуск и проверка
sudo systemctl restart privoxy
sudo systemctl status privoxy
```

Если `systemctl status privoxy` показывает ошибку — смотрите лог: `journalctl -xeu privoxy.service`. Частые причины: дубликат `listen-address`, неверный порт SOCKS (должен совпадать с портом в xray, например 10808), лишние строки в конфиге.

Проверка с хоста:

```bash
curl -x http://127.0.0.1:8118 -sI https://api.elevenlabs.io
```

Должен вернуться ответ от ElevenLabs (не 302 на help и не таймаут).

## 2. Доступ к прокси из Docker

Бэкенд крутится **в контейнере**. Для него «localhost» — это контейнер, а не хост. Поэтому в `.env` нельзя писать `http://127.0.0.1:8118` — контейнер до хоста так не достучится.

В `docker-compose.yml` у сервиса `backend` уже добавлено:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Поэтому из контейнера имя **`host.docker.internal`** указывает на хост. Прокси на хосте должен слушать на `0.0.0.0` (как в примере с Privoxy выше), тогда контейнер до него достучится.

## 3. Переменная в .env

В **корне проекта** (рядом с `docker-compose.yml`) в файле `.env` добавьте или измените:

```env
# Прокси на хосте (порт 8118 — пример для Privoxy)
ELEVENLABS_HTTP_PROXY=http://host.docker.internal:8118
```

Порт замените на тот, на котором у вас реально слушает HTTP-прокси (8118 для Privoxy, 1080/8080 и т.д. — как у вашего VPN/прокси).

Если по какой-то причине `host.docker.internal` не резолвится, подставьте IP шлюза Docker-сети на хосте, например:

```env
ELEVENLABS_HTTP_PROXY=http://172.17.0.1:8118
```

(на сервере можно посмотреть: `ip addr show docker0 | grep inet`).

## 4. Перезапуск бэкенда

```bash
cd /path/to/agiens-chat-hackaton   # или как у вас называется проект
docker compose up -d backend
```

Проверьте логи:

```bash
docker compose logs backend -f
```

Отправьте голосовое в чат — в логах не должно быть 302 от ElevenLabs и ошибок SSL.

## Краткий чеклист

| Шаг | Действие |
|-----|----------|
| 1 | На сервере: VPN включён, трафик в интернет идёт через VPN. |
| 2 | На сервере: HTTP-прокси (от VPN или Privoxy поверх SOCKS5), слушает на `0.0.0.0:ПОРТ`. |
| 3 | В `.env`: `ELEVENLABS_HTTP_PROXY=http://host.docker.internal:ПОРТ`. |
| 4 | `docker compose up -d backend`. |

После этого запросы к ElevenLabs из бэкенда идут через прокси на хосте → через VPN → в интернет.

Если в логах бэкенда появляется **503 Too many open connections** от прокси — в коде уже используется один общий HTTP-клиент для всех запросов к ElevenLabs; перезапустите backend (`docker compose up -d backend`) и при необходимости перезапустите Privoxy на хосте (`sudo systemctl restart privoxy`).

Если после запуска xray через прокси по-прежнему приходит **503 Too many open connections** — увеличьте лимит соединений Privoxy и перезапустите его:

```bash
# В конфиг Privoxy добавить (или увеличить): не более 256–512
grep -q '^max-client-connections' /etc/privoxy/config || echo 'max-client-connections 256' | sudo tee -a /etc/privoxy/config
# Если строка уже есть — вручную отредактировать: sudo nano /etc/privoxy/config
sudo systemctl restart privoxy
```

Затем снова проверить: `curl -x http://127.0.0.1:8118 -sI https://api.elevenlabs.io`

Если появляется **503 Forwarding failure** — Privoxy не может передать запрос в SOCKS (xray). Проверьте на хосте:
- **xray запущен:** `ps aux | grep xray`; при необходимости перезапустите: `nohup xray run -c ~/vless-reality-vision.json > ~/xray.log 2>&1 &`
- **Privoxy смотрит на правильный порт SOCKS** в `/etc/privoxy/config`: `forward-socks5 / 127.0.0.1:10808 .` (порт 10808 как в вашем xray)
- Перезапуск цепочки: `sudo systemctl restart privoxy`, затем `docker compose restart backend`
