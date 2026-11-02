/* Interface do validador. Toda a validação acontece no worker.js, no navegador. */
"use strict";

const GROUP_ORDER = [
  "Estrutura", "Nomes de variáveis", "Listas de opções", "Lógica", "Validações",
  "Metadados de coleta", "Consentimento", "Proteção de dados (LGPD)", "Desagregação",
  "Idiomas", "Validação técnica (pyxform)",
];
const STATUS = {
  aprovado: { cls: "ok", titulo: "Aprovado", texto: "O formulário segue o padrão de qualidade. Pode seguir para publicação." },
  aprovado_com_avisos: { cls: "aviso", titulo: "Aprovado com avisos", texto: "Não há erros. Os avisos são recomendações: vale revisar antes de publicar." },
  reprovado: { cls: "erro", titulo: "Reprovado", texto: "Corrija os erros antes de publicar. Os avisos são recomendações." },
  ilegivel: { cls: "erro", titulo: "Não foi possível ler o arquivo", texto: "Confira se é uma planilha .xlsx válida (no Kobo: Download XLS)." },
};

const $ = (sel) => document.querySelector(sel);
const worker = new Worker("worker.js");
let ready = false;
let pending = null;
let requestId = 0;
let lastResult = null;
let filter = "todos";

/* Cria elementos sem innerHTML: o conteúdo da planilha nunca é interpretado como HTML. */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function plural(n, um, varios) {
  return `${n} ${n === 1 ? um : varios}`;
}

/* ------------------------------------------------------------------ motor */

worker.onmessage = (event) => {
  const msg = event.data;
  if (msg.type === "ready") {
    ready = true;
    setEngineStatus("pronto", "Validador pronto. Envie um arquivo.");
    if (pending) {
      const job = pending;
      pending = null;
      runValidation(job.name, job.buffer);
    }
  } else if (msg.type === "fatal") {
    setEngineStatus("falha", "Não foi possível carregar o validador neste navegador. Tente atualizar a página ou usar outro navegador.");
    console.error(msg.message);
  } else if (msg.type === "result" && msg.id === requestId) {
    showResult(JSON.parse(msg.json), msg.annotated);
  } else if (msg.type === "error" && msg.id === requestId) {
    showFailure(msg.message);
  }
};

function setEngineStatus(state, text) {
  const box = $("#status-motor");
  box.dataset.estado = state;
  $("#status-texto").textContent = text;
}

/* ------------------------------------------------------------------ envio */

async function handleFile(file) {
  if (!file) return;
  if (!/\.xlsx$/i.test(file.name)) {
    showFailure("Envie uma planilha no formato .xlsx. Se o arquivo for .xls (antigo), abra no Excel e salve como .xlsx.");
    return;
  }
  validateBuffer(file.name, await file.arrayBuffer());
}

function validateBuffer(name, buffer) {
  showLoading(name);
  if (!ready) {
    pending = { name, buffer };
    return;
  }
  runValidation(name, buffer);
}

function runValidation(name, buffer) {
  requestId += 1;
  worker.postMessage({ id: requestId, name, buffer }, [buffer]);
}

const input = $("#arquivo");
const zone = $("#zona-envio");
input.addEventListener("change", () => {
  handleFile(input.files[0]);
  input.value = "";
});
["dragenter", "dragover"].forEach((type) =>
  zone.addEventListener(type, (e) => {
    e.preventDefault();
    zone.classList.add("arrastando");
  }),
);
["dragleave", "drop"].forEach((type) =>
  zone.addEventListener(type, (e) => {
    e.preventDefault();
    zone.classList.remove("arrastando");
  }),
);
zone.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));

document.querySelectorAll("[data-exemplo]").forEach((button) =>
  button.addEventListener("click", async () => {
    const path = button.dataset.exemplo;
    const resp = await fetch(path);
    validateBuffer(path.split("/").pop(), await resp.arrayBuffer());
  }),
);

/* ------------------------------------------------------------------ resultado */

function resultSection() {
  const section = $("#resultado");
  section.hidden = false;
  section.replaceChildren();
  return section;
}

function showLoading(name) {
  const section = resultSection();
  section.append(
    el("div", { class: "cartao carregando" },
      el("span", { class: "spinner", "aria-hidden": "true" }),
      el("span", {}, ready ? `Validando ${name}…` : `Validando ${name}. Aguarde o validador terminar de carregar…`),
    ),
  );
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showFailure(message) {
  const section = resultSection();
  section.append(
    el("div", { class: "banner erro" },
      el("div", {},
        el("h2", {}, "Algo deu errado"),
        el("p", {}, message),
      ),
    ),
  );
}

function download(name, data, type) {
  const blob = new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function baseName(file) {
  return file.replace(/\.xlsx$/i, "");
}

function showResult(result, annotated) {
  lastResult = { result, annotated };
  filter = "todos";
  render();
}

function render() {
  const { result, annotated } = lastResult;
  const report = result.report;
  const status = STATUS[report.status] || STATUS.reprovado;
  const section = resultSection();

  const counts = report.read_error
    ? report.read_error
    : `${plural(report.summary.errors, "erro", "erros")} e ${plural(report.summary.warnings, "aviso", "avisos")}`;

  section.append(
    el("div", { class: `banner ${status.cls}` },
      el("div", { class: "banner-icone", "aria-hidden": "true" }, status.cls === "ok" ? "✓" : status.cls === "aviso" ? "!" : "✕"),
      el("div", {},
        el("p", { class: "banner-arquivo" }, report.file),
        el("h2", {}, `${status.titulo}${report.read_error ? "" : `: ${counts}`}`),
        el("p", {}, report.read_error ? counts : status.texto),
      ),
    ),
  );

  if (report.read_error) return;

  const actions = el("div", { class: "acoes" });
  if (annotated) {
    actions.append(
      el("button", {
        type: "button", class: "botao primario",
        onclick: () => download(`${baseName(report.file)}_anotado.xlsx`, annotated,
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
      }, "Baixar planilha anotada (.xlsx)"),
    );
  }
  actions.append(
    el("button", {
      type: "button", class: "botao",
      onclick: () => download(`relatorio_${baseName(report.file)}.md`, result.markdown, "text/markdown"),
    }, "Relatório (.md)"),
    el("button", {
      type: "button", class: "botao",
      onclick: () => download(`relatorio_${baseName(report.file)}.json`, JSON.stringify(report, null, 2), "application/json"),
    }, "Dados (.json)"),
    el("button", {
      type: "button", class: "botao-link",
      onclick: () => { $("#zona-envio").scrollIntoView({ behavior: "smooth" }); $("#arquivo").focus(); },
    }, "Validar outro arquivo"),
  );
  section.append(actions);
  if (annotated) {
    section.append(el("p", { class: "texto-apoio" },
      "Na planilha anotada, as linhas com problema ficam coloridas (vermelho para erro, amarelo para aviso) e a célula mais escura tem um comentário com o que corrigir. A primeira aba, ‘validacao’, resume tudo com links: apague-a antes de publicar."));
  }
  if (result.note) section.append(el("p", { class: "nota" }, result.note));

  const failed = report.rules.filter((r) => !r.passed);
  const passed = report.rules.filter((r) => r.passed);

  if (failed.length) {
    const total = report.summary.errors + report.summary.warnings;
    const chips = el("div", { class: "filtros", role: "group", "aria-label": "Filtrar problemas" },
      chip("todos", `Todos (${total})`),
      chip("erro", `Erros (${report.summary.errors})`),
      chip("aviso", `Avisos (${report.summary.warnings})`),
    );
    section.append(chips);

    const visible = failed.filter((r) => filter === "todos" || r.severity === filter);
    const groups = groupBy(visible, (r) => r.group);
    for (const group of sortGroups(Object.keys(groups))) {
      const rules = groups[group].sort((a, b) => (a.severity === b.severity ? a.rule_id.localeCompare(b.rule_id) : a.severity === "erro" ? -1 : 1));
      section.append(
        el("div", { class: "grupo" },
          el("h3", {}, group),
          rules.map(ruleCard),
        ),
      );
    }
    if (!visible.length) section.append(el("p", { class: "texto-apoio" }, "Nenhum item neste filtro."));
  }

  if (passed.length) {
    section.append(
      el("details", { class: "aprovadas" },
        el("summary", {}, `${plural(passed.length, "verificação aprovada", "verificações aprovadas")}`),
        el("ul", {}, passed.map((r) => el("li", {}, el("span", { class: "id-regra" }, r.rule_id), " ", r.description))),
      ),
    );
  }
}

function chip(value, label) {
  return el("button", {
    type: "button",
    class: `chip${filter === value ? " ativo" : ""}`,
    "aria-pressed": filter === value ? "true" : "false",
    onclick: () => { filter = value; render(); },
  }, label);
}

function ruleCard(rule) {
  const sev = rule.severity === "erro" ? "erro" : "aviso";
  return el("details", { class: `regra ${sev}`, open: true },
    el("summary", {},
      el("span", { class: `pilula ${sev}` }, sev === "erro" ? "Erro" : "Aviso"),
      el("span", { class: "regra-titulo" }, rule.description),
      el("span", { class: "regra-meta" }, `${rule.rule_id} · ${plural(rule.findings.length, "ocorrência", "ocorrências")}`),
    ),
    el("p", { class: "porque" }, el("strong", {}, "Por que importa: "), rule.why_it_matters),
    el("ul", { class: "ocorrencias" }, rule.findings.map(findingItem)),
  );
}

function findingItem(f) {
  const where = f.sheet ? (f.row ? `${f.sheet} · linha ${f.row}` : f.sheet) : "formulário";
  const message = f.message.replace(/^pyxform: /, "Conversor oficial: ");
  const fix = f.suggestion || "";
  const isOriginal = fix.startsWith("Mensagem original:");
  return el("li", {},
    el("span", { class: "local" }, where),
    el("div", {},
      el("p", { class: "mensagem" }, message),
      fix && !isOriginal ? el("p", { class: "correcao" }, el("strong", {}, "Como corrigir: "), fix) : null,
      isOriginal ? el("details", { class: "original" }, el("summary", {}, "Ver mensagem original em inglês"), el("p", {}, fix.replace("Mensagem original: ", ""))) : null,
    ),
  );
}

function groupBy(list, key) {
  return list.reduce((acc, item) => {
    (acc[key(item)] ||= []).push(item);
    return acc;
  }, {});
}

function sortGroups(groups) {
  const pos = (g) => (GROUP_ORDER.indexOf(g) === -1 ? 99 : GROUP_ORDER.indexOf(g));
  return groups.sort((a, b) => pos(a) - pos(b));
}

/* ------------------------------------------------------------------ lista de regras */

fetch("rules.json")
  .then((r) => r.json())
  .then((data) => {
    const rules = Object.entries(data.regras).map(([id, r]) => ({ id, ...r }));
    const groups = groupBy(rules, (r) => r.grupo);
    const box = $("#lista-regras");
    for (const group of sortGroups(Object.keys(groups))) {
      box.append(
        el("details", {},
          el("summary", {}, `${group} (${groups[group].length})`),
          el("ul", {}, groups[group].map((r) =>
            el("li", {},
              el("span", { class: `pilula ${r.severidade}` }, r.severidade === "erro" ? "Erro" : "Aviso"),
              " ",
              el("span", { class: "id-regra" }, r.id),
              " ",
              r.descricao,
              r.ativa === false ? el("em", {}, " (só na versão de linha de comando)") : null,
            ),
          )),
        ),
      );
    }
  })
  .catch(() => {});
