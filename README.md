# xlsform-validator

[![Testes](https://github.com/agdala/xlsform-validator/actions/workflows/testes.yml/badge.svg)](https://github.com/agdala/xlsform-validator/actions/workflows/testes.yml)
[![Versão web](https://github.com/agdala/xlsform-validator/actions/workflows/publicar-web.yml/badge.svg)](https://agdala.github.io/xlsform-validator/)
[![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)](LICENSE)

Valida formulários XLSForm contra um padrão de qualidade e governança de dados **antes** de irem a
campo, e gera um relatório claro do que corrigir, com aba, linha e sugestão.

**Compatível com as plataformas que usam o padrão XLSForm:** KoboToolbox, ODK, SurveyCTO, Ona e
ArcGIS Survey123 (veja a seção de limitações sobre recursos exclusivos de cada plataforma).

### ▶ Use agora, sem instalar nada: **[agdala.github.io/xlsform-validator](https://agdala.github.io/xlsform-validator/)**

Arraste a planilha do formulário e veja o resultado. Se houver erros, baixe a **sua planilha
anotada**, com cada problema marcado na célula onde está. Quando o formulário for aprovado, baixe o
**formulário pronto para publicar**. O arquivo é processado no seu navegador e **não é enviado a
nenhum servidor**.

---

## 1. O problema

Em operações de coleta de dados, especialmente em contexto humanitário, é comum que cada equipe
monte o próprio formulário no Excel ou no Formbuilder do Kobo. Sem uma checagem padronizada:

- **erros só aparecem no tratamento dos dados**, quando a coleta já terminou e não dá para voltar a
  campo: idades de 250 anos, datas de chegada no futuro, "nenhuma necessidade" marcada junto com
  "alimentação", variáveis com acento que quebram o script de análise;
- **critérios de proteção ficam de fora**: entrevista que segue mesmo sem consentimento, coleta de
  CPF e telefone sem justificativa, perguntas sobre violência sem a opção "prefiro não responder";
- **resultados não podem ser comparados**: cada equipe usa uma lista de sexo e faixas etárias
  diferentes, e os dados não somam;
- **a revisão depende de uma pessoa experiente** olhando planilha por planilha, o que não escala e
  não deixa registro.

O custo de corrigir um formulário antes da coleta é minutos. Depois da coleta, é limpeza manual,
perda de dados ou uma nova rodada de campo.

## 2. Como a ferramenta resolve

```
formulario.xlsx ──► leitura (openpyxl, com nº real das linhas)
                         │
                         ├─► 33 regras de qualidade e governança (rules.yaml)
                         ├─► conversão oficial pyxform (TEC-01/02)
                         └─► ODK Validate, opcional (TEC-03)
                         │
                         ▼
          relatório Markdown + JSON  ──►  código de saída 0 / 1 / 2
                         │
                         ▼
     ┌───────────────────┬────────────────────┬──────────────────────────┐
     │ Versão web        │ Linha de comando   │ GitHub Action            │
     │ quem cria o       │ analistas e        │ governança: comentário   │
     │ formulário        │ automações         │ no PR e bloqueio do merge│
     │ + planilha anotada│ + --anotar         │ se houver erro           │
     └───────────────────┴────────────────────┴──────────────────────────┘
```

- **Padrão explícito e versionado.** As regras ficam em um YAML com ID, severidade e o motivo de
  existirem. O padrão vira um documento que a equipe discute e aprova, não conhecimento tácito.
- **Relatório acionável.** Cada problema traz aba, linha da planilha e, quando possível, a correção
  pronta (`"crime de odio" → crime_de_odio`, `constraint: . >= 0 and . <= 120`).
- **Revisão automática no fluxo de trabalho.** Formulários ficam na pasta `forms/` do repositório;
  todo pull request que adiciona ou altera um formulário é validado e recebe o relatório como
  comentário.
- **Correção onde o problema está.** A planilha anotada devolve o próprio arquivo do usuário com as
  linhas coloridas, um comentário em cada célula com problema e uma aba de resumo com links. Quem
  não é técnico não precisa interpretar "aba survey, linha 12".
- **Dois públicos, o mesmo padrão.** A versão web atende quem monta o formulário (autoatendimento,
  sem instalar nada). A GitHub Action atende a equipe de governança (controle central). As duas
  usam exatamente as mesmas regras.
- **Erro x aviso.** Erros bloqueiam (código de saída 1); avisos orientam sem travar a equipe.

## 3. Regras

São 36 regras em 11 grupos. As severidades e parâmetros abaixo são o padrão e podem ser alterados
(seção 6).

**Estrutura**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| EST-01 | erro | As abas survey e choices existem (choices só é exigida se houver perguntas de múltipla escolha). | Sem essas abas, com o nome exato em minúsculas, o KoboToolbox e o ODK não conseguem carregar o formulário. |
| EST-02 | erro | A aba settings existe. | É na settings que ficam o identificador e a versão do formulário. A especificação a trata como opcional, mas sem ela o form_id passa a depender do nome do arquivo e as versões não ficam rastreáveis. |
| EST-03 | erro | A aba survey tem as colunas type, name e label (ou label::idioma). | São as colunas obrigatórias da especificação XLSForm; sem elas o formulário não é convertido. |
| EST-04 | erro | A aba choices tem as colunas list_name (ou "list name"), name e label. | Sem essas colunas as listas de opções não são associadas às perguntas. |
| EST-05 | erro | A aba settings tem form_id e version preenchidos. | O form_id identifica o formulário no servidor e a version distingue os dados coletados com cada revisão. Sem eles, dados de versões diferentes se misturam e não é possível saber qual pergunta cada pessoa viu. |
| EST-06 | aviso | A version segue o padrão aaaammddrr (data + número da revisão). | Um padrão único permite ordenar versões e saber quando cada uma foi publicada. |
| EST-07 | erro | Toda pergunta tem label (metadados, calculate, hidden e grupos são exceção). | Uma pergunta sem texto aparece em branco para o enumerador, que vai improvisar a pergunta. |

**Nomes de variáveis**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| NOM-01 | erro | Os nomes das perguntas são únicos. | Dois campos com o mesmo nome viram a mesma coluna na base; um sobrescreve o outro ou o formulário não converte. |
| NOM-02 | erro | Os nomes estão em snake_case (minúsculas, números e "_", começando por letra). | Nomes padronizados evitam erros em scripts de análise (R, Python, Stata, Power BI), que diferenciam maiúsculas e minúsculas e tratam hífen e ponto de forma especial. |
| NOM-03 | erro | Os nomes não têm acentos, cedilha nem caracteres especiais. | Acentos em nomes de colunas quebram importações com codificação diferente e geram nomes ilegíveis na exportação. |
| NOM-04 | aviso | Os nomes respeitam o tamanho máximo. | Nomes longos são truncados em ferramentas como Stata e SPSS (limite de 32 caracteres) e dificultam a leitura da base. |

**Listas de opções**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| OPC-01 | erro | Toda lista usada em select_one, select_multiple ou rank existe na aba choices. | Uma lista inexistente impede a conversão do formulário ou deixa a pergunta sem opções. |
| OPC-02 | erro | Não há opções com o mesmo código dentro de uma lista (respeita allow_choice_duplicates). | Duas opções com o mesmo código ficam impossíveis de distinguir na análise. |
| OPC-03 | aviso | Não há listas órfãs (definidas e nunca usadas). | Listas órfãs costumam indicar uma pergunta apagada ou com o nome da lista digitado errado. |
| OPC-04 | erro | Os códigos (coluna name) das opções de listas usadas em select_multiple não têm espaço. O label pode ter várias palavras. | Em select_multiple as respostas marcadas são gravadas em um único campo, separadas por espaço (padrão XForms). Um código com espaço fica impossível de separar das outras respostas. O Formbuilder do Kobo resolve isso trocando espaços por "_" no código. |
| OPC-05 | aviso | Em select_multiple, opções do tipo "nenhum", "não sofri" ou "não sabe" são exclusivas (constraint impede marcar outra junto). | Sem a restrição surgem respostas contraditórias, como "nenhuma necessidade" e "alimentação" ao mesmo tempo. |

**Lógica**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| LOG-01 | erro | Todo campo citado com ${...} em relevant, constraint, calculation e demais expressões existe no formulário. | Uma referência quebrada faz o formulário falhar na conversão ou esconder perguntas que deveriam aparecer. |
| LOG-02 | aviso | Toda constraint tem constraint_message. | Sem mensagem, o enumerador vê um erro genérico em campo e não sabe o que corrigir. |

**Validações**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| VAL-01 | erro | Campos de idade têm constraint com limite inferior (>= 0) e superior plausível. | Idades como 250 ou -3 são erros de digitação comuns que só aparecem na limpeza dos dados. |
| VAL-02 | erro | Campos de data têm constraint que impede datas futuras. | Datas de eventos passados (chegada, nascimento) no futuro são erros de digitação que distorcem tempos e idades. |
| VAL-03 | aviso | Campos numéricos (integer, decimal) têm limites na constraint. | Sem limites, valores como 999 pessoas na família passam direto e distorcem médias e totais. |

**Metadados de coleta**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| MET-01 | erro | Os metadados start, end e today estão no formulário. | Eles permitem medir a duração das entrevistas e detectar formulários preenchidos rápido demais ou fora do período de coleta. |

**Consentimento**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| CON-01 | erro | Existe uma pergunta de consentimento (select_one com nome que indique consentimento). | Coletar dados sem consentimento informado viola princípios de proteção e a LGPD. |
| CON-02 | erro | O consentimento está entre as primeiras perguntas (metadados, notas e cálculos não contam). | Nenhuma informação sobre a pessoa pode ser coletada antes de ela concordar em participar. |
| CON-03 | erro | Todas as perguntas após o consentimento dependem dele (relevant próprio ou do grupo), encerrando a entrevista se a resposta for "não". | Se a pessoa recusar e as perguntas continuarem aparecendo, o enumerador pode seguir com a entrevista sem consentimento. |

**Proteção de dados (LGPD)**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| LGPD-01 | aviso | Sinaliza campos que parecem conter dado pessoal direto (nome, documento, telefone, endereço, e-mail) e ainda não foram confirmados na coluna dado_pessoal. | A LGPD exige minimização: só coletar o dado pessoal indispensável. A detecção é por palavras-chave; use a coluna dado_pessoal (sim/nao) para confirmar ou descartar. |
| LGPD-02 | erro | Todo campo com dado pessoal tem justificativa documentada na coluna justificativa_dados_pessoais. | A justificativa registra finalidade e base legal (LGPD, arts. 6º e 7º) e obriga a equipe a decidir conscientemente se o dado é necessário. |
| LGPD-03 | aviso | Perguntas de múltipla escolha sobre temas sensíveis oferecem a opção "prefiro não responder". | Violência, saúde, orientação sexual, raça e religião são dados pessoais sensíveis (LGPD, art. 11). Forçar a resposta gera dados falsos e pode expor a pessoa a risco. |

**Desagregação**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| DES-01 | erro | Existe pergunta de sexo com a lista padronizada. | Sem desagregação por sexo não é possível identificar necessidades e riscos diferentes entre mulheres e homens. |
| DES-02 | erro | Existe faixa etária, perguntada com lista padronizada ou calculada a partir da idade. | Faixas etárias padronizadas permitem comparar resultados entre coletas e somar dados de diferentes equipes. |

**Idiomas**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| IDI-01 | erro | Se houver colunas label::idioma, todos os labels estão preenchidos em todos os idiomas (survey e choices). | Uma tradução faltando aparece em branco ou no idioma errado para quem responde, e o enumerador improvisa a tradução. |
| IDI-02 | aviso | Hints e mensagens de constraint também estão traduzidos em todos os idiomas. | Instruções e mensagens de erro sem tradução levam a respostas inconsistentes entre idiomas. |
| IDI-03 | aviso | Em formulários com mais de um idioma, default_language está definido na settings. | Sem idioma padrão, o aplicativo pode abrir o formulário em um idioma que o enumerador não domina. |

**Validação técnica (pyxform)**

| ID | Severidade | O que verifica | Por que importa |
|---|---|---|---|
| TEC-01 | erro | O formulário é convertido sem erros pelo pyxform, o conversor oficial usado pelo KoboToolbox e pelo ODK. | Se o pyxform não converte, o formulário não pode ser publicado. |
| TEC-02 | aviso | Avisos emitidos pelo pyxform durante a conversão. | Os avisos apontam problemas que não impedem a publicação, mas costumam gerar comportamento inesperado em campo. |
| TEC-03 | erro | O XForm gerado passa no ODK Validate (requer Java; ative com --odk-validate). *(desligada por padrão)* | O ODK Validate testa as expressões como o aplicativo de coleta vai executá-las, pegando erros que a conversão não vê. |

### Por que o código da opção não pode ter espaço, mas o label pode (OPC-04)

Cada opção tem um **label** (o texto que a pessoa vê, com quantas palavras forem necessárias) e
um **name** (o código gravado na base). Em `select_multiple`, as opções marcadas são gravadas em
um único campo **separadas por espaço**, pelo padrão XForms usado por ODK, Enketo e Kobo:

| list_name | name (código) | label (tela) |
|---|---|---|
| tipos_violencia | nao_sofri | Não sofri |
| tipos_violencia | violencia_baseada_em_genero | Violência baseada em gênero |
| tipos_violencia | crime_de_odio | Crime de ódio |

Resposta gravada: `violencia_baseada_em_genero crime_de_odio`. Se o código fosse
`crime de odio`, seria impossível saber onde termina cada opção. Por isso o Formbuilder do Kobo
troca espaços por `_` ao gerar o código, e é essa a correção que o relatório sugere.

## 4. Exemplo: relatório do formulário ruim

A pasta [`examples/`](examples) tem dois formulários **fictícios** de avaliação de necessidades em
um abrigo temporário, gerados por [`scripts/build_examples.py`](scripts/build_examples.py):

| Arquivo | Resultado |
|---|---|
| [`abrigo_bom.xlsx`](examples/abrigo_bom.xlsx) | ✅ Aprovado, 0 erros e 0 avisos (inclusive no ODK Validate). Bilíngue (pt/es), com consentimento, LGPD e desagregação. |
| [`abrigo_ruim.xlsx`](examples/abrigo_ruim.xlsx) | ❌ Reprovado, com erros comuns de formulários montados sem padrão. |

Comando:

```bash
xlsform-validator examples/abrigo_ruim.xlsx
```

**Arquivo:** `examples/abrigo_ruim.xlsx`

**Status:** ❌ Reprovado

| Erros | Avisos | Regras verificadas | Regras com problema |
|---:|---:|---:|---:|
| 26 | 11 | 35 | 26 |

**Resumo por regra**

| Regra | Severidade | Ocorrências | Descrição |
|---|---|---:|---|
| CON-01 | ❌ erro | 1 | Existe uma pergunta de consentimento (select_one com nome que indique consentimento). |
| DES-01 | ❌ erro | 1 | Existe pergunta de sexo com a lista padronizada. |
| DES-02 | ❌ erro | 1 | Existe faixa etária, perguntada com lista padronizada ou calculada a partir da idade. |
| EST-05 | ❌ erro | 1 | A aba settings tem form_id e version preenchidos. |
| EST-07 | ❌ erro | 1 | Toda pergunta tem label (metadados, calculate, hidden e grupos são exceção). |
| IDI-01 | ❌ erro | 6 | Se houver colunas label::idioma, todos os labels estão preenchidos em todos os idiomas (survey e choices). |
| LGPD-02 | ❌ erro | 3 | Todo campo com dado pessoal tem justificativa documentada na coluna justificativa_dados_pessoais. |
| LOG-01 | ❌ erro | 1 | Todo campo citado com ${...} em relevant, constraint, calculation e demais expressões existe no formulário. |
| MET-01 | ❌ erro | 2 | Os metadados start, end e today estão no formulário. |
| NOM-01 | ❌ erro | 1 | Os nomes das perguntas são únicos. |
| NOM-02 | ❌ erro | 1 | Os nomes estão em snake_case (minúsculas, números e "_", começando por letra). |
| NOM-03 | ❌ erro | 1 | Os nomes não têm acentos, cedilha nem caracteres especiais. |
| OPC-01 | ❌ erro | 1 | Toda lista usada em select_one, select_multiple ou rank existe na aba choices. |
| OPC-02 | ❌ erro | 1 | Não há opções com o mesmo código dentro de uma lista (respeita allow_choice_duplicates). |
| OPC-04 | ❌ erro | 1 | Os códigos (coluna name) das opções de listas usadas em select_multiple não têm espaço. O label pode ter várias palavras. |
| TEC-01 | ❌ erro | 1 | O formulário é convertido sem erros pelo pyxform, o conversor oficial usado pelo KoboToolbox e pelo ODK. |
| VAL-01 | ❌ erro | 1 | Campos de idade têm constraint com limite inferior (>= 0) e superior plausível. |
| VAL-02 | ❌ erro | 1 | Campos de data têm constraint que impede datas futuras. |
| IDI-03 | ⚠️ aviso | 1 | Em formulários com mais de um idioma, default_language está definido na settings. |
| LGPD-01 | ⚠️ aviso | 3 | Sinaliza campos que parecem conter dado pessoal direto (nome, documento, telefone, endereço, e-mail) e ainda não foram confirmados na coluna dado_pessoal. |
| LGPD-03 | ⚠️ aviso | 1 | Perguntas de múltipla escolha sobre temas sensíveis oferecem a opção "prefiro não responder". |
| LOG-02 | ⚠️ aviso | 2 | Toda constraint tem constraint_message. |
| NOM-04 | ⚠️ aviso | 1 | Os nomes respeitam o tamanho máximo. |
| OPC-03 | ⚠️ aviso | 1 | Não há listas órfãs (definidas e nunca usadas). |
| OPC-05 | ⚠️ aviso | 1 | Em select_multiple, opções do tipo "nenhum", "não sofri" ou "não sabe" são exclusivas (constraint impede marcar outra junto). |
| VAL-03 | ⚠️ aviso | 1 | Campos numéricos (integer, decimal) têm limites na constraint. |

<details>
<summary><b>Ver o relatório completo</b> (também em <a href="examples/relatorio_abrigo_ruim.md">examples/relatorio_abrigo_ruim.md</a> e <a href="examples/relatorio_abrigo_ruim.json">.json</a>)</summary>

**Arquivo:** `examples/abrigo_ruim.xlsx`

**Status:** ❌ Reprovado

| Erros | Avisos | Regras verificadas | Regras com problema |
|---:|---:|---:|---:|
| 26 | 11 | 35 | 26 |

#### Resumo por regra

| Regra | Severidade | Ocorrências | Descrição |
|---|---|---:|---|
| CON-01 | ❌ erro | 1 | Existe uma pergunta de consentimento (select_one com nome que indique consentimento). |
| DES-01 | ❌ erro | 1 | Existe pergunta de sexo com a lista padronizada. |
| DES-02 | ❌ erro | 1 | Existe faixa etária, perguntada com lista padronizada ou calculada a partir da idade. |
| EST-05 | ❌ erro | 1 | A aba settings tem form_id e version preenchidos. |
| EST-07 | ❌ erro | 1 | Toda pergunta tem label (metadados, calculate, hidden e grupos são exceção). |
| IDI-01 | ❌ erro | 6 | Se houver colunas label::idioma, todos os labels estão preenchidos em todos os idiomas (survey e choices). |
| LGPD-02 | ❌ erro | 3 | Todo campo com dado pessoal tem justificativa documentada na coluna justificativa_dados_pessoais. |
| LOG-01 | ❌ erro | 1 | Todo campo citado com ${...} em relevant, constraint, calculation e demais expressões existe no formulário. |
| MET-01 | ❌ erro | 2 | Os metadados start, end e today estão no formulário. |
| NOM-01 | ❌ erro | 1 | Os nomes das perguntas são únicos. |
| NOM-02 | ❌ erro | 1 | Os nomes estão em snake_case (minúsculas, números e "_", começando por letra). |
| NOM-03 | ❌ erro | 1 | Os nomes não têm acentos, cedilha nem caracteres especiais. |
| OPC-01 | ❌ erro | 1 | Toda lista usada em select_one, select_multiple ou rank existe na aba choices. |
| OPC-02 | ❌ erro | 1 | Não há opções com o mesmo código dentro de uma lista (respeita allow_choice_duplicates). |
| OPC-04 | ❌ erro | 1 | Os códigos (coluna name) das opções de listas usadas em select_multiple não têm espaço. O label pode ter várias palavras. |
| TEC-01 | ❌ erro | 1 | O formulário é convertido sem erros pelo pyxform, o conversor oficial usado pelo KoboToolbox e pelo ODK. |
| VAL-01 | ❌ erro | 1 | Campos de idade têm constraint com limite inferior (>= 0) e superior plausível. |
| VAL-02 | ❌ erro | 1 | Campos de data têm constraint que impede datas futuras. |
| IDI-03 | ⚠️ aviso | 1 | Em formulários com mais de um idioma, default_language está definido na settings. |
| LGPD-01 | ⚠️ aviso | 3 | Sinaliza campos que parecem conter dado pessoal direto (nome, documento, telefone, endereço, e-mail) e ainda não foram confirmados na coluna dado_pessoal. |
| LGPD-03 | ⚠️ aviso | 1 | Perguntas de múltipla escolha sobre temas sensíveis oferecem a opção "prefiro não responder". |
| LOG-02 | ⚠️ aviso | 2 | Toda constraint tem constraint_message. |
| NOM-04 | ⚠️ aviso | 1 | Os nomes respeitam o tamanho máximo. |
| OPC-03 | ⚠️ aviso | 1 | Não há listas órfãs (definidas e nunca usadas). |
| OPC-05 | ⚠️ aviso | 1 | Em select_multiple, opções do tipo "nenhum", "não sofri" ou "não sabe" são exclusivas (constraint impede marcar outra junto). |
| VAL-03 | ⚠️ aviso | 1 | Campos numéricos (integer, decimal) têm limites na constraint. |

#### O que corrigir

**❌ CON-01 · Existe uma pergunta de consentimento (select_one com nome que indique consentimento).**

*Por que importa:* Coletar dados sem consentimento informado viola princípios de proteção e a LGPD.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | - | Não há pergunta de consentimento (select_one com nome que indique consentimento). | Adicione no início: type = select_one sim_nao, name = consentimento. |

**❌ DES-01 · Existe pergunta de sexo com a lista padronizada.**

*Por que importa:* Sem desagregação por sexo não é possível identificar necessidades e riscos diferentes entre mulheres e homens.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 8 | A lista 'sexo' da pergunta 'sexo' não segue o padrão: faltam os códigos feminino, masculino. | Use a lista padrão com os códigos: feminino, masculino. |

**❌ DES-02 · Existe faixa etária, perguntada com lista padronizada ou calculada a partir da idade.**

*Por que importa:* Faixas etárias padronizadas permitem comparar resultados entre coletas e somar dados de diferentes equipes.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | - | Não há faixa etária: nem pergunta com lista padronizada, nem calculate a partir da idade. | Adicione um calculate 'faixa_etaria' a partir do campo de idade, nas faixas 0_4, 5_11, 12_17, 18_59, 60_mais. |

**❌ EST-05 · A aba settings tem form_id e version preenchidos.**

*Por que importa:* O form_id identifica o formulário no servidor e a version distingue os dados coletados com cada revisão. Sem eles, dados de versões diferentes se misturam e não é possível saber qual pergunta cada pessoa viu.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| settings | 2 | O campo 'version' não está preenchido na aba 'settings'. | Crie a coluna version com a data e a revisão, ex.: 2026110201. |

**❌ EST-07 · Toda pergunta tem label (metadados, calculate, hidden e grupos são exceção).**

*Por que importa:* Uma pergunta sem texto aparece em branco para o enumerador, que vai improvisar a pergunta.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 15 | A pergunta 'observacoes' (tipo text) não tem label. | Escreva o texto da pergunta exatamente como deve ser lido. |

**❌ IDI-01 · Se houver colunas label::idioma, todos os labels estão preenchidos em todos os idiomas (survey e choices).**

*Por que importa:* Uma tradução faltando aparece em branco ou no idioma errado para quem responde, e o enumerador improvisa a tradução.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 3 | 'NomeCompleto': coluna label sem tradução para Español (es). | Preencha a(s) coluna(s): label::Español (es). |
| survey | 10 | 'pessoas_família': coluna label sem tradução para Español (es). | Preencha a(s) coluna(s): label::Español (es). |
| survey | 11 | 'violencias_sofridas': coluna label sem tradução para Español (es). | Preencha a(s) coluna(s): label::Español (es). |
| survey | 12 | 'recebe_auxilio': coluna label sem tradução para Español (es). | Preencha a(s) coluna(s): label::Español (es). |
| survey | 14 | 'abrigo': coluna label sem tradução para Español (es). | Preencha a(s) coluna(s): label::Español (es). |
| choices | 9 | 'racismo_estrutural': coluna label sem tradução para Español (es). | Preencha a(s) coluna(s): label::Español (es). |

**❌ LGPD-02 · Todo campo com dado pessoal tem justificativa documentada na coluna justificativa_dados_pessoais.**

*Por que importa:* A justificativa registra finalidade e base legal (LGPD, arts. 6º e 7º) e obriga a equipe a decidir conscientemente se o dado é necessário.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 3 | O campo 'NomeCompleto' coleta dado pessoal sem justificativa documentada. | Preencha a coluna 'justificativa_dados_pessoais' com a finalidade e a base legal (ex.: 'Contato para encaminhamento; consentimento'). |
| survey | 4 | O campo 'cpf' coleta dado pessoal sem justificativa documentada. | Preencha a coluna 'justificativa_dados_pessoais' com a finalidade e a base legal (ex.: 'Contato para encaminhamento; consentimento'). |
| survey | 5 | O campo 'endereco_anterior' coleta dado pessoal sem justificativa documentada. | Preencha a coluna 'justificativa_dados_pessoais' com a finalidade e a base legal (ex.: 'Contato para encaminhamento; consentimento'). |

**❌ LOG-01 · Todo campo citado com ${...} em relevant, constraint, calculation e demais expressões existe no formulário.**

*Por que importa:* Uma referência quebrada faz o formulário falhar na conversão ou esconder perguntas que deveriam aparecer.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 12 | A coluna 'relevant' cita ${renda_familar}, mas não existe pergunta com esse nome. | - |

**❌ MET-01 · Os metadados start, end e today estão no formulário.**

*Por que importa:* Eles permitem medir a duração das entrevistas e detectar formulários preenchidos rápido demais ou fora do período de coleta.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | - | O metadado 'start' não está no formulário. | Adicione uma linha com type = start e name = start. |
| survey | - | O metadado 'end' não está no formulário. | Adicione uma linha com type = end e name = end. |

**❌ NOM-01 · Os nomes das perguntas são únicos.**

*Por que importa:* Dois campos com o mesmo nome viram a mesma coluna na base; um sobrescreve o outro ou o formulário não converte.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 14 | O nome 'abrigo' já foi usado na linha 6. | Dê um nome diferente para cada pergunta. |

**❌ NOM-02 · Os nomes estão em snake_case (minúsculas, números e "_", começando por letra).**

*Por que importa:* Nomes padronizados evitam erros em scripts de análise (R, Python, Stata, Power BI), que diferenciam maiúsculas e minúsculas e tratam hífen e ponto de forma especial.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 3 | O nome 'NomeCompleto' não está em snake_case (minúsculas, números e '_', começando por letra). | Sugestão: nome_completo |

**❌ NOM-03 · Os nomes não têm acentos, cedilha nem caracteres especiais.**

*Por que importa:* Acentos em nomes de colunas quebram importações com codificação diferente e geram nomes ilegíveis na exportação.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 10 | O nome 'pessoas_família' tem acento, cedilha ou outro caractere especial. | Sugestão: pessoas_familia |

**❌ OPC-01 · Toda lista usada em select_one, select_multiple ou rank existe na aba choices.**

*Por que importa:* Uma lista inexistente impede a conversão do formulário ou deixa a pergunta sem opções.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 12 | A pergunta 'recebe_auxilio' usa a lista 'sim_nao', que não existe na aba 'choices'. | Crie a lista na aba 'choices' ou corrija o nome dela na coluna type. |

**❌ OPC-02 · Não há opções com o mesmo código dentro de uma lista (respeita allow_choice_duplicates).**

*Por que importa:* Duas opções com o mesmo código ficam impossíveis de distinguir na análise.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| choices | 3 | A opção 'abrigo_a' aparece duas vezes na lista 'abrigos' (primeira vez na linha 2). | Dê um código diferente para cada opção da lista. |

**❌ OPC-04 · Os códigos (coluna name) das opções de listas usadas em select_multiple não têm espaço. O label pode ter várias palavras.**

*Por que importa:* Em select_multiple as respostas marcadas são gravadas em um único campo, separadas por espaço (padrão XForms). Um código com espaço fica impossível de separar das outras respostas. O Formbuilder do Kobo resolve isso trocando espaços por "_" no código.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| choices | 8 | O código 'crime de odio' da lista 'tipos_violencia' tem espaço. Em select_multiple o espaço separa as respostas marcadas, então o código precisa ser uma palavra só. O label pode ter quantas palavras quiser. | Sugestão de código: crime_de_odio |

**❌ TEC-01 · O formulário é convertido sem erros pelo pyxform, o conversor oficial usado pelo KoboToolbox e pelo ODK.**

*Por que importa:* Se o pyxform não converte, o formulário não pode ser publicado.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| choices | 3 | pyxform: Há duas opções com o mesmo código (coluna name) na mesma lista da aba 'choices'. | Mensagem original: [row : 3] On the 'choices' sheet, the 'name' value is invalid. Choice names must be unique for each choice list. If this is intentional, use the setting 'allow_choice_duplicates'. Learn more: https://xlsform.org/#choice-names. |

**❌ VAL-01 · Campos de idade têm constraint com limite inferior (>= 0) e superior plausível.**

*Por que importa:* Idades como 250 ou -3 são erros de digitação comuns que só aparecem na limpeza dos dados.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 9 | O campo de idade 'idade' não tem limite inferior e superior na constraint ('. >= 0'). | constraint: . >= 0 and . <= 120 |

**❌ VAL-02 · Campos de data têm constraint que impede datas futuras.**

*Por que importa:* Datas de eventos passados (chegada, nascimento) no futuro são erros de digitação que distorcem tempos e idades.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 7 | A data 'data_chegada' aceita datas no futuro. | constraint: . <= today()  (se a data puder ser futura, inclua o nome nas exceções da regra) |

**⚠️ IDI-03 · Em formulários com mais de um idioma, default_language está definido na settings.**

*Por que importa:* Sem idioma padrão, o aplicativo pode abrir o formulário em um idioma que o enumerador não domina.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| settings | 2 | O formulário tem mais de um idioma, mas 'default_language' não está definido na aba 'settings'. | Defina default_language, por exemplo: Português (pt). |

**⚠️ LGPD-01 · Sinaliza campos que parecem conter dado pessoal direto (nome, documento, telefone, endereço, e-mail) e ainda não foram confirmados na coluna dado_pessoal.**

*Por que importa:* A LGPD exige minimização: só coletar o dado pessoal indispensável. A detecção é por palavras-chave; use a coluna dado_pessoal (sim/nao) para confirmar ou descartar.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 3 | O campo 'NomeCompleto' parece coletar dado pessoal direto (nome contém 'nome'). | Confirme na coluna 'dado_pessoal': 'sim' se for dado pessoal indispensável, 'nao' se for falso positivo. |
| survey | 4 | O campo 'cpf' parece coletar dado pessoal direto (nome contém 'cpf'). | Confirme na coluna 'dado_pessoal': 'sim' se for dado pessoal indispensável, 'nao' se for falso positivo. |
| survey | 5 | O campo 'endereco_anterior' parece coletar dado pessoal direto (nome contém 'endereco'). | Confirme na coluna 'dado_pessoal': 'sim' se for dado pessoal indispensável, 'nao' se for falso positivo. |

**⚠️ LGPD-03 · Perguntas de múltipla escolha sobre temas sensíveis oferecem a opção "prefiro não responder".**

*Por que importa:* Violência, saúde, orientação sexual, raça e religião são dados pessoais sensíveis (LGPD, art. 11). Forçar a resposta gera dados falsos e pode expor a pessoa a risco.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 11 | A pergunta 'violencias_sofridas' trata de tema sensível e não oferece a opção de não responder. | Inclua na lista 'tipos_violencia' a opção prefiro_nao_responder. |

**⚠️ LOG-02 · Toda constraint tem constraint_message.**

*Por que importa:* Sem mensagem, o enumerador vê um erro genérico em campo e não sabe o que corrigir.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 9 | A pergunta 'idade' tem constraint, mas não tem constraint_message. | Explique em linguagem simples a regra '. >= 0', por exemplo: 'Informe um valor entre 0 e 20'. |
| survey | 13 | A pergunta 'quantidade_pessoas_com_necessidades_especificas' tem constraint, mas não tem constraint_message. | Explique em linguagem simples a regra '. >= 0 and . <= 20', por exemplo: 'Informe um valor entre 0 e 20'. |

**⚠️ NOM-04 · Os nomes respeitam o tamanho máximo.**

*Por que importa:* Nomes longos são truncados em ferramentas como Stata e SPSS (limite de 32 caracteres) e dificultam a leitura da base.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 13 | O nome 'quantidade_pessoas_com_necessidades_especificas' tem 47 caracteres (máximo: 32). | Abrevie o nome mantendo o sentido; o texto completo fica no label. |

**⚠️ OPC-03 · Não há listas órfãs (definidas e nunca usadas).**

*Por que importa:* Listas órfãs costumam indicar uma pergunta apagada ou com o nome da lista digitado errado.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| choices | 11 | A lista 'escolaridade' está definida, mas nenhuma pergunta a usa. | Remova a lista ou confira se alguma pergunta deveria usá-la. |

**⚠️ OPC-05 · Em select_multiple, opções do tipo "nenhum", "não sofri" ou "não sabe" são exclusivas (constraint impede marcar outra junto).**

*Por que importa:* Sem a restrição surgem respostas contraditórias, como "nenhuma necessidade" e "alimentação" ao mesmo tempo.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 11 | A pergunta 'violencias_sofridas' permite marcar 'nao_sofri' junto com outras opções. | constraint: not(selected(., 'nao_sofri') and count-selected(.) > 1) |

**⚠️ VAL-03 · Campos numéricos (integer, decimal) têm limites na constraint.**

*Por que importa:* Sem limites, valores como 999 pessoas na família passam direto e distorcem médias e totais.

| Aba | Linha | Problema | Como corrigir |
|---|---:|---|---|
| survey | 10 | O campo numérico 'pessoas_família' não tem limite na constraint. | Defina o intervalo plausível, por exemplo: . >= 1 and . <= 30 |

<sub>Gerado por xlsform-validator 0.1.0.</sub>

</details>

## 5. Como usar

### 5.1 No navegador (para quem monta o formulário)

1. Abra **[agdala.github.io/xlsform-validator](https://agdala.github.io/xlsform-validator/)**.
2. No KoboToolbox, abra o projeto, clique em **⋯** e depois em **Download XLS** (ou use a planilha que você já tem).
3. Arraste o arquivo `.xlsx` para a página.
4. Leia o resultado: **erros** precisam ser corrigidos, **avisos** são recomendações.
5. **Se houver erros:** clique em **Baixar planilha anotada**, corrija no Excel e valide de novo.
6. **Se for aprovado** (com ou sem avisos): clique em **Baixar formulário pronto para publicar** e
   suba o arquivo na sua plataforma.

O que cada resultado oferece para baixar:

| Resultado | Botão principal | Opções secundárias |
|---|---|---|
| ❌ Reprovado (há erros) | Planilha anotada | Relatório (.md), dados (.json) |
| ⚠️ Aprovado com avisos | Formulário pronto para publicar | Planilha anotada com os avisos, relatório, dados |
| ✅ Aprovado | Formulário pronto para publicar | Planilha anotada, relatório, dados |

O **formulário pronto para publicar** é o seu arquivo original, byte a byte, sem nenhuma alteração.
Se você enviar uma planilha que já tinha sido anotada antes, o validador remove a aba `validacao`,
os comentários e as cores que ele mesmo aplicou, sem mexer na formatação feita pela equipe.

Na planilha anotada:

| Elemento | Significado |
|---|---|
| Linha vermelha clara | A linha tem pelo menos um erro |
| Linha amarela clara | A linha tem só avisos |
| Célula em tom mais forte, com comentário | O ponto exato do problema; passe o mouse para ler o que corrigir |
| Aba `validacao` (primeira aba) | Lista de todos os problemas, com links para as células. Apague antes de publicar |

Exemplo: [`examples/abrigo_ruim_anotado.xlsx`](examples/abrigo_ruim_anotado.xlsx).

**Como funciona por dentro:** a página carrega o [Pyodide](https://pyodide.org) (Python compilado
para WebAssembly) e roda o mesmo pacote Python da linha de comando. Todos os arquivos são servidos
pelo próprio GitHub Pages, sem CDN externo. O teste automatizado da página verifica que **nenhuma
requisição sai do site** durante a validação. Na primeira visita o navegador baixa cerca de
18 MB (uma única vez; depois fica em cache) e o validador pode levar até 30 segundos para ficar
pronto. A página mostra o progresso por etapas (ambiente Python, conversor oficial do XLSForm,
regras) e só libera o envio de arquivos quando tudo está carregado.

**Para publicar a sua própria cópia:** em **Settings → Pages → Build and deployment → Source**,
escolha **GitHub Actions**. O workflow
[`publicar-web.yml`](.github/workflows/publicar-web.yml) monta o site, testa em um navegador real
e publica a cada merge na `main`. Para testar localmente:

```bash
python scripts/build_web.py
python -m http.server -d site 8000
```

### 5.2 Localmente (linha de comando)

Requisitos: Python 3.10+. Java 8+ só é necessário para o ODK Validate (opcional).

```bash
git clone https://github.com/agdala/xlsform-validator.git
cd xlsform-validator
pip install .
```

Validar um formulário (relatório Markdown na tela):

```bash
xlsform-validator caminho/do/formulario.xlsx
```

Validar vários formulários e gravar Markdown e JSON em uma pasta:

```bash
xlsform-validator forms/*.xlsx --formato md json --saida relatorios/
```

Incluir o ODK Validate:

```bash
xlsform-validator formulario.xlsx --odk-validate
```

| Opção | Efeito |
|---|---|
| `--formato md json` | Formato(s) do relatório (padrão: `md`) |
| `--saida PASTA` | Grava `relatorio.md` e/ou `relatorio.json` na pasta, em vez de imprimir |
| `--regras ARQUIVO.yaml` | Usa um padrão de regras personalizado |
| `--exportar-regras ARQUIVO.yaml` | Copia o padrão embutido para você editar |
| `--odk-validate` | Liga a regra TEC-03 (requer Java) |
| `--anotar` | Gera `<nome>_anotado.xlsx` com os problemas marcados nas células |

**Códigos de saída:** `0` aprovado (com ou sem avisos), `1` há pelo menos um erro, `2` arquivo
ilegível ou configuração inválida. Isso permite usar a ferramenta em qualquer pipeline de CI.

### 5.3 No GitHub (validação automática em pull requests)

O workflow [`.github/workflows/validar-formularios.yml`](.github/workflows/validar-formularios.yml):

1. roda em todo pull request e identifica os arquivos `.xlsx` adicionados ou alterados em `forms/`;
2. valida **só os arquivos novos ou alterados**, com ODK Validate;
3. publica o relatório como **um único comentário no PR**, atualizado a cada novo push;
4. grava o relatório no resumo do job e como artefato;
5. **falha o check** se houver erros, o que permite bloquear o merge via *branch protection*.

Fluxo da equipe:

```bash
git checkout -b novo-formulario
cp ~/Downloads/minha_avaliacao.xlsx forms/
git add forms/minha_avaliacao.xlsx
git commit -m "Adiciona formulário de avaliação"
git push -u origin novo-formulario
```

Depois é só abrir o PR, ler o comentário, corrigir e enviar de novo até o check ficar verde.

Para usar em outro repositório, copie o workflow e ajuste o passo de instalação para
`pip install git+https://github.com/agdala/xlsform-validator.git`.

## 6. Como personalizar as regras

```bash
xlsform-validator --exportar-regras minhas_regras.yaml
# edite o arquivo
xlsform-validator formulario.xlsx --regras minhas_regras.yaml
```

Cada regra no YAML:

```yaml
VAL-01:
  grupo: Validações
  descricao: Campos de idade têm constraint com limite inferior (>= 0) e superior plausível.
  severidade: erro            # erro | aviso
  por_que_importa: Idades como 250 ou -3 são erros de digitação comuns...
  ativa: true                 # false desliga a regra
  parametros:
    idade_maxima: 120
    padroes_idade: ['(^|_)idade($|_)', '(^|_)age($|_)', '(^|_)edad($|_)']
```

Ajustes comuns:

| Necessidade | Onde mudar |
|---|---|
| Rebaixar uma regra para aviso | `severidade: aviso` |
| Desligar uma regra | `ativa: false` |
| Usar outra lista padrão de sexo ou outras faixas etárias | `DES-01` / `DES-02` → `codigos_obrigatorios` |
| Exigir também `deviceid` ou `audit` | `MET-01` → `obrigatorios` |
| Reconhecer o consentimento com outro nome | `CON-0x` → `padroes_nome` |
| Ampliar as palavras que indicam dado pessoal | `LGPD-01` → `palavras_nome`, `padroes_label` |
| Permitir datas futuras em campos de agendamento | `VAL-02` → `excecoes` |
| Mudar o tamanho máximo de nomes | `NOM-04` → `tamanho_maximo` |

**Colunas extras usadas pelas regras de LGPD** (o KoboToolbox e o ODK ignoram colunas que não
conhecem, então elas podem ficar no formulário publicado):

| Coluna (aba survey) | Valores | Uso |
|---|---|---|
| `dado_pessoal` | `sim` / `nao` | Confirma um dado pessoal ou descarta um falso positivo da detecção automática |
| `justificativa_dados_pessoais` | texto | Finalidade e base legal da coleta do dado pessoal (mín. 15 caracteres) |

**Para criar uma regra nova:** escreva uma função em `src/xlsform_validator/rules/`, decore com
`@rule("XXX-01")`, adicione a entrada correspondente no `rules.yaml` e um teste em `tests/`. O
carregamento falha se houver regra no YAML sem implementação, o que evita regras "fantasma".

## 7. Decisões técnicas

| Decisão | Motivo |
|---|---|
| **Leitura própria da planilha com openpyxl**, em vez de usar só o pyxform | O pyxform para no primeiro erro e nem sempre informa a linha. Ler a planilha diretamente permite apontar a linha exata e rodar todas as regras mesmo quando o formulário não converte. |
| **pyxform como regra (TEC-01/02)**, não como etapa prévia | O relatório junta, no mesmo lugar, a validação oficial e a de governança. Mensagens do pyxform sem linha são localizadas pelo valor citado. |
| **ODK Validate opcional** | Exige Java e leva alguns segundos; na Action ele roda sempre, localmente só quando pedido. |
| **Regras em YAML + implementação registrada por ID** | Gestores ajustam severidade, parâmetros e justificativas sem programar; o código só muda para regras novas. |
| **Erro x aviso** | Nem todo desvio deve travar a coleta. Avisos cobrem boas práticas e detecções heurísticas, que podem ter falso positivo. |
| **Padrão mais rígido que a especificação**, de forma explícita | `settings` é opcional e nomes com maiúsculas, hífen ou ponto são válidos no XLSForm. As regras EST-02 e NOM-02 são escolhas de governança, e o YAML deixa isso documentado. |
| **Exemplos gerados por script** | Qualquer pessoa pode auditar o que há nos `.xlsx` e recriá-los; nenhum dado real é usado. |
| **Um comentário por PR, atualizado** | Evita poluir a conversa do PR com um comentário a cada push. |
| **Relatório em português, chaves do JSON em inglês** | O relatório é lido pela equipe; o JSON é consumido por outras ferramentas. |
| **Versão web com Python no navegador (Pyodide)**, em vez de reescrever as regras em JavaScript | Um único código de regras para web, terminal e CI: sem duplicar lógica nem testes. E o arquivo não sai do computador do usuário, o que é coerente com o tema de proteção de dados e facilita a adoção em organizações. |
| **Sem servidor e sem CDN externo** | Custo zero, nada para manter ou cair, e nenhuma terceira parte recebe dados ou metadados de uso. Pyodide e dependências são empacotados no build. |
| **Planilha anotada como saída principal da web** | O público da web não é técnico: ver a célula marcada no próprio Excel é mais rápido do que traduzir "aba, linha" de um relatório. |
| **Mensagens do pyxform traduzidas** | As mais comuns viram português simples; a original continua disponível para quem precisar. |
| **Teste ponta a ponta em navegador real no CI** | Garante que a página publicada funciona, cabe no celular e não faz requisições externas. |

Estrutura do código:

```
src/xlsform_validator/
  form.py        modelo do formulário e leitura do .xlsx
  engine.py      registro de regras, carga do YAML, execução
  rules/         uma implementação por grupo de regras
  rules.yaml     padrão de qualidade embutido
  report.py      relatórios Markdown e JSON, status e código de saída
  annotate.py    planilha anotada (cores, comentários e aba de resumo)
  pyxform_messages.py  tradução das mensagens do pyxform
  web.py         ponto de entrada da versão web
  cli.py         linha de comando
web/             página (HTML, CSS, JavaScript) e worker que roda o Python no navegador
tests/           89 testes pytest (cada regra tem casos que passam e que falham)
tests/web/       teste ponta a ponta da página (Playwright) e formulário de exemplo só com avisos
scripts/         gerador dos exemplos e montagem do site (build_web.py)
examples/        formulários fictícios e relatórios gerados
forms/           pasta monitorada pela GitHub Action
```

Para rodar os testes:

```bash
pip install ".[dev]"
pytest
```

## 8. Limitações

- **Detecção por palavras-chave é heurística.** Consentimento, idade, sexo, dado pessoal e temas
  sensíveis são reconhecidos pelo nome e pelo texto das perguntas. Isso gera falsos positivos (ex.:
  "nome do abrigo") e falsos negativos (ex.: um campo de CPF chamado `doc1`). A coluna
  `dado_pessoal` e os padrões no YAML reduzem o problema, mas **não substituem revisão humana** nem
  uma avaliação de impacto à proteção de dados.
- **A lógica não é executada.** A CON-03 verifica se as perguntas dependem do consentimento, mas
  não se a condição está certa (`= 'sim'` ou `= 'nao'`). A LOG-01 verifica se os campos citados
  existem, mas não a sintaxe da expressão; isso fica a cargo do pyxform e do ODK Validate.
- **Problemas de conteúdo ficam fora.** Opções que juntam dois conceitos ("xenofobia e
  homofobia"), perguntas duplas ou enviesadas e tradução incorreta (só a ausência é detectada)
  exigem revisão humana. Detectar o "e" no texto geraria falso positivo em "Água e saneamento".
- **Compatibilidade entre plataformas.** As regras e o conversor oficial (pyxform) seguem o padrão
  XLSForm comum ao KoboToolbox, ODK, SurveyCTO, Ona e ArcGIS Survey123. Recursos exclusivos de
  uma plataforma (por exemplo, funções próprias do SurveyCTO ou colunas específicas do Survey123)
  podem gerar avisos ou erros do conversor oficial, ou simplesmente não ser verificados. Teste
  sempre o formulário final na plataforma de destino.
- **A versão web não roda o ODK Validate** (exige Java) e usa o padrão de regras embutido. Para
  regras personalizadas ou ODK Validate, use a linha de comando ou a GitHub Action.
- **A planilha anotada é regravada pelo openpyxl.** Formatação comum é preservada, mas recursos
  avançados do Excel (macros, imagens, validação de dados com listas externas) podem se perder.
  Por isso ela serve para orientar a correção; para publicar, use o **formulário pronto**, que é o
  arquivo original sem alterações.
- **Só `.xlsx`.** O formato `.xls` antigo e formulários em Google Sheets precisam ser exportados
  para `.xlsx` antes.
- **Listas externas** (`select_one_from_file`, CSV anexos) não são verificadas.
- **PRs vindos de forks** não podem receber comentário (limitação de permissão do GitHub); nesse
  caso o relatório fica no resumo do job.
- **A conformidade com a LGPD não é garantida pela ferramenta.** Ela verifica sinais objetivos
  (justificativa registrada, opção de não responder, consentimento), mas finalidade, base legal,
  retenção e segurança da informação dependem de processos da organização.

## English summary

`xlsform-validator` is a Python CLI and GitHub Action that checks XLSForm
questionnaires (the standard used by KoboToolbox, ODK, SurveyCTO, Ona and ArcGIS Survey123) against a configurable data quality and
data governance standard *before* they go to the field. It runs 36 rules (structure, variable
naming, choice lists, skip logic, value constraints, collection metadata, informed consent,
personal data protection, sex and age disaggregation, translations) plus the official `pyxform`
conversion and, optionally, ODK Validate. It outputs a Markdown and JSON report pointing to the exact
sheet and row to fix, exits non-zero on errors, and comments the result on pull requests.
Rules live in a YAML file with severity and rationale, so teams can adapt the standard without
touching code. A **web version** runs the same Python validator entirely in the browser
(Pyodide, no server: the file never leaves the user's computer) and returns the user's own
spreadsheet with the problems highlighted and commented cell by cell, or, once the form passes,
a file ready to publish. All examples are fictitious.

## Projetos relacionados

Os quatro repositórios formam um ciclo de dados, da coleta ao monitoramento:

| Etapa | Projeto | O que faz | Publicado |
|---|---|---|---|
| 1. Coletar | **xlsform-validator** (este repositório) | Qualidade, consentimento e LGPD em formulários KoboToolbox/ODK | [versão web](https://agdala.github.io/xlsform-validator/) |
| 2. Transformar e publicar | [sismigra-analytics](https://github.com/agdala/sismigra-analytics) | Pipeline bronze/prata/ouro com Python, DuckDB e dbt, com controle de divulgação | [dbt docs](https://agdala.github.io/sismigra-analytics/) |
| 3. Integrar | [record-linkage-kit](https://github.com/agdala/record-linkage-kit) | Deduplicação e cruzamento de cadastros, com revisão humana e pseudonimização | [relatório](https://agdala.github.io/record-linkage-kit/) |
| 4. Monitorar | [monitoring-5w-kit](https://github.com/agdala/monitoring-5w-kit) | Relatos de parceiros, metas e dupla contagem | [relatório](https://agdala.github.io/monitoring-5w-kit/) |

Autoria: Agda Santos, com auxílio de ferramentas de IA.

## Licença

[MIT](LICENSE). Todos os formulários, abrigos e dados de exemplo são fictícios.
