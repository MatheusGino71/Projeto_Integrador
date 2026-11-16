# Validação e roteiro de demonstração

## Testes automatizados

Na raiz do projeto, com as dependências instaladas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes usam o cliente HTTP do Flask e bancos SQLite temporários. Nenhum cadastro local é apagado ou reutilizado. A suíte cobre:

**Resultado local em 16/11/2026:** 23 testes passaram, utilizando Python 3.12.3. Incluem a alternativa `POSTGRES_URL` fornecida pelo Neon e a prioridade de `DATABASE_URL`. A configuração PostgreSQL e o índice parcial foram compilados sem conexão externa; isso não equivale a testar um banco PostgreSQL hospedado.

O iniciador Windows também foi executado. Em um banco separado de demonstração, um teste HTTP com o servidor ativo confirmou carga de exemplos, retirada e devolução com cookies e CSRF habilitados. O ZIP foi extraído em uma pasta de revisão e os mesmos 21 testes passaram a partir dos arquivos empacotados.

| Área | Verificação |
| --- | --- |
| Execução | Páginas vazias, formulários, estilos, favicon e retorno 404 |
| Circulação | Cadastro → empréstimo → devolução → novo empréstimo |
| Integridade | Bloqueio de patrimônio e identificação repetidos |
| Concorrência | Índice do banco impede dois empréstimos em aberto do mesmo equipamento |
| Validação | Datas inválidas, data passada, IDs inexistentes, campos vazios e limites |
| Disponibilidade | Manutenção e pessoa inativa impedem retirada |
| Edição | Desativação e manutenção bloqueadas durante empréstimo pendente |
| Devolução | Segunda tentativa não altera a primeira conferência |
| Prazos | Vencimento hoje, atraso no dia seguinte e contagem encerrada na devolução |
| Demonstração | Carga explícita, sem sobrescrever ou duplicar dados existentes |
| Consultas | Busca, filtros e CSV retornam os mesmos registros |
| Conteúdo | HTML digitado é escapado e fórmulas em CSV são neutralizadas |
| Acesso | Senha, encerramento da sessão e formulários com CSRF |
| Persistência | Dados continuam disponíveis em uma nova instância da aplicação |
| Configuração | Orientação quando variáveis da hospedagem estão ausentes |
| PostgreSQL | Conexão e índice parcial configurados sem depender de acesso externo |
| Inicialização | O comando `init-db` preserva cadastros existentes |

O teste da restrição única verifica diretamente o banco, além da validação HTTP. Ele não é um teste de carga com múltiplas instâncias remotas.

## Roteiro manual para apresentar ao avaliador

1. Execute a aplicação e abra `http://127.0.0.1:5000`.
2. Se o banco estiver vazio, clique em **Explorar com dados fictícios**. Explique que são exemplos e que ainda não houve pesquisa de campo.
3. Mostre os totais na visão geral e o empréstimo em atraso. Abra o filtro de atrasos.
4. Em **Equipamentos**, pesquise por `NT-002` e veja a disponibilidade.
5. Selecione **Emprestar**, escolha uma pessoa e uma data futura. Registre um acessório nas observações e confirme.
6. Volte a **Equipamentos**. A unidade agora aparece como emprestada e não está disponível para outra retirada.
7. Em **Empréstimos**, registre a devolução e a conferência do equipamento.
8. Confira o registro em **Devolvidos**, abra os detalhes e verifique a observação.
9. Mostre o equipamento disponível novamente e exporte o histórico em CSV.
10. Encerre o servidor, inicie novamente e confira que os registros permanecem.

Para demonstrar um atraso sem alterar o relógio do computador, utilize o empréstimo já vencido dos exemplos. A aplicação não permite criar uma nova retirada com prazo no passado.

## Revisão visual e de uso a concluir

- Conferir as telas em computador e celular, incluindo largura de 375 px.
- Verificar foco e operação dos formulários usando apenas o teclado.
- Conferir mensagens de erro e leitura em zoom de 200%.
- Testar um ciclo completo após publicar com PostgreSQL na Vercel.
- Validar a linguagem e os campos com uma pessoa do público escolhido.

A revisão visual no navegador não foi concluída no ambiente de desenvolvimento desta entrega. Os templates foram renderizados nos testes HTTP, mas isso não substitui a conferência do layout em navegador.

## Evidências e limites

A execução da suíte deve ser registrada no ambiente do avaliador. Não se deve apresentar testes locais com SQLite como evidência de que a hospedagem já foi publicada ou validada com PostgreSQL. Os testes técnicos também não demonstram ganho de tempo ou satisfação de usuários reais.
