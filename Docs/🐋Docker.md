**Este survival kit reúne os conceitos essenciais, comandos, boas práticas e dicas de segurança para começar a usar Docker de maneira eficiente e segura.**

---

## **1. Conceitos Fundamentais**

- **Imagem:** Blueprint imutável que contém o app, dependências e instruções para rodar o container[2][6].
- **Container:** Instância em execução de uma imagem, isolada do sistema host[2][6].
- **Dockerfile:** Arquivo de instruções para construir imagens personalizadas.
- **Docker Engine:** Serviço que executa e gerencia containers no host[2].
- **Docker Hub:** Repositório público/privado para compartilhar imagens[2].

---

## **2. Comandos Essenciais**

```bash
# Verificar versão do Docker
docker --version
```

```bash
# Listar containers em execução
docker ps
```

```bash
# Listar todos os containers (inclusive parados)
docker ps -a
```

```bash
# Rodar um container
docker run -d --name meu_container nginx:latest
```

```bash
# Parar um container
docker stop meu_container
```

```bash
# Remover um container
docker rm meu_container
```

```bash
# Listar imagens disponíveis
docker images
```

```bash
# Remover uma imagem
docker rmi nginx:latest
```

```bash
# Construir imagem a partir de um Dockerfile
docker build -t minha_imagem:1.0 .
```

```bash
# Executar comando em container rodando
docker exec -it meu_container bash
```

---

## **3. Boas Práticas de Imagem**

- Use imagens oficiais e minimalistas (ex: `alpine`, `python:3.9-slim`)[4][6].
- Utilize multi-stage builds para reduzir o tamanho da imagem[3][6].
- Remova dependências e arquivos desnecessários após a instalação[4][6].
- Sempre use tags versionadas (ex: `meu-app:1.0.0`), evitando `latest`[6].
- Nunca armazene segredos (senhas, tokens) no Dockerfile[7].

---

## **4. Segurança Essencial**

- **Mantenha Docker e o SO atualizados** para evitar vulnerabilidades[1][2][7].
- **Nunca rode containers como root**; especifique um usuário não privilegiado no Dockerfile[7].
- **Use profiles de segurança** como seccomp, AppArmor ou SELinux[5][7].
- **Limite recursos** (CPU, memória, processos) com flags como `--memory`, `--cpus`, `--ulimit`[1][4][5].
- **Monte volumes e sistemas de arquivos como read-only** quando possível (`--read-only`, `-v ...:ro`)[4][5].
- **Evite containers privilegiados** e minimize permissões[7].
- **Ative o Docker Content Trust** para garantir imagens assinadas[2].
- **Faça scan de vulnerabilidades** nas imagens (ex: Trivy, Clair, `docker scan`)[6][7].

---

## **5. Redes e Comunicação**

- **Use redes privadas do Docker** para isolar serviços sensíveis[2][4].
- **Aplique segmentação de redes** (ex: separar front-end e banco de dados)[2].
- **Configure firewall e TLS** para proteger comunicação entre host e containers[2].
- **Evite expor portas desnecessárias** e use apenas as requeridas[7].

---

## **6. Monitoramento e Logs**

- **Centralize logs** usando drivers de log ou ferramentas externas (ELK, Splunk, CloudWatch)[4].
- **Monitore containers** com Prometheus, Grafana ou outras soluções[4].
- **Implemente healthchecks** no Dockerfile para monitorar a saúde do container[7].

---

## **7. Ciclo de Vida dos Containers**

| Estágio  | Prática Recomendada            | Benefício                      |
| -------- | ------------------------------ | ------------------------------ |
| Criação  | Multi-stage builds             | Imagens menores e seguras      |
| Execução | Limitar recursos, healthchecks | Previne abuso de recursos      |
| Pausa    | `docker pause`                 | Economiza recursos temporários |
| Parada   | SIGTERM antes de SIGKILL       | Desligamento gracioso          |
| Deleção  | Automatizar limpeza            | Sistema limpo e eficiente      |

---

## **8. Checklist Rápido de Segurança**

- [ ] Docker e host atualizados
- [ ] Imagens oficiais e minimalistas
- [ ] Sem segredos no Dockerfile
- [ ] Containers não rodam como root
- [ ] Limites de recursos aplicados
- [ ] Filesystem read-only quando possível
- [ ] Portas expostas apenas se necessário
- [ ] Scans de vulnerabilidade regulares
- [ ] Logs e monitoramento ativos

---

> “A segurança e eficiência no Docker dependem de imagens enxutas, containers bem configurados e monitoramento contínuo.”[1][2][7]

---

Com este survival kit, você estará preparado para operar Docker de forma prática, segura e eficiente.

Citations:
[1] https://www.aquasec.com/blog/docker-security-best-practices/
[2] https://www.comparitech.com/net-admin/docker-security-cheat-sheet/
[3] https://daily.dev/blog/docker-container-lifecycle-management-best-practices
[4] https://dev.to/devops_descent/mastering-docker-essential-best-practices-for-efficiency-and-security-34ij
[5] https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
[6] https://www.datacamp.com/tutorial/docker-tutorial
[7] https://anchore.com/blog/docker-security-best-practices-a-complete-guide/
[8] https://blog.stackademic.com/docker-essentials-every-developer-needs-to-know-21d43d574eed?gi=6243c0a01108
[9] https://www.hostinger.com/tutorials/docker-cheat-sheet
[10] https://blog.gruntwork.io/a-crash-course-on-docker-34073b9e1833?gi=b3d1b4ef42e4