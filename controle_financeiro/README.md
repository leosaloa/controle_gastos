# 💰 Sistema de Controle Financeiro

Sistema completo de controle de despesas pessoais com banco de dados SQLite.

## 📋 Funcionalidades

- ✅ Gestão de Ciclos financeiros
- ✅ Gastos Fixos (assinaturas, contas, etc)
- ✅ Lançamentos de despesas variáveis
- ✅ Cartões de Crédito com controle de limite
- ✅ Investimentos
- ✅ Storytelling inteligente dos gastos
- ✅ Dashboard com resumo geral
- ✅ Banco de dados SQLite local

## 🚀 Como Instalar e Rodar

### 1. Estrutura de Pastas

Crie a seguinte estrutura de pastas:

```
meu_controle_financeiro/
├── app.py
├── requirements.txt
├── README.md
└── templates/
    └── index.html
```

### 2. Instalação

**Passo 1:** Certifique-se de ter Python 3.8+ instalado
```bash
python --version
```

**Passo 2:** Crie um ambiente virtual (recomendado)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

**Passo 3:** Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Executar o Sistema

```bash
python app.py
```

O sistema estará disponível em: **http://127.0.0.1:5000**

### 4. Parar o Sistema

Pressione `Ctrl + C` no terminal

## 📁 Arquivos do Projeto

### `app.py`
Backend em Python/Flask com todas as rotas da API e modelos do banco de dados.

### `templates/index.html`
Frontend HTML com JavaScript para interface do usuário.

### `requirements.txt`
Dependências Python necessárias.

### `financeiro.db`
Banco de dados SQLite (criado automaticamente na primeira execução).

## 🗄️ Estrutura do Banco de Dados

O sistema cria automaticamente 5 tabelas:

1. **ciclo** - Ciclos financeiros (mês/período)
2. **gasto_fixo** - Despesas fixas mensais
3. **lancamento** - Lançamentos de gastos variáveis
4. **investimento** - Investimentos realizados
5. **cartao_credito** - Cartões de crédito e limites

## 📊 Dados de Exemplo

Na primeira execução, o sistema cria:
- 1 ciclo padrão (Janeiro 2026)
- 3 gastos fixos (Netflix, Água, Luz)
- 2 lançamentos (Supermercado, Gasolina)
- 2 investimentos (Tesouro Direto, Ações)
- 1 cartão de crédito (Nubank)

Você pode deletar e adicionar seus próprios dados!

## 🔧 Personalização

### Alterar o orçamento do ciclo

Edite em `app.py` na função `init_db()`:
```python
orcamento=5000.00  # Altere para seu orçamento
```

### Resetar banco de dados

Delete o arquivo `financeiro.db` e execute novamente:
```bash
rm financeiro.db  # Linux/Mac
del financeiro.db  # Windows
python app.py
```

## 🐛 Resolução de Problemas

**Erro: Módulo não encontrado**
```bash
pip install -r requirements.txt
```

**Erro: Porta 5000 em uso**
Edite `app.py` na última linha:
```python
app.run(debug=True, port=5001)  # Use outra porta
```

**Banco não inicializa**
Delete `financeiro.db` e rode novamente.

## 📝 API Endpoints

### Ciclos
- `GET /api/ciclo` - Obter ciclo ativo
- `POST /api/ciclo` - Criar novo ciclo

### Gastos Fixos
- `GET /api/gastos-fixos` - Listar todos
- `POST /api/gastos-fixos` - Criar novo
- `DELETE /api/gastos-fixos/<id>` - Deletar

### Lançamentos
- `GET /api/lancamentos` - Listar todos
- `POST /api/lancamentos` - Criar novo
- `DELETE /api/lancamentos/<id>` - Deletar

### Investimentos
- `GET /api/investimentos` - Listar todos
- `POST /api/investimentos` - Criar novo
- `DELETE /api/investimentos/<id>` - Deletar

### Cartões
- `GET /api/cartoes` - Listar todos
- `POST /api/cartoes` - Criar novo
- `PUT /api/cartoes/<id>` - Atualizar valor
- `DELETE /api/cartoes/<id>` - Deletar

## 📱 Acesso Remoto

Para acessar de outros dispositivos na mesma rede:

```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

Depois acesse: `http://SEU_IP:5000`

## ✨ Melhorias Futuras

- [ ] Autenticação de usuários
- [ ] Gráficos e relatórios
- [ ] Exportar para Excel/PDF
- [ ] Backup automático
- [ ] App mobile

## 📄 Licença

Livre para uso pessoal e modificação!

---

**Desenvolvido com ❤️ usando Python, Flask e SQLite**