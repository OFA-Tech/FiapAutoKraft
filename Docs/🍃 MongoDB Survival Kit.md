## 🚀 Instalação rápida com Docker

```bash
docker run -d -p 27017:27017 \
  --name mongodb \
  -v mongo_data:/data/db \
  mongo
```

**Acesso com GUI opcional:**

```bash
docker run -d -p 8081:8081 \
  --name mongo-express \
  --link mongodb \
  -e ME_CONFIG_MONGODB_SERVER=mongodb \
  mongo-express
```

> Acesse `http://localhost:8081`

---

## 📦 Estrutura Mongo

- **Database** → Ex: `estoque`
- **Collection** → Ex: `produtos`, `robots`
- **Document** → JSON com dados (não precisa de schema fixo)

Exemplo de `produto`:
```json
{
  "_id": "6639d13f1e6b4e4d68",
  "nome": "Caixa A",
  "quantidade": 12,
  "localizacao": "prateleira-3"
}
```

---

## 🔌 Conectando com .NET (MongoDB.Driver)

```bash
dotnet add package MongoDB.Driver
```

```csharp
public class MongoDbConfig
{
    public string ConnectionString { get; set; } = "mongodb://localhost:27017";
    public string Database { get; set; } = "estoque";
}
```

```csharp
public class MongoContext
{
    private readonly IMongoDatabase _db;

    public MongoContext(IOptions<MongoDbConfig> config)
    {
        var client = new MongoClient(config.Value.ConnectionString);
        _db = client.GetDatabase(config.Value.Database);
    }

    public IMongoCollection<Produto> Produtos =>
        _db.GetCollection<Produto>("produtos");
}
```

---

## 🧱 CRUD Básico (.NET)

```csharp
public class ProdutoService
{
    private readonly IMongoCollection<Produto> _colecao;

    public ProdutoService(MongoContext ctx) => _colecao = ctx.Produtos;

    public async Task<List<Produto>> ObterTodos() =>
        await _colecao.Find(_ => true).ToListAsync();

    public async Task<Produto> ObterPorId(string id) =>
        await _colecao.Find(p => p.Id == id).FirstOrDefaultAsync();

    public async Task Criar(Produto p) => await _colecao.InsertOneAsync(p);

    public async Task Atualizar(string id, Produto novo) =>
        await _colecao.ReplaceOneAsync(p => p.Id == id, novo);

    public async Task Remover(string id) =>
        await _colecao.DeleteOneAsync(p => p.Id == id);
}
```

---

## 💡 Vantagens MongoDB

| 💚 MongoDB | Por que é útil |
|------------|----------------|
| Schema flexível | Ideal pra protótipos e projetos dinâmicos |
| JSON-like | Fácil integração com APIs REST |
| Alta performance | Ótimo pra leitura rápida (inventário, visão) |
| Escalável horizontalmente | Escala com sharding |
| Pode ser usado com IA / log / cache | Flexível pra muitos usos |

---

## 🧪 Testar com Mongo Compass

1. Baixe o [MongoDB Compass](https://www.mongodb.com/try/download/compass)
2. Conecte com: `mongodb://localhost:27017`
3. Navegue pelas collections
4. Edite, exclua e visualize documentos facilmente

---

## 🧠 Dicas pro seu projeto de picking

- Coleção `produtos`: inventário do armazém (nome, qtd, localização)
- Coleção `movimentos`: histórico de pickings, logs de IA
- Coleção `robots`: status atual do robô, posição, falhas
- Pode usar Hangfire pra salvar no Mongo após o picking