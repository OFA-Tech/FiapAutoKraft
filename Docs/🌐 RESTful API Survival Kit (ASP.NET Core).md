## 📦 Setup básico do projeto

```bash
dotnet new webapi -n ApiRobusta
cd ApiRobusta
dotnet add package Swashbuckle.AspNetCore
```

---

## 🛠 Estrutura RESTful

```
/api
  └── /produtos
  └── /usuarios
  └── /robots
```

### Rotas REST comuns para `Produto`

| Ação              | Verbo   | Rota              | Status esperado |
|-------------------|---------|-------------------|-----------------|
| Listar todos      | GET     | /api/produtos     | 200 OK          |
| Buscar por ID     | GET     | /api/produtos/3   | 200 / 404       |
| Criar             | POST    | /api/produtos     | 201 Created     |
| Atualizar         | PUT     | /api/produtos/3   | 204 No Content  |
| Deletar           | DELETE  | /api/produtos/3   | 204 No Content  |

---

## ✍️ Exemplo de Controller REST

```csharp
[ApiController]
[Route("api/[controller]")]
public class ProdutosController : ControllerBase
{
    private static List<string> produtos = new() { "Sensor", "Motor", "Placa" };

    [HttpGet]
    public IActionResult Get() => Ok(produtos);

    [HttpGet("{id}")]
    public IActionResult Get(int id)
    {
        if (id < 0 || id >= produtos.Count) return NotFound();
        return Ok(produtos[id]);
    }

    [HttpPost]
    public IActionResult Post([FromBody] string nome)
    {
        produtos.Add(nome);
        return CreatedAtAction(nameof(Get), new { id = produtos.Count - 1 }, nome);
    }

    [HttpPut("{id}")]
    public IActionResult Put(int id, [FromBody] string nome)
    {
        if (id < 0 || id >= produtos.Count) return NotFound();
        produtos[id] = nome;
        return NoContent();
    }

    [HttpDelete("{id}")]
    public IActionResult Delete(int id)
    {
        if (id < 0 || id >= produtos.Count) return NotFound();
        produtos.RemoveAt(id);
        return NoContent();
    }
}
```

---

## 🔍 Swagger (Documentação automática)

Habilite no `Program.cs`:

```csharp
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

app.UseSwagger();
app.UseSwaggerUI();
```

> Acesse em `http://localhost:5000/swagger`

---

## ✅ Boas práticas REST

| Prática | Exemplo |
|--------|---------|
| Use verbos corretos | GET, POST, PUT, DELETE |
| Use `StatusCode` coerente | 404, 201, 204, 500 etc |
| Use DTOs para entrada/saída | Evite expor models diretamente |
| Versionamento? | Use `/api/v1/...` se for necessário |
| Autenticação? | JWT + `[Authorize]` nos controllers |

---

## 🧪 Testar API

### Com Postman / Insomnia
- Envie requisições com corpo JSON
- Teste rotas e status
- Adicione autenticação JWT se necessário

### Com Swagger UI
- Interface gráfica pronta
- Testa os endpoints direto do navegador

---

## 🧠 Dica: Integrando com Hangfire, YOLO, etc

- Você pode fazer um `POST /api/picking/start` que aciona um `BackgroundJob.Enqueue(...)`
- Ou `GET /api/camera/ultimafoto` que retorna uma imagem gerada com OpenCV
- Ou ainda `POST /api/robo/mover` com parâmetros de movimentação
