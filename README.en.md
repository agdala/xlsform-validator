# xlsform-validator

[Português](README.md) | **English**

[![Testes](https://github.com/agdala/xlsform-validator/actions/workflows/testes.yml/badge.svg)](https://github.com/agdala/xlsform-validator/actions/workflows/testes.yml)
[![Versão web](https://github.com/agdala/xlsform-validator/actions/workflows/publicar-web.yml/badge.svg)](https://agdala.github.io/xlsform-validator/)
[![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)](LICENSE)

Validates XLSForm forms against a data quality and data governance standard **before** they go to
the field, and produces a clear report of what to fix, with sheet, row and suggestion.

**Compatible with the platforms that use the XLSForm standard:** KoboToolbox, ODK, SurveyCTO, Ona
and ArcGIS Survey123 (see the limitations section about features specific to each platform).

### ▶ Use it now, with nothing to install: **[agdala.github.io/xlsform-validator](https://agdala.github.io/xlsform-validator/)**

Drag the form spreadsheet onto the page and see the result. If there are errors, download **your
annotated spreadsheet**, with each problem marked in the cell where it is. Once the form passes,
download the **form ready to publish**. The file is processed in your browser and **is not sent to
any server**.

> The web version, the reports and the rule descriptions are in Portuguese.

---

## 1. The problem

In data collection operations, especially in humanitarian settings, each team often builds its own
form in Excel or in the Kobo Formbuilder. Without a standardized check:

- **errors only show up during data processing**, when collection is over and there is no going
  back to the field: ages of 250 years, arrival dates in the future, "no needs" ticked together
  with "food", variable names with accents that break the analysis script;
- **protection criteria are left out**: interviews that continue even without consent, collection
  of CPF (Brazilian taxpayer ID) and phone numbers without justification, questions about violence
  without a "prefer not to answer" option;
- **results cannot be compared**: each team uses a different list for sex and age bands, and the
  data does not add up;
- **the review depends on an experienced person** checking spreadsheet by spreadsheet, which does
  not scale and leaves no record.

Fixing a form before collection costs minutes. After collection, it costs manual cleaning, data
loss or a new round of fieldwork.

## 2. How the tool solves it

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

_The diagram is kept as in the Portuguese README: the form is read with openpyxl (with the real row
numbers), goes through 33 quality and governance rules (rules.yaml), the official pyxform
conversion (TEC-01/02) and, optionally, ODK Validate (TEC-03); the result is a Markdown + JSON
report and an exit code 0 / 1 / 2, used by three channels: the web version (for whoever builds the
form, with the annotated spreadsheet), the command line (analysts and automations, with
`--anotar`) and the GitHub Action (governance: PR comment and merge blocking when there are errors)._

- **Explicit, versioned standard.** Rules live in a YAML file with ID, severity and the reason they
  exist. The standard becomes a document the team discusses and approves, not tacit knowledge.
- **Actionable report.** Each problem comes with sheet, spreadsheet row and, when possible, the
  ready-made fix (`"crime de odio" → crime_de_odio`, `constraint: . >= 0 and . <= 120`).
- **Automatic review in the workflow.** Forms live in the repository's `forms/` folder; every pull
  request that adds or changes a form is validated and receives the report as a comment.
- **Fix where the problem is.** The annotated spreadsheet returns the user's own file with the rows
  coloured, a comment on each cell with a problem and a summary sheet with links. Non-technical
  users do not need to interpret "survey sheet, row 12".
- **Two audiences, the same standard.** The web version serves whoever builds the form
  (self-service, nothing to install). The GitHub Action serves the governance team (central
  control). Both use exactly the same rules.
- **Error x warning.** Errors block (exit code 1); warnings guide without holding the team back.

## 3. Rules

There are 36 rules in 11 groups. The severities and parameters below are the default and can be
changed (section 6).

**Structure**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| EST-01 | error | The survey and choices sheets exist (choices is only required if there are multiple-choice questions). | Without these sheets, with the exact name in lower case, KoboToolbox and ODK cannot load the form. |
| EST-02 | error | The settings sheet exists. | The settings sheet holds the form identifier and version. The specification treats it as optional, but without it the form_id depends on the file name and versions cannot be traced. |
| EST-03 | error | The survey sheet has the type, name and label (or label::language) columns. | These are the mandatory columns of the XLSForm specification; without them the form is not converted. |
| EST-04 | error | The choices sheet has the list_name (or "list name"), name and label columns. | Without these columns the choice lists are not linked to the questions. |
| EST-05 | error | The settings sheet has form_id and version filled in. | The form_id identifies the form on the server and the version distinguishes the data collected with each revision. Without them, data from different versions gets mixed and it is impossible to know which question each person saw. |
| EST-06 | warning | The version follows the yyyymmddrr pattern (date + revision number). | A single pattern makes it possible to sort versions and know when each one was published. |
| EST-07 | error | Every question has a label (metadata, calculate, hidden and groups are exceptions). | A question without text appears blank to the enumerator, who will improvise the question. |

**Variable names**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| NOM-01 | error | Question names are unique. | Two fields with the same name become the same column in the dataset; one overwrites the other or the form does not convert. |
| NOM-02 | error | Names are in snake_case (lower case, digits and "_", starting with a letter). | Standardized names avoid errors in analysis scripts (R, Python, Stata, Power BI), which are case-sensitive and treat hyphens and dots in special ways. |
| NOM-03 | error | Names have no accents, cedillas or special characters. | Accents in column names break imports with a different encoding and produce unreadable names on export. |
| NOM-04 | warning | Names respect the maximum length. | Long names are truncated in tools such as Stata and SPSS (32-character limit) and make the dataset harder to read. |

**Choice lists**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| OPC-01 | error | Every list used in select_one, select_multiple or rank exists in the choices sheet. | A non-existent list prevents the form from converting or leaves the question without options. |
| OPC-02 | error | There are no options with the same code within a list (respects allow_choice_duplicates). | Two options with the same code are impossible to tell apart in the analysis. |
| OPC-03 | warning | There are no orphan lists (defined and never used). | Orphan lists usually indicate a deleted question or a mistyped list name. |
| OPC-04 | error | The codes (name column) of options in lists used in select_multiple have no spaces. The label can have several words. | In select_multiple the selected answers are stored in a single field, separated by spaces (XForms standard). A code with a space cannot be separated from the other answers. The Kobo Formbuilder handles this by replacing spaces with "_" in the code. |
| OPC-05 | warning | In select_multiple, options such as "none", "I did not experience" or "don't know" are exclusive (a constraint prevents ticking another one together). | Without the constraint, contradictory answers appear, such as "no needs" and "food" at the same time. |

**Logic**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| LOG-01 | error | Every field referenced with ${...} in relevant, constraint, calculation and other expressions exists in the form. | A broken reference makes the form fail to convert or hide questions that should appear. |
| LOG-02 | warning | Every constraint has a constraint_message. | Without a message, the enumerator sees a generic error in the field and does not know what to fix. |

**Validations**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| VAL-01 | error | Age fields have a constraint with a lower bound (>= 0) and a plausible upper bound. | Ages such as 250 or -3 are common typos that only show up during data cleaning. |
| VAL-02 | error | Date fields have a constraint that prevents future dates. | Dates of past events (arrival, birth) in the future are typos that distort durations and ages. |
| VAL-03 | warning | Numeric fields (integer, decimal) have bounds in the constraint. | Without bounds, values such as 999 people in the household go straight through and distort means and totals. |

**Collection metadata**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| MET-01 | error | The start, end and today metadata are in the form. | They make it possible to measure interview duration and detect forms filled in too quickly or outside the collection period. |

**Consent**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| CON-01 | error | There is a consent question (select_one with a name indicating consent). | Collecting data without informed consent violates protection principles and the LGPD (Brazil's General Data Protection Law). |
| CON-02 | error | Consent is among the first questions (metadata, notes and calculations do not count). | No information about the person can be collected before they agree to take part. |
| CON-03 | error | All questions after consent depend on it (own relevant or the group's), ending the interview if the answer is "no". | If the person refuses and the questions keep appearing, the enumerator may continue the interview without consent. |

**Data protection (LGPD)**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| LGPD-01 | warning | Flags fields that seem to contain direct personal data (name, document, phone, address, e-mail) and have not yet been confirmed in the dado_pessoal column. | The LGPD requires minimization: collect only the indispensable personal data. Detection is by keywords; use the dado_pessoal column (sim/nao) to confirm or dismiss. |
| LGPD-02 | error | Every field with personal data has a documented justification in the justificativa_dados_pessoais column. | The justification records purpose and legal basis (LGPD, arts. 6 and 7) and forces the team to decide consciously whether the data is necessary. |
| LGPD-03 | warning | Multiple-choice questions on sensitive topics offer a "prefer not to answer" option. | Violence, health, sexual orientation, race and religion are sensitive personal data (LGPD, art. 11). Forcing an answer produces false data and may put the person at risk. |

**Disaggregation**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| DES-01 | error | There is a sex question with the standardized list. | Without disaggregation by sex it is not possible to identify different needs and risks between women and men. |
| DES-02 | error | There is an age band, asked with a standardized list or calculated from age. | Standardized age bands make it possible to compare results across collections and add up data from different teams. |

**Languages**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| IDI-01 | error | If there are label::language columns, all labels are filled in for all languages (survey and choices). | A missing translation appears blank or in the wrong language for the respondent, and the enumerator improvises the translation. |
| IDI-02 | warning | Hints and constraint messages are also translated into all languages. | Untranslated instructions and error messages lead to inconsistent answers across languages. |
| IDI-03 | warning | In forms with more than one language, default_language is set in the settings sheet. | Without a default language, the app may open the form in a language the enumerator does not master. |

**Technical validation (pyxform)**

| ID | Severity | What it checks | Why it matters |
|---|---|---|---|
| TEC-01 | error | The form is converted without errors by pyxform, the official converter used by KoboToolbox and ODK. | If pyxform does not convert it, the form cannot be published. |
| TEC-02 | warning | Warnings issued by pyxform during conversion. | The warnings point to problems that do not prevent publication, but often cause unexpected behaviour in the field. |
| TEC-03 | error | The generated XForm passes ODK Validate (requires Java; enable with --odk-validate). *(off by default)* | ODK Validate tests the expressions the way the collection app will run them, catching errors the conversion does not see. |

### Why the option code cannot have spaces, but the label can (OPC-04)

Each option has a **label** (the text the person sees, with as many words as needed) and a
**name** (the code stored in the dataset). In `select_multiple`, the selected options are stored in
a single field **separated by spaces**, following the XForms standard used by ODK, Enketo and Kobo:

| list_name | name (code) | label (screen) |
|---|---|---|
| tipos_violencia | nao_sofri | Não sofri |
| tipos_violencia | violencia_baseada_em_genero | Violência baseada em gênero |
| tipos_violencia | crime_de_odio | Crime de ódio |

Stored answer: `violencia_baseada_em_genero crime_de_odio`. If the code were `crime de odio`, it
would be impossible to know where each option ends. That is why the Kobo Formbuilder replaces
spaces with `_` when generating the code, and that is the fix the report suggests.

## 4. Example: report for the bad form

The [`examples/`](examples) folder has two **fictitious** needs assessment forms for a temporary
shelter, generated by [`scripts/build_examples.py`](scripts/build_examples.py):

| File | Result |
|---|---|
| [`abrigo_bom.xlsx`](examples/abrigo_bom.xlsx) | ✅ Passed, 0 errors and 0 warnings (including ODK Validate). Bilingual (pt/es), with consent, LGPD and disaggregation. |
| [`abrigo_ruim.xlsx`](examples/abrigo_ruim.xlsx) | ❌ Failed, with errors common in forms built without a standard. |

Command:

```bash
xlsform-validator examples/abrigo_ruim.xlsx
```

The report below is the tool's output, reproduced exactly as generated (the tool writes its reports
in Portuguese). Main labels: *Arquivo* = file, *Reprovado* = failed, *Erros* = errors, *Avisos* =
warnings, *Regras verificadas* = rules checked, *Regras com problema* = rules with problems,
*Resumo por regra* = summary by rule, *Ocorrências* = occurrences, *O que corrigir* = what to fix,
*Aba* = sheet, *Linha* = row, *Problema* = problem, *Como corrigir* = how to fix.

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
<summary><b>See the full report</b> (also in <a href="examples/relatorio_abrigo_ruim.md">examples/relatorio_abrigo_ruim.md</a> and <a href="examples/relatorio_abrigo_ruim.json">.json</a>)</summary>

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

## 5. How to use

### 5.1 In the browser (for whoever builds the form)

1. Open **[agdala.github.io/xlsform-validator](https://agdala.github.io/xlsform-validator/)**.
2. In KoboToolbox, open the project, click **⋯** and then **Download XLS** (or use the spreadsheet you already have).
3. Drag the `.xlsx` file onto the page.
4. Read the result: **errors** must be fixed, **warnings** are recommendations.
5. **If there are errors:** click **Baixar planilha anotada** (download annotated spreadsheet), fix it in Excel and validate again.
6. **If it passes** (with or without warnings): click **Baixar formulário pronto para publicar**
   (download form ready to publish) and upload the file to your platform.

What each result offers for download:

| Result | Main button | Secondary options |
|---|---|---|
| ❌ Failed (there are errors) | Annotated spreadsheet | Report (.md), data (.json) |
| ⚠️ Passed with warnings | Form ready to publish | Annotated spreadsheet with the warnings, report, data |
| ✅ Passed | Form ready to publish | Annotated spreadsheet, report, data |

The **form ready to publish** is your original file, byte for byte, with no changes at all. If you
upload a spreadsheet that had already been annotated, the validator removes the `validacao` sheet,
the comments and the colours it applied itself, without touching the formatting done by the team.

In the annotated spreadsheet:

| Element | Meaning |
|---|---|
| Light red row | The row has at least one error |
| Light yellow row | The row only has warnings |
| Cell in a stronger shade, with a comment | The exact spot of the problem; hover over it to read what to fix |
| `validacao` sheet (first sheet) | List of all problems, with links to the cells. Delete it before publishing |

Example: [`examples/abrigo_ruim_anotado.xlsx`](examples/abrigo_ruim_anotado.xlsx).

**How it works inside:** the page loads [Pyodide](https://pyodide.org) (Python compiled to
WebAssembly) and runs the same Python package as the command line. All files are served by GitHub
Pages itself, with no external CDN. The automated test of the page checks that **no request leaves
the site** during validation. On the first visit the browser downloads about 18 MB (only once; it is
cached afterwards) and the validator may take up to 30 seconds to be ready. The page shows progress
by stage (Python environment, official XLSForm converter, rules) and only enables file upload when
everything is loaded.

**To publish your own copy:** in **Settings → Pages → Build and deployment → Source**, choose
**GitHub Actions**. The [`publicar-web.yml`](.github/workflows/publicar-web.yml) workflow builds the
site, tests it in a real browser and publishes it on every merge to `main`. To test locally:

```bash
python scripts/build_web.py
python -m http.server -d site 8000
```

### 5.2 Locally (command line)

Requirements: Python 3.10+. Java 8+ is only needed for ODK Validate (optional).

```bash
git clone https://github.com/agdala/xlsform-validator.git
cd xlsform-validator
pip install .
```

Validate a form (Markdown report on screen):

```bash
xlsform-validator caminho/do/formulario.xlsx
```

Validate several forms and write Markdown and JSON to a folder:

```bash
xlsform-validator forms/*.xlsx --formato md json --saida relatorios/
```

Include ODK Validate:

```bash
xlsform-validator formulario.xlsx --odk-validate
```

| Option | Effect |
|---|---|
| `--formato md json` | Report format(s) (default: `md`) |
| `--saida PASTA` | Writes `relatorio.md` and/or `relatorio.json` to the folder, instead of printing |
| `--regras ARQUIVO.yaml` | Uses a custom rule standard |
| `--exportar-regras ARQUIVO.yaml` | Copies the built-in standard for you to edit |
| `--odk-validate` | Turns on rule TEC-03 (requires Java) |
| `--anotar` | Generates `<nome>_anotado.xlsx` with the problems marked in the cells |

**Exit codes:** `0` passed (with or without warnings), `1` there is at least one error, `2`
unreadable file or invalid configuration. This makes it possible to use the tool in any CI pipeline.

### 5.3 On GitHub (automatic validation in pull requests)

The [`.github/workflows/validar-formularios.yml`](.github/workflows/validar-formularios.yml) workflow:

1. runs on every pull request and identifies the `.xlsx` files added or changed in `forms/`;
2. validates **only the new or changed files**, with ODK Validate;
3. posts the report as **a single comment on the PR**, updated on every new push;
4. writes the report to the job summary and as an artifact;
5. **fails the check** if there are errors, which makes it possible to block the merge via *branch protection*.

Team workflow:

```bash
git checkout -b novo-formulario
cp ~/Downloads/minha_avaliacao.xlsx forms/
git add forms/minha_avaliacao.xlsx
git commit -m "Adiciona formulário de avaliação"
git push -u origin novo-formulario
```

Then just open the PR, read the comment, fix and push again until the check turns green.

To use it in another repository, copy the workflow and change the installation step to
`pip install git+https://github.com/agdala/xlsform-validator.git`.

## 6. How to customize the rules

```bash
xlsform-validator --exportar-regras minhas_regras.yaml
# edite o arquivo
xlsform-validator formulario.xlsx --regras minhas_regras.yaml
```

Each rule in the YAML:

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

_The YAML keys and values are in Portuguese: `grupo` = group, `descricao` = description,
`severidade` = severity (`erro` = error, `aviso` = warning), `por_que_importa` = why it matters,
`ativa` = active, `parametros` = parameters._

Common adjustments:

| Need | Where to change |
|---|---|
| Downgrade a rule to a warning | `severidade: aviso` |
| Turn a rule off | `ativa: false` |
| Use another standard list for sex or other age bands | `DES-01` / `DES-02` → `codigos_obrigatorios` |
| Also require `deviceid` or `audit` | `MET-01` → `obrigatorios` |
| Recognize consent under another name | `CON-0x` → `padroes_nome` |
| Extend the words that indicate personal data | `LGPD-01` → `palavras_nome`, `padroes_label` |
| Allow future dates in scheduling fields | `VAL-02` → `excecoes` |
| Change the maximum name length | `NOM-04` → `tamanho_maximo` |

**Extra columns used by the LGPD rules** (KoboToolbox and ODK ignore columns they do not know, so
they can stay in the published form):

| Column (survey sheet) | Values | Use |
|---|---|---|
| `dado_pessoal` | `sim` / `nao` | Confirms personal data or dismisses a false positive from automatic detection |
| `justificativa_dados_pessoais` | text | Purpose and legal basis for collecting the personal data (min. 15 characters) |

**To create a new rule:** write a function in `src/xlsform_validator/rules/`, decorate it with
`@rule("XXX-01")`, add the corresponding entry in `rules.yaml` and a test in `tests/`. Loading
fails if there is a rule in the YAML without an implementation, which prevents "ghost" rules.

## 7. Technical decisions

| Decision | Rationale |
|---|---|
| **Own spreadsheet reading with openpyxl**, instead of using only pyxform | pyxform stops at the first error and does not always report the row. Reading the spreadsheet directly makes it possible to point to the exact row and run all rules even when the form does not convert. |
| **pyxform as a rule (TEC-01/02)**, not as a prior step | The report brings together, in one place, the official validation and the governance validation. pyxform messages without a row are located by the value they quote. |
| **Optional ODK Validate** | It requires Java and takes a few seconds; in the Action it always runs, locally only on request. |
| **Rules in YAML + implementation registered by ID** | Managers adjust severity, parameters and justifications without programming; the code only changes for new rules. |
| **Error x warning** | Not every deviation should stop collection. Warnings cover good practices and heuristic detections, which may have false positives. |
| **Stricter standard than the specification**, explicitly | `settings` is optional and names with upper case, hyphens or dots are valid in XLSForm. Rules EST-02 and NOM-02 are governance choices, and the YAML documents this. |
| **Examples generated by script** | Anyone can audit what is in the `.xlsx` files and recreate them; no real data is used. |
| **One comment per PR, updated** | Avoids cluttering the PR conversation with a comment on every push. |
| **Report in Portuguese, JSON keys in English** | The report is read by the team; the JSON is consumed by other tools. |
| **Web version with Python in the browser (Pyodide)**, instead of rewriting the rules in JavaScript | A single rule codebase for web, terminal and CI: no duplicated logic or tests. And the file never leaves the user's computer, which is consistent with the data protection theme and eases adoption in organizations. |
| **No server and no external CDN** | Zero cost, nothing to maintain or go down, and no third party receives data or usage metadata. Pyodide and dependencies are packaged in the build. |
| **Annotated spreadsheet as the main web output** | The web audience is not technical: seeing the marked cell in their own Excel file is faster than translating "sheet, row" from a report. |
| **Translated pyxform messages** | The most common ones become plain Portuguese; the original is still available for whoever needs it. |
| **End-to-end test in a real browser in CI** | Ensures that the published page works, fits on a phone and makes no external requests. |

Code structure:

```
src/xlsform_validator/
  form.py        form model and .xlsx reading
  engine.py      rule registry, YAML loading, execution
  rules/         one implementation per rule group
  rules.yaml     built-in quality standard
  report.py      Markdown and JSON reports, status and exit code
  annotate.py    annotated spreadsheet (colours, comments and summary sheet)
  pyxform_messages.py  translation of pyxform messages
  web.py         entry point of the web version
  cli.py         command line
web/             page (HTML, CSS, JavaScript) and worker that runs Python in the browser
tests/           89 pytest tests (each rule has passing and failing cases)
tests/web/       end-to-end test of the page (Playwright) and sample form with warnings only
scripts/         example generator and site build (build_web.py)
examples/        fictitious forms and generated reports
forms/           folder watched by the GitHub Action
```

To run the tests:

```bash
pip install ".[dev]"
pytest
```

## 8. Limitations

- **Keyword detection is heuristic.** Consent, age, sex, personal data and sensitive topics are
  recognized by the name and text of the questions. This produces false positives (e.g. "nome do
  abrigo", shelter name) and false negatives (e.g. a CPF field called `doc1`). The `dado_pessoal`
  column and the patterns in the YAML reduce the problem, but **do not replace human review** or a
  data protection impact assessment.
- **Logic is not executed.** CON-03 checks whether the questions depend on consent, but not
  whether the condition is right (`= 'sim'` or `= 'nao'`). LOG-01 checks whether the referenced
  fields exist, but not the expression syntax; that is left to pyxform and ODK Validate.
- **Content problems are out of scope.** Options that merge two concepts ("xenofobia e homofobia",
  xenophobia and homophobia), double-barrelled or biased questions and incorrect translation (only
  missing translation is detected) require human review. Detecting "e" (and) in the text would
  produce false positives on "Água e saneamento" (water and sanitation).
- **Cross-platform compatibility.** The rules and the official converter (pyxform) follow the
  XLSForm standard common to KoboToolbox, ODK, SurveyCTO, Ona and ArcGIS Survey123. Features
  specific to one platform (for example, SurveyCTO's own functions or Survey123-specific columns)
  may trigger warnings or errors from the official converter, or simply not be checked. Always test
  the final form on the target platform.
- **The web version does not run ODK Validate** (it requires Java) and uses the built-in rule
  standard. For custom rules or ODK Validate, use the command line or the GitHub Action.
- **The annotated spreadsheet is rewritten by openpyxl.** Common formatting is preserved, but
  advanced Excel features (macros, images, data validation with external lists) may be lost. That
  is why it serves to guide the fix; to publish, use the **ready form**, which is the original file
  with no changes.
- **`.xlsx` only.** The old `.xls` format and forms in Google Sheets must be exported to `.xlsx` first.
- **External lists** (`select_one_from_file`, attached CSVs) are not checked.
- **PRs from forks** cannot receive a comment (a GitHub permission limitation); in that case the
  report stays in the job summary.
- **LGPD compliance is not guaranteed by the tool.** It checks objective signals (recorded
  justification, option not to answer, consent), but purpose, legal basis, retention and
  information security depend on the organization's processes.

## Related projects

The four repositories form a data cycle, from collection to monitoring:

| Stage | Project | What it does | Published |
|---|---|---|---|
| 1. Collect | **xlsform-validator** (this repository) | Quality, consent and LGPD checks for KoboToolbox/ODK forms | [web version](https://agdala.github.io/xlsform-validator/) |
| 2. Transform and publish | [sismigra-analytics](https://github.com/agdala/sismigra-analytics) | Bronze/silver/gold pipeline with Python, DuckDB and dbt, with disclosure control | [dbt docs](https://agdala.github.io/sismigra-analytics/) |
| 3. Integrate | [record-linkage-kit](https://github.com/agdala/record-linkage-kit) | Deduplication and linkage of registries, with human review and pseudonymization | [report](https://agdala.github.io/record-linkage-kit/) |
| 4. Monitor | [monitoring-5w-kit](https://github.com/agdala/monitoring-5w-kit) | Partner reports, targets and double counting | [report](https://agdala.github.io/monitoring-5w-kit/) |

Author: Agda Santos, with the assistance of AI tools.

## License

[MIT](LICENSE). All forms, shelters and example data are fictitious.
