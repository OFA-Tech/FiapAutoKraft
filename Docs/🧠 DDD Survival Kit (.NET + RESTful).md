> **DDD = Separar regras de negócio da infra**  
> Foco em **Domínio** (o que importa pro negócio), com estrutura em **Camadas**.

---

## 🗂 Estrutura de Pastas (Clean DDD Style)

```
/src
  └── Api (Controllers, Program.cs)
  └── Application (UseCases, Interfaces, DTOs)
  └── Domain (Entidades, Enums, Regras)
  └── Infrastructure (EF, Repos, Services)
  └── Shared (Utils, Exceptions, Base Classes)
```

---

## 🔑 Camadas e Responsabilidades

| Camada        | Responsabilidade                                     |
|---------------|-------------------------------------------------------|
| **Domain**     | Regras de negócio, entidades, validações              |
| **Application**| Casos de uso, orquestra lógica (sem dependência de infra) |
| **Infrastructure** | Persistência, APIs externas, serviços, etc.        |
| **Api**         | Controllers e Serialização (entrada/saída)           |

---

## 📦 Exemplo prático: Sistema de Picking

### 🧱 Domain

```csharp
// Domain/Entities/Produto.cs
public class Produto
{
    public Guid Id { get; private set; }
    public string Nome { get; private set; }
    public int Quantidade { get; private set; }

    public Produto(string nome, int quantidade)
    {
        if (quantidade < 0) throw new DomainException("Quantidade inválida");
        Id = Guid.NewGuid();
        Nome = nome;
        Quantidade = quantidade;
    }

    public void AtualizarQuantidade(int novaQtd)
    {
        if (novaQtd < 0) throw new DomainException("Qtd negativa");
        Quantidade = novaQtd;
    }
}
```

---

### 💡 Application

```csharp
// Application/UseCases/Picking/IniciarPickingUseCase.cs
public class IniciarPickingUseCase
{
    private readonly IProdutoRepository _repo;

    public IniciarPickingUseCase(IProdutoRepository repo) => _repo = repo;

    public async Task Handle(Guid produtoId)
    {
        var produto = await _repo.ObterPorId(produtoId);
        produto.AtualizarQuantidade(produto.Quantidade - 1);
        await _repo.Salvar(produto);
    }
}
```

---

### 💾 Infrastructure

```csharp
// Infrastructure/Repositories/ProdutoRepository.cs
public class ProdutoRepository : IProdutoRepository
{
    private readonly DbContext _context;

    public ProdutoRepository(DbContext context) => _context = context;

    public async Task<Produto> ObterPorId(Guid id)
        => await _context.Set<Produto>().FindAsync(id);

    public async Task Salvar(Produto produto)
    {
        _context.Update(produto);
        await _context.SaveChangesAsync();
    }
}
```

---

### 🌐 API

```csharp
// Api/Controllers/PickingController.cs
[ApiController]
[Route("api/[controller]")]
public class PickingController : ControllerBase
{
    private readonly IniciarPickingUseCase _useCase;

    public PickingController(IniciarPickingUseCase useCase) => _useCase = useCase;

    [HttpPost("{produtoId}")]
    public async Task<IActionResult> Post(Guid produtoId)
    {
        await _useCase.Handle(produtoId);
        return NoContent();
    }
}
```

---

## 🧰 Extras úteis

| Ferramenta     | Uso |
|----------------|-----|
| **AutoMapper** | Mapear DTOs ↔ Entidades |
| **FluentValidation** | Validação em DTOs de entrada |
| **MediatR**    | Orquestração de Use Cases com CQRS |
| **EF Core**    | Persistência via ORM |
| **Swagger**    | Documentação automática |
| **Hangfire**   | Agendamento de casos de uso |

---

## ✅ Boas práticas DDD

- ✅ Domínio não depende de nada (nem EF, nem web)
- ✅ Não retorne entidades diretamente nos Controllers (use DTOs)
- ✅ Valide regras no **Domínio**, e dados no **DTO**
- ✅ Mantenha os Controllers magros (delegue tudo para `UseCases`)
- ✅ Nomeie as coisas com o vocabulário do negócio