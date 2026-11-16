# Circula — empréstimos de equipamentos

Aplicação web acadêmica para escolas e laboratórios. A lógica é escrita em **Python com Flask**; as páginas são HTML gerado por Jinja, com CSS local. Não é necessário instalar Node.js, TypeScript ou Java.

## Executar agora

No Windows, abra **`iniciar.cmd`**. Ele prepara um ambiente virtual quando necessário, instala as dependências na primeira execução e inicia a aplicação.

Abra **http://127.0.0.1:5000**. Para encerrar, pressione `Ctrl+C` no terminal.

Requisitos: Python **3.12 recomendado** e acesso à internet para a primeira instalação das dependências. O sistema em si funciona localmente sem internet depois da instalação.

### Instalação manual no Windows / PowerShell

Na pasta do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Não é preciso ativar o ambiente virtual. Se o comando `py` não estiver disponível, use o executável do seu Python no primeiro comando. Nas próximas execuções, basta o último comando.

### Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## O que funciona

- Cadastro, busca, filtros e edição de equipamentos com patrimônio único.
- Situação do equipamento: apto para empréstimo, manutenção ou desativado.
- Cadastro e edição de pessoas, com identificação única, vínculo e contato.
- Empréstimo de uma unidade física a uma pessoa ativa.
- Prazo de devolução, observações da retirada e conferência da devolução.
- Disponibilidade atualizada a cada operação e bloqueio de empréstimos simultâneos do mesmo item.
- Atrasos calculados pela data de Brasília, com vencimento válido até o fim do dia informado.
- Histórico, detalhes de cada empréstimo e exportação dos resultados filtrados em CSV.
- Painel com totais e composição do acervo por categoria.
- Senha única de gestão quando `ADMIN_PASSWORD` estiver configurada.

Os três requisitos do trabalho aparecem no fluxo completo: o usuário preenche formulários; o Python valida e grava no banco; o painel e as tabelas consultam o banco para apresentar resultados atualizados.

## Primeiro uso e demonstração

O banco começa vazio. Você pode cadastrar equipamentos e pessoas ou selecionar **“Explorar com dados fictícios”** na visão geral.

Essa opção insere 8 equipamentos, 5 pessoas e 4 empréstimos, incluindo um atraso e uma devolução. Nomes e e-mails são fictícios. Os exemplos só podem ser carregados se o banco estiver totalmente vazio; os registros existentes nunca são sobrescritos. As datas dos exemplos são relativas ao dia do carregamento.

## Banco de dados

**Localmente:** SQLite, criado automaticamente em `instance/circula.db`. Fechar o navegador ou reiniciar o servidor não apaga os registros. Com a aplicação parada, copie esse arquivo para fazer um backup local. O arquivo do banco não vai para o Git nem para o pacote de entrega.

**Na Vercel:** PostgreSQL externo, por exemplo Neon. A conexão é escolhida por `DATABASE_URL` ou, se ela estiver vazia, por `POSTGRES_URL`, fornecida por algumas integrações do Neon. Os mesmos modelos são utilizados nos dois bancos. Não use SQLite em `/tmp` na hospedagem: esse arquivo não é uma base persistente compartilhada entre execuções.

Cada equipamento representa **uma unidade física**, não um saldo de estoque. O índice único de empréstimos em aberto impede duplicidade também no banco. A devolução preserva o histórico. Cadastros com empréstimos em andamento não podem ser desativados ou colocados em manutenção.

## Publicar depois no Git e na Vercel

Repositório: [MatheusGino71/Projeto_Integrador](https://github.com/MatheusGino71/Projeto_Integrador). A configuração para a Vercel está incluída; **a aplicação ainda não foi publicada**.

1. Use o repositório acima para importar o projeto na Vercel. O `.gitignore` já exclui `.env`, `.venv`, caches, bancos locais e entregas geradas.
2. Crie um PostgreSQL no Neon ou outro provedor e copie a conexão com TLS (`sslmode=require`). Você também pode conectar o Neon pelo Marketplace da Vercel.
3. Em sua máquina, copie `.env.example` para `.env` e preencha:

   ```dotenv
   DATABASE_URL=postgresql://USUARIO:SENHA@HOST/BANCO?sslmode=require
   SECRET_KEY=uma-chave-aleatoria-longa
   ADMIN_PASSWORD=uma-senha-de-acesso-forte
   ```

   Não envie o `.env` ao Git. Para gerar o valor de `SECRET_KEY`, execute:

   ```powershell
   .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Para inicializar o banco remoto manualmente, execute:

   ```powershell
   .\.venv\Scripts\python.exe -m flask --app app init-db
   ```

   Esse comando cria as tabelas e os índices sem apagar registros existentes. A Vercel executa esse mesmo comando automaticamente durante o build, depois de instalar as dependências. Não é uma ferramenta de migração de versões do esquema.

5. Importe o repositório na Vercel. Use a raiz do projeto e o preset **Flask** detectado pela plataforma. O `vercel.json` já configura o comando de inicialização do banco. Não configure build de frontend nem uma pasta `dist`.
6. Cadastre `SECRET_KEY` e `ADMIN_PASSWORD` e confira a conexão em `DATABASE_URL` ou `POSTGRES_URL` no ambiente da Vercel. A plataforma fornece `VERCEL=1` automaticamente.
7. Acesse o endereço publicado, entre com a senha e teste um cadastro, um empréstimo e uma devolução. Após alterar variáveis, faça um novo deployment.

Na hospedagem, a aplicação exige a conexão PostgreSQL e as duas variáveis de acesso. O build verifica a configuração e cria as tabelas ausentes antes de publicar. Se faltarem configurações em uma versão já publicada, ela mostra uma página de orientação em vez de gravar dados em arquivos temporários. Os arquivos de `public/` são servidos no mesmo caminho localmente e pela CDN da Vercel.

O PostgreSQL hospedado e o deployment precisam ser validados depois de conectar suas contas. Os testes incluídos usam SQLite temporário; não dependem de conta externa.

Referências oficiais de publicação: [Flask na Vercel](https://vercel.com/docs/frameworks/backend/flask), [runtime Python](https://vercel.com/docs/functions/runtimes/python), [armazenamento](https://vercel.com/docs/marketplace-storage).

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

No Linux/macOS, substitua o executável por `.venv/bin/python`. Os testes usam bancos isolados e não modificam seus cadastros. Consulte os casos e o roteiro manual em [docs/TESTES.md](docs/TESTES.md).

## Arquivos para a avaliação

- [docs/PROJETO.md](docs/PROJETO.md): problema, público, necessidade, solução e os três eixos com referências.
- [docs/TESTES.md](docs/TESTES.md): validação automatizada e roteiro para a demonstração.
- [docs/ARQUITETURA.md](docs/ARQUITETURA.md): organização e modelo de dados.
- Código, templates, estilos e dependências neste repositório.

Para gerar um ZIP com os arquivos necessários, sem ambiente virtual, credenciais ou banco local:

```powershell
.\.venv\Scripts\python.exe empacotar.py
```

O pacote será criado em `entrega/circula-projeto.zip`. O avaliador extrai a pasta e segue este README. A primeira instalação das bibliotecas requer internet.

## Limites desta versão

Aplicação para uma unidade escolar e uma área de gestão compartilhada por senha. Não inclui contas individuais, reservas futuras, multas, notificações por e-mail, anexos nem assinatura de termos. A conferência é feita pelo responsável antes da confirmação. O histórico mostra os dados atuais dos cadastros relacionados.

O problema local e os benefícios ainda precisam de validação com usuários reais. Os dados de demonstração e os testes técnicos não substituem essa pesquisa.
