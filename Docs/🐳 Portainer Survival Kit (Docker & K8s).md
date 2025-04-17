## ✅ O que é o Portainer?

Portainer é uma **UI web** pra gerenciar:
- Containers
- Stacks (docker-compose)
- Volumes, networks, imagens
- Usuários, roles e acessos
- Clusters Kubernetes (se quiser escalar)

Funciona com:
- Docker local ou remoto
- Docker Swarm
- Kubernetes

---

## 🚀 Instalação Rápida (Docker Standalone)

```bash
docker volume create portainer_data

docker run -d -p 9000:9000 -p 9443:9443 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

> Acesse:  
> http://localhost:9000 (primeiro acesso = criar senha)

---

## 🌐 Portainer via Docker Compose

```yaml
version: "3"
services:
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    ports:
      - "9000:9000"
      - "9443:9443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
      - "portainer_data:/data"
    restart: always

volumes:
  portainer_data:
```

---

## 👨‍💻 Recursos úteis na interface

| Recurso         | Uso |
|------------------|-----|
| **Containers**     | Iniciar, parar, recriar, logs, exec shell |
| **Stacks**         | Deploy via docker-compose direto na web |
| **Volumes**        | Criar, deletar, inspecionar |
| **Images**         | Pull de imagem direto |
| **Network**        | Criar redes customizadas (bridge, etc) |
| **Users/Roles**    | Gerenciar time com permissões |
| **Registries**     | Conectar ao Docker Hub, GitLab, etc |
| **Templates**      | Apps prontos com 1 clique |

---

## 🛡 Segurança

- HTTPS com auto-cert incluso (porta 9443)
- Pode configurar autenticação externa (LDAP, etc)
- Pode esconder terminal (CLI) por nível de usuário
- RBAC (controle de acesso por time/usuário)

---

## 🔄 Atualização

```bash
docker pull portainer/portainer-ce:latest
docker stop portainer && docker rm portainer
# Execute novamente o container com os mesmos volumes
```

---

## 🔗 Integração com projetos

Você pode:

- Subir sua aplicação (API REST, IA, OpenCV, etc) via compose
- Gerenciar seu MongoDB, Redis, Postgres, RabbitMQ, etc visualmente
- Acompanhar consumo de CPU/memória dos serviços da sua stack
- Ver os logs da aplicação direto na UI
- Integrar com webhook ou scripts de deploy automático

---

## 🧠 Dica pro seu projeto

Crie um `docker-compose.yml` com:
- Sua API REST com Hangfire
- MongoDB ou PostgreSQL
- Serviço de IA (YOLO, TensorFlow)
- Portainer pra monitorar tudo 🔥