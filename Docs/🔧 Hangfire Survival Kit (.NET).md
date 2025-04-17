## 📦 Instalação

```bash
dotnet add package Hangfire
dotnet add package Hangfire.AspNetCore
```

Opcional (para usar Redis, PostgreSQL, etc):

```bash
dotnet add package Hangfire.Redis.StackExchange
dotnet add package Hangfire.PostgreSql
```

---

## ⚙️ Setup Básico no `Startup.cs` ou `Program.cs` (.NET 6+)

```csharp
builder.Services.AddHangfire(config =>
    config.UseInMemoryStorage()); // ou UsePostgreSqlStorage, UseRedisStorage, etc.

builder.Services.AddHangfireServer();

app.UseHangfireDashboard(); // /hangfire disponível
```

> Use `UsePostgreSqlStorage("connection_string")` ou outro provedor de acordo com seu banco.

---

## 🧪 Criando um Job Simples

```csharp
public class TarefasRoboticas
{
    public void FazerInventario()
    {
        Console.WriteLine("Rodando inventário automático...");
    }
}
```

### 🚀 Enfileirar Job (execução imediata)

```csharp
BackgroundJob.Enqueue(() => new TarefasRoboticas().FazerInventario());
```

### ⏰ Executar com delay

```csharp
BackgroundJob.Schedule(() => Console.WriteLine("Executar depois..."), TimeSpan.FromMinutes(5));
```

### 🔁 Job Recorrente

```csharp
RecurringJob.AddOrUpdate(
    "inventario-estoque",
    () => new TarefasRoboticas().FazerInventario(),
    Cron.Hourly); // minutely, daily, Cron expression, etc
```

### 🔄 Cron Personalizado

```csharp
CronExpression expression = Cron.MinuteInterval(10); // a cada 10 minutos
```

---

## 📋 Painel de Monitoramento

- Rota padrão: `http://localhost:5000/hangfire`
- Proteção com autenticação? Sim:

```csharp
app.UseHangfireDashboard("/hangfire", new DashboardOptions {
    Authorization = new[] { new PainelHangfireSeguranca() }
});
```

---

## 🧠 Armazenamento Alternativo

- **Redis** (ideal para distribuição ou jobs rápidos):
```csharp
.UseRedisStorage("localhost:6379");
```

- **PostgreSQL**:
```csharp
.UsePostgreSqlStorage("Host=localhost;Database=db;Username=postgres;Password=123");
```

---

## 🔄 Reprocessar/Retry automático

Hangfire por padrão:
- Reexecuta jobs com falha (ex: 10 vezes com delay exponencial)
- Loga exceções no painel
- Você pode customizar com filtros:

```csharp
public class NoRetryAttribute : JobFilterAttribute, IAutomaticRetryPolicy
{
    public override int Attempts => 0;
}
```

---

## 🧠 Dicas Rápidas

| Dica | Uso |
|------|-----|
| `IBackgroundJobClient` | Injete via DI para criar jobs |
| `RecurringJob.RemoveIfExists("nome")` | Remove job antigo |
| Use DTOs simples | Evite passar objetos pesados nos parâmetros |
| Combine com REST API | Ideal pra acionar jobs programaticamente |
| Evite usar DbContext diretamente em métodos estáticos | Prefira injeção de dependência |
