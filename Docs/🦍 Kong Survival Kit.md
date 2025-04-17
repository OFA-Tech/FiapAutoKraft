## 📦 O que é o Kong?

Kong é um **API Gateway open source** que atua como **proxy reverso inteligente**:

- Centraliza o tráfego de APIs
- Autentica, rate-limita e roteia requests
- Registra logs e monitora
- Escala facilmente com Docker/Kubernetes
- Suporta **plugins poderosos**

---

## 🚀 Instalação rápida com Docker

```yaml
version: '3.8'
services:
  kong-database:
    image: postgres:13
    environment:
      POSTGRES_USER: kong
      POSTGRES_DB: kong
      POSTGRES_PASSWORD: kong
    volumes:
      - kong_data:/var/lib/postgresql/data

  kong:
    image: kong/kong-gateway:3.6.0.0-alpine
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-database
      KONG_PG_PASSWORD: kong
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
    ports:
      - "8000:8000"   # Gateway público
      - "8001:8001"   # Admin API
    depends_on:
      - kong-database

  konga:
    image: pantsel/konga
    environment:
      DB_ADAPTER: postgres
      DB_HOST: kong-database
      DB_USER: kong
      DB_PASSWORD: kong
      DB_DATABASE: kong
    ports:
      - "1337:1337"

volumes:
  kong_data:
```

> `Konga` é o painel web para administrar suas rotas/plugins visualmente.

---

## 🌐 Como funciona

```
[Client] → [Kong Gateway] → [Sua API]
                      ↘ Plugins (rate-limit, auth, etc)
```

---

## 🔧 Criando uma rota via Admin API

```bash
# Registra um serviço
curl -i -X POST http://localhost:8001/services \
  --data name=api-produtos \
  --data url=http://api-produtos:5000

# Cria uma rota pública
curl -i -X POST http://localhost:8001/services/api-produtos/routes \
  --data paths[]=/produtos
```

Agora o acesso externo seria:

```
GET http://localhost:8000/produtos
```

---

## 🧩 Plugins úteis (top para o seu projeto)

| Plugin           | Função                                  |
|------------------|------------------------------------------|
| `rate-limiting`  | Evita overload (ex: 10 req/s por IP)     |
| `key-auth`       | Protege APIs com chave de acesso         |
| `jwt`            | Valida tokens JWT                        |
| `cors`           | Libera cross-domain (ex: pra frontend)  |
| `request-transformer` | Adiciona/remover headers            |
| `acl`            | Cria controle de grupos de acesso       |
| `loggly/syslog`  | Logging centralizado                     |

---

## 🧪 Teste básico com `httpie` ou `curl`

```bash
http POST :8001/services name=api-teste url=http://localhost:5000
http POST :8001/services/api-teste/routes paths:='["/teste"]'
```

---

## 👀 Painel visual com Konga

Acesse:  
**http://localhost:1337**

- Interface para ver logs, serviços, rotas
- Ativar/desativar plugins
- Testar chamadas

---

## 🔐 Com DDD e RESTful?

Use o Kong pra centralizar todos os seus _bounded contexts_ (serviços):

```
/produtos → api-produto
/inventario → api-inventario
/robos → api-robo
```

E coloque:

- **Rate limit** por cliente
- **JWT** com claims baseadas em papéis
- **CORS e Headers padrão** automáticos

---

## 🧠 Dicas para seu projeto robótico

| Componente       | Rota                        |
|------------------|-----------------------------|
| Inventário       | `/api/inventario`           |
| Robô AMR         | `/api/robo/movimentar`      |
| Visão computacional | `/api/visao/processar`  |
| Log de tarefas   | `/api/logs`                 |

**Com o Kong**:  
Todas essas rotas podem ser expostas por um único endpoint externo via proxy e protegidas com plugins inteligentes.