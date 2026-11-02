# Relatório de validação XLSForm

**Arquivo:** `examples/abrigo_ruim.xlsx`

**Status:** ❌ Reprovado

| Erros | Avisos | Regras verificadas | Regras com problema |
|---:|---:|---:|---:|
| 26 | 11 | 35 | 26 |

## Resumo por regra

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

## O que corrigir

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
| survey | 3 | 'NomeCompleto': coluna label sem tradução para Español (es). | Preencha a coluna label::Español (es). |
| survey | 10 | 'pessoas_família': coluna label sem tradução para Español (es). | Preencha a coluna label::Español (es). |
| survey | 11 | 'violencias_sofridas': coluna label sem tradução para Español (es). | Preencha a coluna label::Español (es). |
| survey | 12 | 'recebe_auxilio': coluna label sem tradução para Español (es). | Preencha a coluna label::Español (es). |
| survey | 14 | 'abrigo': coluna label sem tradução para Español (es). | Preencha a coluna label::Español (es). |
| choices | 9 | 'racismo_estrutural': coluna label sem tradução para Español (es). | Preencha a coluna label::Español (es). |

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
| choices | 3 | pyxform: [row : 3] On the 'choices' sheet, the 'name' value is invalid. Choice names must be unique for each choice list. If this is intentional, use the setting 'allow_choice_duplicates'. Learn more: https://xlsform.org/#choice-names. | - |

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

