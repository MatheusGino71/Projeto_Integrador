# Projeto Integrador — Circula

**Título:** Sistema web de controle de empréstimos de equipamentos escolares.

**Produto:** aplicação web independente.

**Tecnologia:** Python, Flask e banco relacional.

**Instituição, curso, disciplina, docente e integrantes:** preencher conforme os dados da turma.

**Versão do documento:** 16 de novembro de 2026.

## 1. Origem do projeto

### Problema

Em escolas e laboratórios, equipamentos como notebooks, projetores e tablets podem ser compartilhados por diferentes pessoas. Quando as retiradas são anotadas em registros dispersos, torna-se difícil responder rapidamente quem está com um item, quando ele deve voltar e quais unidades estão disponíveis.

Para este projeto, essa dificuldade é uma **hipótese de problema** fundamentada em trabalhos e práticas institucionais semelhantes. Não foi realizada entrevista, observação de rotina ou medição em uma escola parceira. Portanto, o documento não afirma que uma instituição específica possui essa falha.

### Público afetado

O público direto é formado pelos responsáveis pela entrega e recebimento dos equipamentos de uma escola ou laboratório. Alunos, professores e colaboradores são beneficiários da consulta mais organizada ao acervo, embora a operação desta primeira versão seja feita pela área de gestão.

### Necessidade

Manter um registro central de cada unidade, identificar o responsável pela retirada, combinar uma data de devolução e registrar o retorno. A consulta deve distinguir equipamentos disponíveis, emprestados, em manutenção e desativados.

### Solução

O Circula é uma aplicação web que recebe esses dados por formulários, valida as regras do empréstimo, armazena os registros em banco e apresenta o estado atualizado do acervo e dos prazos. O sistema ajuda a acompanhar o compartilhamento; a conferência física continua sendo realizada pelo responsável.

## 2. Objetivos

### Objetivo geral

Desenvolver uma aplicação web funcional para centralizar o controle de empréstimos de equipamentos escolares e facilitar a consulta de disponibilidade e devoluções pendentes.

### Objetivos específicos

1. Cadastrar equipamentos por patrimônio e pessoas por identificação única.
2. Registrar o vínculo entre equipamento, pessoa responsável e prazo de devolução.
3. Impedir duas retiradas simultâneas da mesma unidade.
4. Registrar a devolução e manter o histórico de utilização.
5. Destacar empréstimos com prazo vencido e apresentar indicadores calculados sobre os registros.
6. Disponibilizar os arquivos e as instruções necessárias para o avaliador executar o produto.

## 3. Eixo 1 — Fundamentação teórica

### 3.1 Circulação de equipamentos em instituições de ensino

O resumo do trabalho de Bourscheit (2020), disponível no repositório da UTFPR, apresenta uma aplicação web voltada ao controle dos empréstimos de equipamentos de um departamento acadêmico. O estudo oferece um antecedente diretamente relacionado ao recorte deste projeto: organizar registros da circulação de equipamentos em ambiente educacional. [Fonte: UTFPR](https://repositorio.utfpr.edu.br/jspui/handle/1/25937).

Morais et al. (2025) descrevem, no resumo de seu artigo, um processo manual de empréstimo de materiais na UFERSA e propõem uma arquitetura para apoiar seu gerenciamento. A avaliação apresentada é baseada em cenários arquiteturais. Esse trabalho sustenta a pertinência de estudar o fluxo de retirada e devolução, mas não comprova os resultados do Circula. [Fonte: revista Temática](https://periodicos.ufpb.br/index.php/tematica/article/view/74481).

A página institucional da UNIFAL-MG documenta o empréstimo de notebooks e a responsabilidade do usuário pela devolução de materiais. Essa prática reforça a necessidade de associar uma pessoa identificada a um equipamento e ao respectivo prazo. [Fonte: Sistema de Bibliotecas da UNIFAL-MG](https://www.unifal-mg.edu.br/bibliotecas/circulacao-de-materiais/).

### 3.2 Conceitos aplicados ao produto

**Identificação individual do bem:** cada unidade recebe um patrimônio único. Isso evita confundir unidades do mesmo modelo e permite consultar a situação de cada uma.

**Rastreabilidade da circulação:** o empréstimo relaciona equipamento, responsável, retirada, prazo e devolução. As observações permitem registrar acessórios e condições verificadas na entrega e no recebimento. Trata-se de rastreabilidade do fluxo cadastrado, sem localização física automática do bem.

**Integridade dos dados:** chaves estrangeiras ligam as tabelas. Um índice único parcial permite apenas um empréstimo em aberto por equipamento. Validações no servidor complementam as restrições do banco.

**Disponibilidade derivada:** a aplicação consulta a situação do equipamento e a existência de empréstimo em aberto. A devolução encerra o empréstimo, fazendo a unidade voltar a aparecer como disponível.

Essas decisões são a aplicação dos conceitos ao Circula, não resultados medidos nos trabalhos citados. A pesquisa documental foi delimitada a circulação de equipamentos em instituições de ensino, evitando uma discussão genérica sobre tecnologia na educação.

## 4. Eixo 2 — Relevância e benefícios esperados

O valor prático proposto está no acesso centralizado à informação durante a rotina de retirada e devolução.

| Dificuldade a investigar | Recurso entregue | Benefício esperado |
| --- | --- | --- |
| Não saber qual unidade pode ser retirada | Filtro de disponibilidade | Encontrar uma opção sem conferir registros dispersos |
| Dificuldade de identificar o responsável | Pessoa vinculada a cada empréstimo | Localizar o contato associado ao item |
| Perder de vista datas de devolução | Lista de atrasos e ordenação por prazo | Priorizar o acompanhamento de pendências |
| Registrar retiradas conflitantes | Bloqueio na aplicação e índice único no banco | Evitar dois empréstimos em aberto para a mesma unidade |
| Perder informações ao devolver um item | Histórico e observações da devolução | Consultar a circulação já encerrada |

Os benefícios são **esperados**. Não há evidência coletada de redução de perdas, economia financeira ou ganho de tempo nesta versão.

### Proposta de validação com o público

Convidar um responsável pelo laboratório para executar três tarefas: encontrar uma unidade disponível, registrar uma retirada e concluir a devolução. Medir tempo, conclusão sem ajuda e erros observados. Se possível, comparar com o procedimento atual usando o mesmo cenário e repetir as tarefas para reduzir o efeito de aprendizagem.

Perguntas úteis para uma entrevista breve:

1. Como vocês registram a retirada e a devolução hoje?
2. Quais informações são mais difíceis de localizar?
3. Como identificam atrasos e conferem acessórios?
4. Os campos e as situações do Circula correspondem à rotina real?

Essa etapa permanece pendente. Não devem ser incluídas respostas, participantes ou percentuais fictícios no relatório final.

## 5. Eixo 3 — Aplicação funcional e executável

### Requisitos funcionais

| Código | Requisito | Local no produto |
| --- | --- | --- |
| RF01 | Cadastrar e editar equipamento | Equipamentos |
| RF02 | Cadastrar e editar pessoa responsável | Pessoas |
| RF03 | Consultar disponibilidade e situação | Equipamentos e visão geral |
| RF04 | Registrar empréstimo com prazo | Novo empréstimo |
| RF05 | Registrar devolução e conferência | Devolver |
| RF06 | Consultar registros em atraso e histórico | Empréstimos |
| RF07 | Apresentar indicadores derivados do banco | Visão geral |
| RF08 | Exportar os empréstimos filtrados | Exportar CSV |

### Regras de negócio

- Cada equipamento corresponde a uma unidade física com patrimônio único.
- A matrícula ou identificação de uma pessoa deve ser única.
- Somente uma pessoa ativa e um equipamento disponível podem participar de um novo empréstimo.
- A retirada recebe automaticamente a data atual; o prazo deve ser hoje ou uma data futura.
- O equipamento pode ter apenas um empréstimo em aberto.
- O atraso começa no dia seguinte ao vencimento, considerando a data de Brasília.
- A devolução encerra a circulação e preserva o registro no histórico.
- Um cadastro com empréstimo pendente não pode ser desativado; um equipamento emprestado não pode ser colocado em manutenção.

### Execução e verificação

O README descreve a instalação e execução em Windows, Linux e macOS. O banco SQLite é criado automaticamente para avaliação local. A configuração por variável de ambiente permite utilizar PostgreSQL na futura hospedagem na Vercel.

A suíte automatizada verifica o ciclo completo, persistência, restrições, filtros, exportação, autenticação e formulários. Os procedimentos estão em [TESTES.md](TESTES.md). A publicação e a conexão a um PostgreSQL hospedado dependem das contas que serão configuradas posteriormente e ainda não foram verificadas.

## 6. Delimitação

Esta versão atende uma unidade escolar e uma área de gestão com senha compartilhada na hospedagem. Contas individuais, reservas futuras, multas, notificações, leitura de código de barras e assinatura de termos ficam fora do escopo.

O fluxo termina na confirmação da devolução. O responsável deve conferir o item fisicamente e registrar ocorrências. A aplicação não determina quem possui direito institucional ao empréstimo, nem substitui regras próprias de uma instituição.

## 7. Referências

BOURSCHEIT, Luiz Gustavo. **Aplicação para gerenciamento de empréstimos de equipamentos eletrônicos**. 2020. Trabalho de Conclusão de Curso (Especialização em Tecnologia Java) — Universidade Tecnológica Federal do Paraná, Pato Branco, 2020. Disponível no [repositório da UTFPR](https://repositorio.utfpr.edu.br/jspui/handle/1/25937). Acesso em: 16 nov. 2026. Consulta ao registro e resumo do trabalho.

MORAIS, Emanuel Bruno Duarte de; MELO, Taísso Reni de Souza; SOUSA, Reudismam Rolim de; GONÇALVES, Samara Martins Nascimento. **Uma arquitetura de sistema de empréstimos de materiais para a UFERSA**. Temática, v. 21, n. 7, p. 78–95, 2025. [DOI: 10.22478/ufpb.1807-8931.2025v21n7.74481](https://doi.org/10.22478/ufpb.1807-8931.2025v21n7.74481). Acesso em: 16 nov. 2026. Consulta ao resumo e aos metadados do artigo.

UNIVERSIDADE FEDERAL DE ALFENAS. Sistema de Bibliotecas. **Empréstimo**. [Página institucional](https://www.unifal-mg.edu.br/bibliotecas/circulacao-de-materiais/). Acesso em: 16 nov. 2026.
