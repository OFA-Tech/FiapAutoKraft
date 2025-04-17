## 🧠 O que é o SonarQube?

É uma plataforma que **analisa seu código-fonte automaticamente** em busca de:

- Bugs e vulnerabilidades
- _Code smells_ (más práticas)
- Cobertura de testes
- Duplicação de código
- Manutenção da qualidade com _Quality Gates_

---

## 🚀 Stack comum com SonarQube

Ideal pra usar com:

- **.NET / C#**
- **Python / Java / JavaScript / TypeScript**
- **SQL / HTML / Dockerfile / YAML**
- Integração com Git, GitHub Actions, GitLab CI/CD, Jenkins

---

## ⚙️ Instalação rápida com Docker

```yaml
version: '3'

services:
  sonarqube:
    image: sonarqube:community
    container_name: sonarqube
    ports:
      - "9000:9000"
    environment:
      SONAR_JDBC_URL: jdbc:postgresql://db:5432/sonar
      SONAR_JDBC_USERNAME: sonar
      SONAR_JDBC_PASSWORD: sonar
    depends_on:
      - db

  db:
    image: postgres:13
    container_name: postgres-sonar
    environment:
      POSTGRES_USER: sonar
      POSTGRES_PASSWORD: sonar
      POSTGRES_DB: sonar
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

> Depois: acesse `http://localhost:9000` com `admin / admin`

---

## 🔍 Análise de código local (ex: backend C# ou Python)

### 🧪 1. Instale o scanner

```bash
# Windows/Linux/macOS
# https://docs.sonarcloud.io/advanced-setup/ci-based-analysis/sonarscanner-cli/

brew install sonarscanner  # macOS
```

### 🧪 2. Crie arquivo `sonar-project.properties`

```ini
sonar.projectKey=api-produto
sonar.projectName=API Produto
sonar.projectVersion=1.0

sonar.sources=src
sonar.language=cs
sonar.host.url=http://localhost:9000
sonar.login=<SEU_TOKEN>
```

> Gere o token em `My Account > Security > Generate Token`

### 🧪 3. Rode o scanner

```bash
sonar-scanner
```

---

## 📈 Quality Gate

- Regras de aprovação automática de PRs
- Pode travar merges se houver falhas críticas ou cobertura baixa
- Personalizável por projeto/time

---

## 🧱 Exemplos de erros que ele detecta

| Tipo              | Exemplo                                       |
|-------------------|-----------------------------------------------|
| 🐞 Bug            | NullReference, divisão por zero               |
| 🔐 Vulnerabilidade| Senhas hardcoded, SQL injection               |
| 🤢 Code Smell     | Métodos longos, variáveis não usadas          |
| 🧪 Coverage        | Falta de testes unitários                    |
| 📋 Duplicação     | Blocos de código idênticos entre arquivos     |

---

## 🔄 Integração com CI/CD (GitHub Actions, GitLab, Jenkins)

Exemplo com **GitHub Actions**:

```yaml
- name: Run SonarQube Scanner
  uses: sonarsource/sonarqube-scan-action@v1.0.1
  with:
    projectBaseDir: .
    args: >
      -Dsonar.projectKey=api-produto
      -Dsonar.organization=seu-org
      -Dsonar.sources=.
      -Dsonar.host.url=http://localhost:9000
      -Dsonar.login=${{ secrets.SONAR_TOKEN }}
```

---

## 🧠 Dicas para o seu projeto

| Componente           | Análise recomendada                     |
|----------------------|------------------------------------------|
| API REST (.NET/C#)   | Code smells, coverage, duplicações       |
| IA / Visão (Python)  | Bugs e vulnerabilidades (ex: `eval`, `os.system`) |
| Scripts Docker/YAML  | Checagem de boas práticas de CI/CD       |
| Front (JS/TS)        | Segurança e padrões de UI                |

---

## ✅ Checklist prático

- [ ] Subir SonarQube local com Docker
- [ ] Integrar scanner com sua API (.NET/Python/etc)
- [ ] Criar token pessoal no Sonar
- [ ] Adicionar `sonar-project.properties`
- [ ] Rodar e monitorar painel (http://localhost:9000)