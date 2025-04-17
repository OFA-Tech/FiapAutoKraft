## 🚀 Instalação rápida com Docker

```bash
docker run --name mysql -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=estoque -p 3306:3306 -d mysql:8
```

> A senha padrão aqui é `root`, mas recomendo trocar em produção.

---

## 💻 GUI Web: Adminer (alternativa ao phpMyAdmin)

```bash
docker run --name adminer -d -p 8080:8080 adminer
```

> Acesse `http://localhost:8080`  
> Server: `mysql` • User: `root` • Password: `root`

---

## 📦 Estrutura SQL clássica

```sql
CREATE TABLE Produto (
  Id CHAR(36) PRIMARY KEY,
  Nome VARCHAR(100),
  Quantidade INT,
  Localizacao VARCHAR(50)
);
```

---

## 🔌 Usando com .NET (.NET Core / EF Core)

```bash
dotnet add package Pomelo.EntityFrameworkCore.MySql
```

### ⚙️ Configuração no `appsettings.json`:

```json
{
  "ConnectionStrings": {
    "MySqlConn": "Server=localhost;Database=estoque;User=root;Password=root;"
  }
}
```

---

## 🧱 DbContext básico

```csharp
public class Produto
{
    public Guid Id { get; set; }
    public string Nome { get; set; }
    public int Quantidade { get; set; }
    public string Localizacao { get; set; }
}

public class EstoqueDbContext : DbContext
{
    public EstoqueDbContext(DbContextOptions<EstoqueDbContext> options)
        : base(options) {}

    public DbSet<Produto> Produtos { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Produto>().ToTable("Produto");
    }
}
```

### Startup:

```csharp
builder.Services.AddDbContext<EstoqueDbContext>(options =>
    options.UseMySql(builder.Configuration.GetConnectionString("MySqlConn"),
        new MySqlServerVersion(new Version(8, 0, 0))));
```

---

## 🧪 Comandos úteis

| Comando                             | Função |
|------------------------------------|--------|
| `SHOW DATABASES;`                  | Ver bancos criados |
| `USE estoque;`                     | Selecionar banco |
| `SHOW TABLES;`                     | Ver tabelas |
| `DESCRIBE Produto;`                | Ver estrutura da tabela |
| `SELECT * FROM Produto;`           | Listar dados |
| `DROP TABLE Produto;`              | Deletar tabela |
| `ALTER TABLE Produto ADD coluna...`| Alterar tabela |

---

## 🔐 Dica extra: usar `uuid()` no lugar de `AUTO_INCREMENT` pra Ids

```sql
CREATE TABLE Produto (
  Id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  Nome VARCHAR(100),
  Quantidade INT
);
```

---

## 🤖 Dica pro seu projeto de picking

| Tabela        | Uso no projeto |
|---------------|----------------|
| `Produto`     | Inventário com nome, qtd, localização |
| `LogPicking`  | Histórico das execuções de picking |
| `RoboStatus`  | Status atual dos AMRs e URs |
| `Agendamentos`| Integra com Hangfire para tarefas |