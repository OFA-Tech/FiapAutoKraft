

**Este guia reúne os conceitos essenciais, comandos básicos, boas práticas e dicas de segurança para gerenciar containers com Podman, uma alternativa segura e sem daemon ao Docker.**

---

## **1. Conceitos Básicos**

- **Podman:** Ferramenta de gerenciamento de containers de código aberto, sem daemon, compatível com OCI, desenvolvida pela Red Hat, focada em segurança e facilidade de uso[2][3].
- **Containers:** Ambientes isolados que compartilham o kernel do sistema host, oferecendo virtualização leve[1][8].
- **Pods:** Grupos de containers que compartilham rede e recursos, facilitando a orquestração de múltiplos containers[2][3].

---

## **2. Instalação do Podman**

```bash
# No Oracle Linux ou distribuições compatíveis
sudo transactional-update pkg install podman
# Reinicie o sistema após a instalação
```

Para outras distribuições, consulte a documentação específica, como no link oficial[1].

---

## **3. Comandos Essenciais**

```bash
# Verificar versão do Podman
podman --version
```

```bash
# Listar containers em execução
podman ps
```

```bash
# Listar todos os containers (inclusive parados)
podman ps -a
```

```bash
# Executar um container interativo e removê-lo após uso
podman run -it --rm ubuntu:latest /bin/bash
```

```bash
# Criar e iniciar um container
podman run -d --name meu_container nginx:latest
```

```bash
# Parar um container
podman stop meu_container
```

```bash
# Remover um container
podman rm meu_container
```

```bash
# Buscar uma imagem no repositório
podman pull nginx:latest
```

```bash
# Criar um pod
podman pod create --name meu_pod
```

```bash
# Adicionar containers ao pod
podman run -d --name web --pod meu_pod nginx:latest
podman run -d --name db --pod meu_pod postgres:latest
```

---

## **4. Boas Práticas**

- **Utilize imagens oficiais ou minimalistas** para reduzir vulnerabilidades e tamanho.
- **Prefira containers rootless** para maior segurança.
- **Use pods** para agrupar containers que precisam compartilhar rede e recursos.
- **Atualize o Podman regularmente** para garantir segurança e compatibilidade.
- **Evite usar privilégios de root** desnecessariamente.
- **Gerencie volumes e redes de forma segura**, expondo apenas o necessário.

---

## **5. Segurança**

- **Rodar containers sem privilégios de root** (rootless).
- **Utilizar perfis de segurança** como SELinux ou AppArmor.
- **Limitar recursos** com flags como `--memory`, `--cpus`.
- **Manter o sistema e o Podman atualizados**.
- **Utilizar imagens verificadas** e realizar scans de vulnerabilidades.
- **Configurar firewalls** para restringir acessos às portas expostas.

---

## **6. Monitoramento e Logs**

- Use comandos como `podman logs ` para verificar logs.
- Monitore containers com ferramentas externas (Prometheus, Grafana).
- Configure healthchecks nos containers para monitorar sua saúde.

---

## **7. Gerenciamento de Pods**

| Comando | Descrição |
| --- | --- |
| `podman pod create --name nome_pod` | Cria um novo pod |
| `podman run --pod nome_pod` | Executa container dentro do pod |
| `podman pod ps` | Lista os pods ativos |
| `podman pod stop nome_pod` | Para o pod e seus containers |
| `podman pod rm nome_pod` | Remove o pod |

---

## **8. Dicas finais**

- Aproveite o **compatibilidade com comandos Docker** para facilitar a transição.
- Explore o **Podman Desktop** para uma interface gráfica, facilitando o gerenciamento[8].
- Use **Buildah e Skopeo** integrados ao Podman para criar e gerenciar imagens de forma avançada[3].

---

> “O Podman oferece uma alternativa segura, leve e sem daemon ao Docker, ideal para ambientes que priorizam segurança e simplicidade.”

---

Com este survival kit, você estará preparado para gerenciar containers de forma eficiente, segura e compatível com o ecossistema OCI usando Podman.

Citations:
[1] https://docs.oracle.com/pt-br/learn/intro_podman/index.html
[2] https://www.redhat.com/pt-br/topics/containers/what-is-podman
[3] https://www.datacamp.com/pt/tutorial/introduction-to-podman-for-machine-learning-streamlining-ml-ops-workflows
[4] https://www.youtube.com/watch?v=epEuLq_IkMw
[5] https://documentation.suse.com/pt-br/sle-micro/6.0/html/Micro-podman/index.html
[6] https://dev.to/dellamas/ptbr-podman-uma-bela-opcao-1lg6
[7] https://documentation.suse.com/pt-br/sle-micro/6.0/pdf/podman-basics_pt_br.pdf
[8] https://www.redhat.com/pt-br/topics/open-source/o-que-e-o-podman-desktop